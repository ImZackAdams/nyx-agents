import logging
import sys
import feedparser
import os
from datetime import datetime
from urllib.parse import urlparse, urlunparse

# Adjust paths if necessary, depending on your directory structure:
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from bot.services.news.news_service import NewsService

# Set up logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def simulate_news_fetch():
    """Simulate fetching and processing the latest article from the first configured RSS feed."""
    news_service = NewsService(logger=logger)

    if not news_service.FEED_URLS:
        logger.error("No feed URLs configured in NewsService.")
        return

    feed_url = news_service.FEED_URLS[0]
    logger.info(f"Fetching feed: {feed_url}")

    feed = feedparser.parse(feed_url)
    if not feed.entries:
        logger.warning("No entries found in this feed.")
        return

    # Find the latest article
    latest_entry = None
    latest_time = None
    for entry in feed.entries:
        pub_time = entry.get('published_parsed') or entry.get('updated_parsed')
        if pub_time and (latest_time is None or pub_time > latest_time):
            latest_time = pub_time
            latest_entry = entry

    if not latest_entry:
        logger.info("No latest article found.")
        return

    article_url = latest_entry.get('link', '')
    title = latest_entry.get('title', 'No title')

    logger.info(f"Latest article title: {title}")
    logger.info(f"URL: {article_url}")

    # Try extracting content
    content = news_service.get_article_content(article_url)
    if content:
        logger.info("Content extracted successfully!")
        preview = content[:500] + "..." if len(content) > 500 else content
        logger.info(f"Content preview:\n{preview}")
    else:
        logger.warning("Failed to extract content for this article.")

if __name__ == "__main__":
    simulate_news_fetch()
