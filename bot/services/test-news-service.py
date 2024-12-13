import logging
from datetime import datetime
import sys
import feedparser

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_rss_feeds():
    """Test all RSS feeds individually"""
    from news_service import NewsService
    
    news_service = NewsService(logger=logger)
    
    for feed_url in news_service.FEED_URLS:
        logger.info(f"\nTesting RSS feed: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            if feed.entries:
                logger.info(f"Successfully fetched feed - {len(feed.entries)} entries found")
                first_entry = feed.entries[0]
                logger.info(f"Latest article: {first_entry.get('title', 'No title')}")
            else:
                logger.error(f"No entries found in feed")
        except Exception as e:
            logger.error(f"Error fetching feed: {e}")

def test_the_block_scraping():
    """Test function to verify The Block article fetching and parsing"""
    from news_service import NewsService
    
    news_service = NewsService(logger=logger)
    
    logger.info("\nTesting full article fetch from The Block...")
    
    article = news_service.get_latest_article()
    if article:
        logger.info(f"Successfully fetched article:")
        logger.info(f"Title: {article.title}")
        logger.info(f"URL: {article.url}")
        logger.info(f"Published at: {article.published_at}")
        
        logger.info("\nTesting content extraction...")
        content = news_service.get_article_content(article.url)
        
        if content:
            logger.info("Successfully extracted content!")
            logger.info(f"\nContent preview (first 500 chars):\n{content[:500]}...")
            logger.info(f"Content length: {len(content)} characters")
            return True
        else:
            logger.error("Failed to extract content")
            return False
    else:
        logger.error("Failed to fetch article from RSS feed")
        return False

def test_specific_article(url: str):
    """Test content extraction from a specific article URL"""
    from news_service import NewsService
    
    news_service = NewsService(logger=logger)
    
    logger.info(f"\nTesting specific article: {url}")
    content = news_service.get_article_content(url)
    
    if content:
        logger.info("Successfully extracted content!")
        logger.info(f"\nContent preview (first 500 chars):\n{content[:500]}...")
        logger.info(f"Content length: {len(content)} characters")
        return True
    else:
        logger.error("Failed to extract content")
        return False

if __name__ == "__main__":
    # Test RSS feeds first
    test_rss_feeds()
    
    # Test article fetching and parsing
    success = test_the_block_scraping()
    logger.info(f"\nOverall test {'successful' if success else 'failed'}")
    
    # You can uncomment and modify this to test specific articles
    # test_url = "https://www.theblock.co/post/123456/your-specific-article"
    # test_specific_article(test_url)