import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
import feedparser
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from typing import Optional, Dict, Protocol, List
from urllib.parse import urlparse, urlunparse
import random
from functools import wraps
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Article:
    title: str
    url: str
    content: str = ''
    published_at: Optional[datetime] = None

class ContentExtractor(Protocol):
    """Protocol for content extractors"""
    def extract(self, soup: BeautifulSoup) -> Optional[str]:
        ...

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

class BaseExtractor:
    """Base class for content extractors with common utilities"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def extract(self, soup: BeautifulSoup) -> Optional[str]:
        """Generic content extraction for unknown domains."""
        article_body = soup.find("article") or soup.find("main") or soup.find("body")
        return self._extract_paragraphs(article_body)
    
    @staticmethod
    def _extract_paragraphs(container) -> Optional[str]:
        if not container:
            return None
        paragraphs = container.find_all("p")
        text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        return text.strip() if text.strip() else None
    
    def _clean_unwanted_elements(self, article_body):
        """Remove unwanted elements from the article body"""
        unwanted_selectors = [
            'script', 'style', 'nav', 'header', 'footer',
            '.ad', '.advertisement', '.social-share',
            '.related-articles', '.newsletter-signup'
        ]
        for selector in unwanted_selectors:
            for element in article_body.select(selector):
                element.decompose()

class CointelegraphExtractor(BaseExtractor):
    """Cointelegraph content extractor with enhanced selector support"""
    
    def __init__(self, logger=None):
        super().__init__(logger=logger)
        self.selectors = [
            "div.post-content",
            "div.post-content__text",
            "div.article__body",
            "div.post-page__article-content",
            "div[class*='post-content']",
            "div[class*='article-content']",
            "article div.content",
            "article"
        ]
    
    def extract(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content using multiple selector strategies"""
        self.logger.debug("Starting Cointelegraph content extraction")
        
        # Check for paywall/premium content
        if self._is_premium_content(soup):
            self.logger.warning("Premium content detected")
            return None
        
        # Try each selector strategy
        for selector in self.selectors:
            self.logger.debug(f"Trying selector: {selector}")
            if article_body := soup.select_one(selector):
                self._clean_unwanted_elements(article_body)
                if text := self._extract_paragraphs(article_body):
                    self.logger.info(f"Successfully extracted content using selector: {selector}")
                    return text
        
        return self._fallback_extraction(soup)
    
    def _is_premium_content(self, soup: BeautifulSoup) -> bool:
        """Check if the article is premium content"""
        premium_indicators = [
            ".premium-content",
            ".locked-content",
            ".subscribe-content",
            "[data-premium='true']"
        ]
        return any(bool(soup.select(selector)) for selector in premium_indicators)
    
    def _fallback_extraction(self, soup: BeautifulSoup) -> Optional[str]:
        """Fallback method for content extraction"""
        all_paragraphs = soup.select('article p, div[class*="content"] p, div[class*="article"] p')
        if all_paragraphs:
            text = "\n\n".join(p.get_text(strip=True) for p in all_paragraphs if p.get_text(strip=True))
            return text if len(text) > 500 else None
        return None

