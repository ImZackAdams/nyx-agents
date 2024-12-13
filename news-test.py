# news_fetcher.py
from dataclasses import dataclass
from datetime import datetime
import feedparser
from typing import Optional, Tuple, List
from urllib.parse import urlparse, urlunparse

@dataclass
class Article:
    title: str
    url: str
    content: str
    published_at: datetime

class NewsFetcher:
    FEED_URLS = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/?",
        "https://cointelegraph.com/rss"
    ]
    
    def get_latest_article(self) -> Optional[Tuple[str, str]]:
        latest_article = None
        latest_time = None
        
        for url in self.FEED_URLS:
            feed = feedparser.parse(url)
            if not feed.entries:
                continue
                
            for entry in feed.entries:
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
            content='',  # To be filled by content extractor
            published_at=datetime(*latest_time[:6]) if latest_time else datetime.now()
        )

# content_extractor.py
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from typing import Optional

class ContentExtractor:
    @staticmethod
    def get_full_content(url: str) -> Optional[str]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            )
            page = context.new_page()
            
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                if not response or response.status != 200:
                    return None
                    
                page.wait_for_timeout(3000)
                html = page.content()
                
                soup = BeautifulSoup(html, 'html.parser')
                domain = urlparse(url).netloc.lower()
                
                return ContentExtractor._extract_by_domain(soup, domain)
                
            except Exception as e:
                return None
            finally:
                browser.close()
    
    @staticmethod
    def _extract_by_domain(soup: BeautifulSoup, domain: str) -> Optional[str]:
        if "coindesk.com" in domain:
            return ContentExtractor._extract_coindesk(soup)
        elif "cointelegraph.com" in domain:
            return ContentExtractor._extract_cointelegraph(soup)
        return ContentExtractor._extract_generic(soup)
    
    @staticmethod
    def _extract_coindesk(soup: BeautifulSoup) -> Optional[str]:
        article_body = soup.find("div", class_="article-pharagraphs") or soup.find("article")
        return ContentExtractor._extract_paragraphs(article_body)
    
    @staticmethod
    def _extract_cointelegraph(soup: BeautifulSoup) -> Optional[str]:
        selectors = [
            "div.post-content",
            "div.post-content__text",
            "div.article__body",
            "div.post-page__article-content"
        ]
        
        for selector in selectors:
            if article_body := soup.select_one(selector):
                if text := ContentExtractor._extract_paragraphs(article_body):
                    return text
        
        article_body = soup.find("article") or soup.find("main") or soup.find("body")
        return ContentExtractor._extract_paragraphs(article_body)
    
    @staticmethod
    def _extract_generic(soup: BeautifulSoup) -> Optional[str]:
        article_body = soup.find("article") or soup.find("main") or soup.find("body")
        return ContentExtractor._extract_paragraphs(article_body)
    
    @staticmethod
    def _extract_paragraphs(container) -> Optional[str]:
        if not container:
            return None
        paragraphs = container.find_all("p")
        text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        return text.strip() if text.strip() else None

# summarizer.py
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class SummaryConfig:
    min_length: int
    max_length: int
    personality: str
    hooks: List[str]
    
    @classmethod
    def default(cls) -> 'SummaryConfig':
        return cls(
            min_length=180,
            max_length=280,
            personality="Informative and professional with a touch of excitement",
            hooks=["🚨 Breaking:", "📊 Market Update:", "💡 New Development:"]
        )

class Summarizer:
    def __init__(self, config: SummaryConfig):
        self.config = config
    
    def generate_prompt(self, article: Article) -> str:
        return (
            f"System: You are summarizing a crypto news article. "
            f"Response must be {self.config.min_length}-{self.config.max_length} characters, "
            f"include at least one hashtag and emoji, and focus on the key points.\n\n"
            f"{self.config.personality}\n\n"
            f"Article to summarize:\n"
            f"Title: {article.title}\n\n"
            f"Content:\n{article.content[:800]}\n\n"
            f"Create a single summary that:\n"
            f"1. Captures the key points\n"
            f"2. Uses appropriate market terms\n"
            f"3. Includes strategic emojis\n"
            f"4. Ends with a relevant hashtag"
        )

# main.py
def main():
    # Initialize components
    news_fetcher = NewsFetcher()
    content_extractor = ContentExtractor()
    summarizer = Summarizer(SummaryConfig.default())
    
    # Get latest article
    if article := news_fetcher.get_latest_article():
        # Extract content
        if content := content_extractor.get_full_content(article.url):
            article.content = content
            
            # Generate summary prompt
            prompt = summarizer.generate_prompt(article)
            
            # Here you would use your bot to generate the actual summary
            # summary = bot.generate_response(prompt)
            
            return {
                'title': article.title,
                'url': article.url,
                'prompt': prompt
            }
    
    return None

if __name__ == "__main__":
    main()