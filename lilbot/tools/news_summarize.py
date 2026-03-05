from __future__ import annotations

from typing import Any, Dict

from lilbot.tools.base_tool import Tool
from lilbot.integrations.news.news_service import NewsService
from lilbot.llm.provider import LLMProvider


class SummarizeLatestNewsTool(Tool):
    name = "summarize_latest_news"
    description = "Fetch the latest article and summarize it"
    input_schema = {"max_chars": "int"}

    def __init__(self, news_service: NewsService, llm: LLMProvider):
        self.news_service = news_service
        self.llm = llm

    def run(self, input_data: Dict[str, Any]) -> Any:
        max_chars = int(input_data.get("max_chars", 320))
        article = self.news_service.get_latest_article()
        if not article:
            return {"error": "No new articles found"}

        article.content = self.news_service.get_article_content(article.url) or ""
        if not article.content:
            return {"error": "Failed to extract article content", "url": article.url}

        prompt = (
            "Summarize the article in a concise, factual paragraph. "
            f"Keep it under {max_chars} characters.\n\n"
            f"Title: {article.title}\n"
            f"Content: {article.content[:2000]}\n\n"
            "FINAL:"
        )

        summary = self.llm.generate(prompt)
        summary = summary.replace("FINAL:", "").strip()

        if len(summary) > max_chars:
            summary = summary[:max_chars].rsplit(" ", 1)[0].strip()

        return {
            "title": article.title,
            "url": article.url,
            "summary": summary,
        }
