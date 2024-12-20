import json
import os
from typing import Set, Dict
from datetime import datetime, timedelta

class NewsTracker:
    def __init__(self, storage_file: str = "posted_articles.json"):
        self.storage_file = storage_file
        self.posted_articles: Dict[str, str] = {}  # url -> timestamp
        self._load_posted_articles()
        
    def _load_posted_articles(self) -> None:
        """Load previously posted articles from storage."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    self.posted_articles = json.load(f)
            except Exception:
                self.posted_articles = {}
    
    def _save_posted_articles(self) -> None:
        """Save posted articles to storage."""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.posted_articles, f)
        except Exception as e:
            print(f"Error saving posted articles: {e}")
    
    def is_article_posted(self, url: str) -> bool:
        """Check if an article has been posted before."""
        return url in self.posted_articles
    
    def mark_as_posted(self, url: str) -> None:
        """Mark an article as posted."""
        self.posted_articles[url] = datetime.now().isoformat()
        self._save_posted_articles()
    
    def cleanup_old_entries(self, days: int = 30) -> None:
        """Remove entries older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        self.posted_articles = {
            url: timestamp
            for url, timestamp in self.posted_articles.items()
            if datetime.fromisoformat(timestamp) > cutoff
        }
        self._save_posted_articles()