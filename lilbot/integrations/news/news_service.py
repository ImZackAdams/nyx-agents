from __future__ import annotations

import feedparser
import os
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urlunparse
import logging
from functools import wraps

from .extractors import ContentExtractionService
from .storage import ArticleStorage
from .article import Article

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def handle_errors(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            if hasattr(self, "logger") and self.logger:
                self.logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return None
    return wrapper


class NewsService:
    """Service for fetching and processing news articles"""

    def __init__(self, storage_file: str = "posted_articles.json", logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.storage = ArticleStorage(storage_file, logger=self.logger)
        self.content_service = ContentExtractionService(logger=self.logger)
        self.feed_urls = [
            url.strip() for url in os.getenv("NEWS_FEEDS", "").split(",") if url.strip()
        ]

    @handle_errors
    def get_latest_article(self) -> Optional[Article]:
        if not self.feed_urls:
            self.logger.info("No NEWS_FEEDS configured; skipping news fetch.")
            return None
        latest_article = None
        latest_time = None

        for url in self.feed_urls:
            self.logger.debug(f"Fetching RSS feed: {url}")
            feed = feedparser.parse(url)
            if not feed.entries:
                self.logger.warning(f"No entries found in feed: {url}")
                continue

            for entry in feed.entries:
                article_url = entry.get("link", "")
                parsed = urlparse(article_url)
                clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

                if self.storage.is_article_posted(clean_url):
                    continue

                pub_time = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub_time and (latest_time is None or pub_time > latest_time):
                    latest_time = pub_time
                    latest_article = entry

        if not latest_article:
            self.logger.info("No new articles found")
            return None

        title = latest_article.get("title", "")
        article_url = latest_article.get("link", "")
        parsed = urlparse(article_url)
        clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

        return Article(
            title=title,
            url=clean_url,
            published_at=datetime(*latest_time[:6]) if latest_time else datetime.now(),
        )

    def get_article_content(self, url: str) -> Optional[str]:
        return self.content_service.get_article_content(url, self.logger)

    def mark_article_as_posted(self, article: Article) -> None:
        self.storage.mark_as_posted(article)
        self.logger.info(f"Article marked as posted: {article.title}")

    def cleanup_old_articles(self, days: int = 30) -> None:
        self.storage.cleanup_old_entries(days)
