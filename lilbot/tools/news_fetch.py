from __future__ import annotations

from typing import Any, Dict

from lilbot.tools.base_tool import Tool
from lilbot.integrations.news.news_service import NewsService


class FetchLatestNewsTool(Tool):
    name = "fetch_latest_news"
    description = "Fetch the latest unposted news article from configured RSS feeds"
    input_schema = {"include_content": "bool"}

    def __init__(self, news_service: NewsService):
        self.news_service = news_service

    def run(self, input_data: Dict[str, Any]) -> Any:
        include_content = bool(input_data.get("include_content", True))
        article = self.news_service.get_latest_article()
        if not article:
            return {"error": "No new articles found"}
        if include_content:
            article.content = self.news_service.get_article_content(article.url)
        return {
            "title": article.title,
            "url": article.url,
            "published_at": article.published_at.isoformat(),
            "content": article.content,
        }