class TheBlockExtractor(BaseExtractor):
    """The Block content extractor with comprehensive selector support"""
    
    def __init__(self, logger=None):
        super().__init__(logger=logger)
        self.selectors = [
            "article[class*='Post_article']",
            "div[class*='Post_content']",
            "div.article__content",
            "div[class*='ArticleContent']",
            "article div[class*='content']",
            "div[class*='post-content']",
            "article",
            "#articleContent",
            # Additional broader selectors
            "div[class*='article']",
            "div[class*='content']",
            ".post-body",
            "main article",
            ".article-container",
            # Very broad fallbacks
            "main",
            ".main-content"
        ]
    
    def extract(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content using multiple selector strategies"""
        self.logger.debug("Starting TheBlock content extraction")
        
        # Check for premium/paywall content
        if self._is_restricted_content(soup):
            self.logger.warning("Premium/Restricted content detected")
            return None
        
        # Try each selector strategy
        for selector in self.selectors:
            self.logger.debug(f"Trying selector: {selector}")
            if article_body := soup.select_one(selector):
                self._clean_unwanted_elements(article_body)
                self._remove_premium_elements(article_body)
                if text := self._extract_paragraphs(article_body):
                    text = self._clean_text(text)
                    if text and len(text) > 500:
                        self.logger.info(f"Successfully extracted content using selector: {selector}")
                        return text
        
        return self._fallback_extraction(soup)
    
    def _is_restricted_content(self, soup: BeautifulSoup) -> bool:
        """Check if the article is restricted/premium content"""
        restricted_indicators = [
            '.premium-content',
            '.subscription-block',
            '.paywall',
            '.article-paywall',
            'div[class*="Premium"]',
            'div[class*="premium"]',
            'div[class*="Paywall"]'
        ]
        return any(bool(soup.select(selector)) for selector in restricted_indicators)
    
    def _remove_premium_elements(self, article_body):
        """Remove premium-specific elements from the article body"""
        premium_selectors = [
            'div[class*="PremiumContent"]',
            'div[class*="premium-content"]',
            'div[class*="paywall"]',
            '.premium-overlay',
            '.premium-banner'
        ]
        for selector in premium_selectors:
            for element in article_body.select(selector):
                element.decompose()
    
    @staticmethod
    def _clean_text(text: str) -> Optional[str]:
        """Clean extracted text of unwanted content"""
        replacements = {
            '[Premium Content]': '',
            '[Subscribe]': '',
            'Premium Content': '',
            'Subscribe to read the full article': '',
            'Subscribe to access this article': ''
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = text.strip()
        return text if len(text) > 100 else None
    
    def _fallback_extraction(self, soup: BeautifulSoup) -> Optional[str]:
        """Fallback method for content extraction"""
        # Try to find content in any major content area
        content_selectors = [
            'article p',
            'div[class*="content"] p',
            'div[class*="article"] p',
            'div[class*="post"] p'
        ]
        
        all_paragraphs = []
        for selector in content_selectors:
            paragraphs = soup.select(selector)
            all_paragraphs.extend(paragraphs)
        
        if all_paragraphs:
            text = "\n\n".join(p.get_text(strip=True) for p in all_paragraphs if p.get_text(strip=True))
            return self._clean_text(text)
        return None

class CoindeskExtractor(BaseExtractor):
    """Enhanced Coindesk content extractor with multiple selector strategies"""
    
    def __init__(self, logger=None):
        super().__init__(logger=logger)
        self.selectors = [
            "div.article-body",
            "div.at-body",
            "div[data-article-body]",
            "div.article-content",
            "div.article-wrapper",
            ".article-container",
            "article",
            "main article",
            ".post-content",
            ".at-article",
            # Broader selectors as fallback
            "div[class*='article']",
            "div[class*='content']",
            "main",
        ]
    
    def extract(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content using multiple selector strategies"""
        self.logger.debug("Starting Coindesk content extraction")
        
        # Check for paywall
        if self._is_paywalled(soup):
            self.logger.warning("Paywall detected")
            return None
        
        # Try each selector strategy
        for selector in self.selectors:
            self.logger.debug(f"Trying selector: {selector}")
            if article_body := soup.select_one(selector):
                self._clean_unwanted_elements(article_body)
                if text := self._extract_paragraphs(article_body):
                    self.logger.info(f"Successfully extracted content using selector: {selector}")
                    return text
        
        # Fallback to more aggressive extraction
        self.logger.debug("No content found with primary selectors, trying fallback")
        return self._fallback_extraction(soup)
    
    def _is_paywalled(self, soup: BeautifulSoup) -> bool:
        """Check if the article is behind a paywall"""
        paywall_indicators = [
            "div.article-paywall",
            "div.paywall",
            "div[data-paywall]",
            "div.premium-content",
            "#premium-content",
            ".locked-content"
        ]
        return any(bool(soup.select(selector)) for selector in paywall_indicators)
    
    def _fallback_extraction(self, soup: BeautifulSoup) -> Optional[str]:
        """Fallback method for content extraction"""
        # Try to find any div containing multiple paragraphs
        for div in soup.find_all('div'):
            paragraphs = div.find_all('p')
            if len(paragraphs) > 5:  # Assume article body has at least 5 paragraphs
                text = self._extract_paragraphs(div)
                if text and len(text) > 500:  # Minimum content length
                    return text
        return None

class ContentExtractionService:
    """Service for extracting content from different news sources"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.extractors = {
            "coindesk.com": CoindeskExtractor(logger=self.logger),
            "cointelegraph.com": CointelegraphExtractor(logger=self.logger),
            "theblock.co": TheBlockExtractor(logger=self.logger)
        }
    
    def get_article_content(self, url: str, logger=None) -> Optional[str]:
        """Extract content from the given URL"""
        logger = logger or self.logger
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                viewport={"width": 1920, "height": 1080}
            )
            
            # Add stealth options
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
            """)
            
            page = context.new_page()
            page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
            })
            
            try:
                logger.debug(f"Fetching content from: {url}")
                
                # Use domcontentloaded instead of networkidle for faster initial load
                response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                if not response or response.status != 200:
                    logger.error(f"Failed to fetch {url}: Status {response.status if response else 'No Response'}")
                    return None

                # Domain-specific waiting strategy
                domain = urlparse(url).netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]

                # Define content ready selectors per domain
                content_selectors = {
                    "coindesk.com": "article, div.article-body, .at-body",
                    "theblock.co": "article, div[class*='ArticleContent'], div[class*='Post_content']",
                    "cointelegraph.com": "div.post-content, article"
                }

                # Wait for content or timeout
                try:
                    selector = content_selectors.get(domain, "article")
                    page.wait_for_selector(selector, timeout=5000)
                except Exception as e:
                    logger.warning(f"Timeout waiting for content selector, proceeding anyway: {e}")
                
                # Short additional wait for dynamic content
                try:
                    page.wait_for_timeout(2000)
                except Exception as e:
                    logger.warning(f"Additional wait interrupted: {e}")

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                extractor = self.extractors.get(domain, BaseExtractor(logger=logger))
                logger.debug(f"Using extractor for domain: {domain}")

                text = extractor.extract(soup)
                if not text:
                    logger.warning(f"No content extracted for {url}")
                return text
                
            except Exception as e:
                logger.error(f"Error extracting content from {url}: {e}")
                return None
            finally:
                browser.close()

