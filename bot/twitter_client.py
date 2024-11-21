import tweepy
import os

def setup_twitter_client():
    """Authenticate with Twitter API and return a client."""
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    bearer_token = os.getenv('BEARER_TOKEN')
    access_token = os.getenv('ACCESS_TOKEN')
    access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')

    return tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

def post_to_twitter(tweet, client, logger):
    """Post a tweet using the Twitter API."""
    try:
        client.create_tweet(text=tweet)
        logger.info("Tweet posted successfully!")
    except tweepy.TweepError as e:
        logger.error(f"Failed to post tweet: {str(e)}")
