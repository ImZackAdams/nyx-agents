import json
import os
from datetime import datetime, timedelta
from typing import Dict
import logging
from functools import wraps
from article import Article # type: ignore

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

class ArticleStorage:
    """Handles persistence of posted articles"""
    
    def __init__(self, storage_file: str = "posted_articles.json", logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.storage_file = storage_file
        self.posted_articles: Dict[str, str] = {}
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