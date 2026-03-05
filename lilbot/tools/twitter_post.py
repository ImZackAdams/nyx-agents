from __future__ import annotations

from typing import Any, Dict

from lilbot.tools.base_tool import Tool
from lilbot.integrations.twitter.client import TwitterClient


class PostTweetTool(Tool):
    name = "post_tweet"
    description = "Post a tweet to Twitter/X"
    input_schema = {"text": "string"}
    risky = True

    def __init__(self, client: TwitterClient):
        self.client = client

    def run(self, input_data: Dict[str, Any]) -> Any:
        text = input_data.get("text", "").strip()
        if not text:
            return {"error": "text is required"}
        tweet_id = self.client.create_tweet(text=text)
        return {"tweet_id": tweet_id}
