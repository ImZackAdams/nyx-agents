import logging
from datetime import datetime
import sys
import feedparser
import os
import sys
# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(root_dir)



# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_latest_articles_from_each_source():
    """Fetch and test content extraction for the latest article from each news source."""
    from bot.services.news.news_service import NewsService
    
    news_service = NewsService(logger=logger)
    
    for feed_url in news_service.FEED_URLS:
        logger.info(f"\nTesting feed: {feed_url}")
        
        # Parse this specific feed
        feed = feedparser.parse(feed_url)
        
        if not feed.entries:
            logger.error("No entries found in this feed.")
            continue
        
        # Find the latest article in this feed
        latest_entry = None
        latest_time = None
        for entry in feed.entries:
            pub_time = entry.get('published_parsed') or entry.get('updated_parsed')
            if pub_time and (latest_time is None or pub_time > latest_time):
                latest_time = pub_time
                latest_entry = entry
        
        if not latest_entry:
            logger.error("Could not determine the latest entry in this feed.")
            continue
        
        article_url = latest_entry.get('link', '')
        title = latest_entry.get('title', 'No title')
        
        logger.info(f"Latest article title: {title}")
        logger.info(f"URL: {article_url}")

        # Extract content for this article
        content = news_service.get_article_content(article_url)
        if content:
            logger.info("Successfully extracted content!")
            logger.info(f"Content preview (first 500 chars):\n{content[:500]}...")
            logger.info(f"Content length: {len(content)} characters")
        else:
            logger.error("Failed to extract content for this article.")

if __name__ == "__main__":
    test_latest_articles_from_each_source()
