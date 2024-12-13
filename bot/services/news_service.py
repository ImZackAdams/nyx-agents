from dataclasses import dataclass
from datetime import datetime
import feedparser
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse
import random

@dataclass
class Article:
    title: str
    url: str
    content: str = ''
    published_at: Optional[datetime] = None

class NewsService:
    FEED_URLS = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/?",
        "https://cointelegraph.com/rss"
    ]
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def get_latest_article(self) -> Optional[Article]:
        """Fetch the latest article from configured RSS feeds."""
        latest_article = None
        latest_time = None
        
        for url in self.FEED_URLS:
            try:
                feed = feedparser.parse(url)
                if not feed.entries:
                    continue
                    
                for entry in feed.entries:
                    pub_time = entry.get('published_parsed') or entry.get('updated_parsed')
                    if pub_time and (latest_time is None or pub_time > latest_time):
                        latest_time = pub_time
                        latest_article = entry
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error fetching from {url}: {e}")
                continue
        
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
        """Extract the full content of an article using Playwright."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            )
            page = context.new_page()
            
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                if not response or response.status != 200:
                    if self.logger:
                        self.logger.error(f"Failed to fetch {url}: Status {response.status if response else 'No Response'}")
                    return None
                    
                page.wait_for_timeout(3000)
                html = page.content()
                
                soup = BeautifulSoup(html, 'html.parser')
                domain = urlparse(url).netloc.lower()
                
                return self._extract_content_by_domain(soup, domain)
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error extracting content from {url}: {e}")
                return None
            finally:
                browser.close()
    
    def _extract_content_by_domain(self, soup: BeautifulSoup, domain: str) -> Optional[str]:
        """Extract content based on the specific domain."""
        if "coindesk.com" in domain:
            return self._extract_coindesk(soup)
        elif "cointelegraph.com" in domain:
            return self._extract_cointelegraph(soup)
        return self._extract_generic(soup)
    
    def _extract_coindesk(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content specifically from CoinDesk articles."""
        article_body = soup.find("div", class_="article-pharagraphs") or soup.find("article")
        return self._extract_paragraphs(article_body)
    
    def _extract_cointelegraph(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content specifically from CoinTelegraph articles."""
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
    
    def _extract_generic(self, soup: BeautifulSoup) -> Optional[str]:
        """Generic content extraction for unknown domains."""
        article_body = soup.find("article") or soup.find("main") or soup.find("body")
        return self._extract_paragraphs(article_body)
    
    def _extract_paragraphs(self, container) -> Optional[str]:
        """Extract and clean text from paragraph elements."""
        if not container:
            return None
        paragraphs = container.find_all("p")
        text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        return text.strip() if text.strip() else None

    def generate_summary_prompt(self, article: Article, style_config) -> str:
        """Generate the summary prompt using the style configuration."""
        min_len, max_len = style_config.get_length_constraints()
        personality = style_config.get_personality_prompt()
        hooks = style_config.get_appropriate_hooks()
        hook = random.choice(hooks) if hooks else ""
        
        return (
            f"System: You are summarizing a crypto news article. "
            f"Response must be {min_len}-{max_len} characters, "
            f"include at least one hashtag and emoji, and focus on the key points.\n\n"
            f"{personality}\n\n"
            f"Article to summarize:\n"
            f"Title: {article.title}\n\n"
            f"Content:\n{article.content[:800]}\n\n"
            f"Create a single summary that:\n"
            f"1. Captures the key points\n"
            f"2. Uses appropriate market terms\n"
            f"3. Includes strategic emojis\n"
            f"4. Ends with a relevant hashtag"
        )