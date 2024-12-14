import feedparser
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urlunparse
import logging
from functools import wraps
from .extractors import ContentExtractionService
from .storage import ArticleStorage
from .article import Article # type: ignore

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def handle_errors(func):
    """Decorator for consistent error handling"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Error in {func.__name__}: {e}")
            return None
    return wrapper

class NewsService:
    """Service for fetching and processing crypto news articles"""
    
    FEED_URLS = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/?",
        "https://cointelegraph.com/rss",
        "https://www.theblock.co/rss.xml"
    ]
    
    def __init__(self, storage_file: str = "posted_articles.json", logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.storage = ArticleStorage(storage_file, logger=self.logger)
        self.content_service = ContentExtractionService(logger=self.logger)
    
    @handle_errors
    def get_latest_article(self) -> Optional[Article]:
        """Fetch the latest unposted article from configured RSS feeds"""
        latest_article = None
        latest_time = None
        
        for url in self.FEED_URLS:
            self.logger.debug(f"Fetching RSS feed: {url}")
            feed = feedparser.parse(url)
            if not feed.entries:
                self.logger.warning(f"No entries found in feed: {url}")
                continue
                
            for entry in feed.entries:
                article_url = entry.get('link', '')
                parsed = urlparse(article_url)
                clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
                
                if self.storage.is_article_posted(clean_url):
                    continue
                
                pub_time = entry.get('published_parsed') or entry.get('updated_parsed')
                if pub_time and (latest_time is None or pub_time > latest_time):
                    latest_time = pub_time
                    latest_article = entry
        
        if not latest_article:
            self.logger.info("No new articles found")
            return None
            
        title = latest_article.get('title', '')
        article_url = latest_article.get('link', '')
        parsed = urlparse(article_url)
        clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
        
        return Article(
            title=title,
            url=clean_url,
            published_at=datetime(*latest_time[:6]) if latest_time else datetime.now()
        )
    
    def get_article_content(self, url: str) -> Optional[str]:
        """Extract the full content of an article"""
        return self.content_service.get_article_content(url, self.logger)
    
    def mark_article_as_posted(self, article: Article) -> None:
        """Mark an article as posted"""
        self.storage.mark_as_posted(article)
    
    def cleanup_old_articles(self, days: int = 30) -> None:
        """Clean up old article entries"""
        self.storage.cleanup_old_entries(days)

def main():
    """Main function to demonstrate usage"""
    logging.basicConfig(level=logging.INFO)
    news_service = NewsService()
    
    # Get latest article
    article = news_service.get_latest_article()
    if not article:
        print("No new articles found")
        return
    
    print(f"Latest article: {article.title}")
    print(f"URL: {article.url}")
    
    # Get content
    content = news_service.get_article_content(article.url)
    if content:
        print("\nContent preview:")
        print(content[:500] + "...")
        # Mark as posted only if content was successfully extracted
        news_service.mark_article_as_posted(article)
    else:
        print("Failed to extract content")

if __name__ == "__main__":
    main()