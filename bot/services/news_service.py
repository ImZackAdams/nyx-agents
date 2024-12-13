import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
import feedparser
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from typing import Optional, Dict, Protocol
from urllib.parse import urlparse, urlunparse
import random
from functools import wraps

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

class CoindeskExtractor(BaseExtractor):
    def extract(self, soup: BeautifulSoup) -> Optional[str]:
        article_body = soup.find("div", class_="article-pharagraphs") or soup.find("article")
        return self._extract_paragraphs(article_body)

class CointelegraphExtractor(BaseExtractor):
    def extract(self, soup: BeautifulSoup) -> Optional[str]:
        selectors = [
            "div.post-content",
            "div.post-content__text",
            "div.article__body",
            "div.post-page__article-content"
        ]
        
        for selector in selectors:
            if article_body := soup.select_one(selector):
                if text := self._extract_paragraphs(article_body):
                    return text
        
        article_body = soup.find("article") or soup.find("main") or soup.find("body")
        return self._extract_paragraphs(article_body)

class TheBlockExtractor(BaseExtractor):
    def extract(self, soup: BeautifulSoup) -> Optional[str]:
        selectors = [
            # Existing selectors
            "article[class*='Post_article']",
            "div[class*='Post_content']",
            "div.article__content",
            "div[class*='ArticleContent']",
            "article div[class*='content']",
            "article",

            # New selector targeting the specific element you identified
            "#articleContent"
        ]

        for selector in selectors:
            if article_body := soup.select_one(selector):
                self._clean_unwanted_elements(article_body)
                if text := self._extract_paragraphs(article_body):
                    return self._clean_text(text)
                    
        return self._fallback_extraction(soup)

    
    @staticmethod
    def _clean_unwanted_elements(article_body):
        for unwanted in article_body.select(
            '.premium-content, .subscription-block, .paywall, .article-paywall, '
            'div[class*="Premium"], div[class*="premium"], div[class*="Paywall"], '
            'script, style, nav, header, footer'
        ):
            unwanted.decompose()
    
    @staticmethod
    def _clean_text(text: str) -> Optional[str]:
        text = text.replace('[Premium Content]', '').replace('[Subscribe]', '').strip()
        return text if len(text) > 100 else None
    
    def _fallback_extraction(self, soup: BeautifulSoup) -> Optional[str]:
        all_paragraphs = soup.select('article p, div[class*="content"] p, div[class*="article"] p')
        if all_paragraphs:
            text = "\n\n".join(p.get_text(strip=True) for p in all_paragraphs if p.get_text(strip=True))
            return self._clean_text(text)
        return None

class ContentExtractionService:
    """Service for extracting content from different news sources"""
    
    def __init__(self):
        self.extractors = {
            "coindesk.com": CoindeskExtractor(),
            "cointelegraph.com": CointelegraphExtractor(),
            "theblock.co": TheBlockExtractor()
        }
    
    def get_article_content(self, url: str, logger=None) -> Optional[str]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            )
            page = context.new_page()
            
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                if not response or response.status != 200:
                    if logger:
                        logger.error(f"Failed to fetch {url}: Status {response.status if response else 'No Response'}")
                    return None

                # Give the page a moment to load additional content
                page.wait_for_timeout(3000)

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                domain = urlparse(url).netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]

                extractor = self.extractors.get(domain, BaseExtractor())

                # Optional: Add debug logs
                if logger:
                    logger.debug(f"Using extractor for domain: {domain}")

                return extractor.extract(soup)
                
            except Exception as e:
                if logger:
                    logger.error(f"Error extracting content from {url}: {e}")
                return None
            finally:
                browser.close()


class NewsService:
    """Service for fetching and processing crypto news articles."""
    
    FEED_URLS = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/?",
        "https://cointelegraph.com/rss",
        "https://www.theblock.co/rss.xml"
    ]
    
    def __init__(self, logger=None, storage_file: str = "posted_articles.json"):
        self.logger = logger
        self.storage_file = storage_file
        self.posted_articles: Dict[str, str] = {}
        self.content_service = ContentExtractionService()
        self._load_posted_articles()
    
    @handle_errors
    def _load_posted_articles(self) -> None:
        """Load previously posted articles from storage."""
        if os.path.exists(self.storage_file):
            with open(self.storage_file, 'r') as f:
                self.posted_articles = json.load(f)
    
    @handle_errors
    def _save_posted_articles(self) -> None:
        """Save posted articles to storage."""
        with open(self.storage_file, 'w') as f:
            json.dump(self.posted_articles, f)
    
    def is_article_posted(self, url: str) -> bool:
        """Check if an article has been posted before."""
        return url in self.posted_articles
    
    def mark_as_posted(self, article: Article) -> None:
        """Mark an article as posted."""
        self.posted_articles[article.url] = datetime.now().isoformat()
        self._save_posted_articles()
    
    @handle_errors
    def cleanup_old_entries(self, days: int = 30) -> None:
        """Remove entries older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        self.posted_articles = {
            url: timestamp
            for url, timestamp in self.posted_articles.items()
            if datetime.fromisoformat(timestamp) > cutoff
        }
        self._save_posted_articles()
    
    @handle_errors
    def get_latest_article(self) -> Optional[Article]:
        """Fetch the latest unposted article from configured RSS feeds."""
        latest_article = None
        latest_time = None
        
        for url in self.FEED_URLS:
            feed = feedparser.parse(url)
            if not feed.entries:
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
        """Extract the full content of an article."""
        return self.content_service.get_article_content(url, self.logger)