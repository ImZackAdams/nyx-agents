from __future__ import annotations

import os
from typing import Optional
import tweepy


class TwitterClient:
    """Handles raw Twitter API interactions"""

    def __init__(self):
        self.client = self._setup_client()

    def _setup_client(self) -> tweepy.Client:
        credentials = self._get_credentials()
        return tweepy.Client(
            bearer_token=credentials["bearer_token"],
            consumer_key=credentials["api_key"],
            consumer_secret=credentials["api_secret"],
            access_token=credentials["access_token"],
            access_token_secret=credentials["access_token_secret"],
        )

    def _get_credentials(self) -> dict:
        credentials = {
            "api_key": os.getenv("API_KEY") or os.getenv("TWITTER_API_KEY"),
            "api_secret": os.getenv("API_SECRET") or os.getenv("TWITTER_API_SECRET"),
            "bearer_token": os.getenv("BEARER_TOKEN") or os.getenv("TWITTER_BEARER_TOKEN"),
            "access_token": os.getenv("ACCESS_TOKEN") or os.getenv("TWITTER_ACCESS_TOKEN"),
            "access_token_secret": os.getenv("ACCESS_TOKEN_SECRET") or os.getenv("TWITTER_ACCESS_SECRET"),
        }
        if not all(credentials.values()):
            raise ValueError("Missing Twitter API credentials in environment variables.")
        return credentials

    def create_tweet(self, text: str) -> Optional[str]:
        response = self.client.create_tweet(text=text)
        return response.data.get("id")
