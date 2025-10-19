import asyncio
from rss_collector import RSSCollector
from publisher import get_publisher
import config

async def main():
    rss = RSSCollector()
    articles = await rss.collect_all_feeds()
    pub = get_publisher()
    max_count = getattr(config, 'MAX_ARTICLES_PER_DAY', 3)
    published = 0
    for article in articles[:max_count]:
        ok = await pub.publish_article(article)
        if ok:
            published += 1
    await pub.close()
    print(f"Published {published} article(s)")

if __name__ == "__main__":
    asyncio.run(main())