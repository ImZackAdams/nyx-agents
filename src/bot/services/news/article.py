from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Article:
    """Represents a news article"""
    title: str
    url: str
    content: str = ''
    published_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.published_at:
            self.published_at = datetime.now()