# new_src/api/twitter/client.py
import os
import tweepy
from typing import Optional

class TwitterClient:
    """Handles raw Twitter API interactions"""
    
    def __init__(self):
        self.client = self._setup_client()
    
    def _setup_client(self) -> tweepy.Client:
        """Initialize Twitter API client with credentials"""
        credentials = self._get_credentials()
        
        return tweepy.Client(
            bearer_token=credentials["bearer_token"],
            consumer_key=credentials["api_key"],
            consumer_secret=credentials["api_secret"],
            access_token=credentials["access_token"],
            access_token_secret=credentials["access_token_secret"]
        )
    
    def _get_credentials(self) -> dict:
        """Get Twitter API credentials from environment variables"""
        credentials = {
            "api_key": os.getenv("API_KEY"),
            "api_secret": os.getenv("API_SECRET"),
            "bearer_token": os.getenv("BEARER_TOKEN"),
            "access_token": os.getenv("ACCESS_TOKEN"),
            "access_token_secret": os.getenv("ACCESS_TOKEN_SECRET")
        }
        
        if not all(credentials.values()):
            raise ValueError("Missing Twitter API credentials in environment variables.")
            
        return credentials

    def create_tweet(self, text: str) -> Optional[str]:
        """Create a tweet and return its ID"""
        try:
            response = self.client.create_tweet(text=text)
            return response.data.get('id')
        except Exception as e:
            raise Exception(f"Failed to post tweet: {e}")