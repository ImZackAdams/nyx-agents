import os
import tweepy


def setup_twitter_client():
    """Authenticate with the Twitter API and return a Tweepy client instance."""
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    bearer_token = os.getenv("BEARER_TOKEN")
    access_token = os.getenv("ACCESS_TOKEN")
    access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")
    
    if not all([api_key, api_secret, bearer_token, access_token, access_token_secret]):
        raise ValueError("Missing Twitter API credentials in environment variables.")
    
    return tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )
