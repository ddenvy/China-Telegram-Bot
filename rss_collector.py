"""RSS feed collector for fetching and processing news articles."""

import asyncio
import aiohttp
import feedparser
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from rss_sources import get_all_feeds
import config

class RSSCollector:
    def __init__(self):
        self.feeds = get_all_feeds()
        self.data_dir = "data"
        self.seen_articles_file = os.path.join(self.data_dir, "seen_articles.json")
        self.ensure_data_dir()
        self.seen_articles = self.load_seen_articles()

    def ensure_data_dir(self):
        """Ensure data directory exists."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def load_seen_articles(self) -> set:
        """Load previously seen article URLs to avoid duplicates."""
        if os.path.exists(self.seen_articles_file):
            try:
                with open(self.seen_articles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('urls', []))
            except (json.JSONDecodeError, FileNotFoundError):
                return set()
        return set()

    def save_seen_articles(self):
        """Save seen article URLs to file."""
        data = {
            'urls': list(self.seen_articles),
            'last_updated': datetime.now().isoformat()
        }
        with open(self.seen_articles_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def fetch_feed(self, session: aiohttp.ClientSession, feed_config: Dict) -> List[Dict]:
        """Fetch and parse a single RSS feed."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            async with session.get(feed_config['url'], timeout=30, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    articles = []
                    for entry in feed.entries:
                        # Skip if we've already seen this article
                        if entry.link in self.seen_articles:
                            continue
                        
                        # Check if article is recent (within last 24 hours)
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            pub_date = datetime(*entry.published_parsed[:6])
                            if datetime.now() - pub_date > timedelta(days=1):
                                continue
                        
                        # Try to extract image URL
                        image_url = None
                        try:
                            if hasattr(entry, 'media_content') and entry.media_content:
                                image_url = entry.media_content[0].get('url')
                            elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                                image_url = entry.media_thumbnail[0].get('url')
                            elif hasattr(entry, 'links'):
                                for l in entry.links:
                                    if getattr(l, 'rel', '') == 'enclosure' and 'image' in getattr(l, 'type', ''):
                                        image_url = getattr(l, 'href', None)
                                        if image_url:
                                            break
                            elif hasattr(entry, 'image'):
                                image_url = getattr(entry, 'image', None)
                        except Exception:
                            image_url = None
                        
                        article = {
                            'title': entry.title,
                            'link': entry.link,
                            'description': getattr(entry, 'description', ''),
                            'published': getattr(entry, 'published', ''),
                            'source': feed_config['name'],
                            'category': feed_config['category'],
                            'image_url': image_url
                        }
                        articles.append(article)
                    
                    return articles
                else:
                    reason = getattr(response, 'reason', '')
                    print(f"❌ Failed to fetch {feed_config['name']}: HTTP {response.status} {reason}")
                    return []
        except Exception as e:
            print(f"❌ Error fetching {feed_config['name']}: {type(e).__name__}: {e}")
            return []

    async def collect_all_feeds(self) -> List[Dict]:
        """Collect articles from all RSS feeds."""
        print("🔄 Collecting RSS feeds...")
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_feed(session, feed) for feed in self.feeds]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            all_articles = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Error processing {self.feeds[i]['name']}: {result}")
                else:
                    all_articles.extend(result)
                    if result:
                        print(f"✅ {self.feeds[i]['name']}: {len(result)} new articles")
        
        # Sort by relevance/recency and limit
        all_articles = sorted(all_articles, key=lambda x: x.get('published', ''), reverse=True)
        limited_articles = all_articles[:config.MAX_ARTICLES_PER_DAY]
        
        # Note: seen articles are now marked on publish, not on collect
        print(f"📰 Total collected: {len(limited_articles)} articles")
        return limited_articles

    def cleanup_old_seen_articles(self, days: int = 7):
        """Clean up old seen articles to prevent the set from growing too large."""
        # This is a simple cleanup - in production you might want more sophisticated logic
        if len(self.seen_articles) > 1000:
            # Keep only recent articles (this is a simplified approach)
            print("🧹 Cleaning up old seen articles...")
            # For now, just clear half of them randomly
            articles_list = list(self.seen_articles)
            self.seen_articles = set(articles_list[len(articles_list)//2:])
            self.save_seen_articles()

async def main():
    """Test function for RSS collector."""
    collector = RSSCollector()
    articles = await collector.collect_all_feeds()
    
    print(f"\n📊 Collected {len(articles)} articles:")
    for article in articles[:3]:  # Show first 3
        print(f"- {article['title']} ({article['source']})")

if __name__ == "__main__":
    asyncio.run(main())