class NewsService:
    """Service for fetching and processing crypto news articles"""
    
    FEED_URLS = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/?",
        "https://cointelegraph.com/rss",
        "https://www.theblock.co/rss.xml"
    ]
    
    def __init__(self, storage_file: str = "posted_articles.json", logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.storage_file = storage_file
        self.posted_articles: Dict[str, str] = {}
        self.content_service = ContentExtractionService(logger=self.logger)
        self._load_posted_articles()
    
    @handle_errors
    def _load_posted_articles(self) -> None:
        """Load previously posted articles from storage"""
        if os.path.exists(self.storage_file):
            with open(self.storage_file, 'r') as f:
                self.posted_articles = json.load(f)
    
    @handle_errors
    def _save_posted_articles(self) -> None:
        """Save posted articles to storage"""
        with open(self.storage_file, 'w') as f:
            json.dump(self.posted_articles, f)
    
    def is_article_posted(self, url: str) -> bool:
        """Check if an article has been posted before"""
        return url in self.posted_articles
    
    def mark_as_posted(self, article: Article) -> None:
        """Mark an article as posted"""
        self.posted_articles[article.url] = datetime.now().isoformat()
        self._save_posted_articles()
    
    @handle_errors
    def cleanup_old_entries(self, days: int = 30) -> None:
        """Remove entries older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        self.posted_articles = {
            url: timestamp
            for url, timestamp in self.posted_articles.items()
            if datetime.fromisoformat(timestamp) > cutoff
        }
        self._save_posted_articles()
    
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
                
                if self.is_article_posted(clean_url):
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
        news_service.mark_as_posted(article)
    else:
        print("Failed to extract content")

if __name__ == "__main__":
    main()