"""RSS feed sources for Chinese technology and business news."""

RSS_FEEDS = [
    {
        "name": "Tech in Asia (China)",
        "url": "https://www.techinasia.com/tag/china/feed",
        "category": "tech_news"
    },
    {
        "name": "ChinaTechNews.com",
        "url": "https://chinatechnews.com/feed",
        "category": "tech_news"
    },
    {
        "name": "Pandaily",
        "url": "https://pandaily.com/feed",
        "category": "tech_news"
    },
]

def get_all_feeds():
    """Return all RSS feed configurations."""
    return RSS_FEEDS

def get_feeds_by_category(category):
    """Return RSS feeds filtered by category."""
    return [feed for feed in RSS_FEEDS if feed["category"] == category]