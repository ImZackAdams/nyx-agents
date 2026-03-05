from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    title: str
    url: str
    published_at: datetime
    content: Optional[str] = None
