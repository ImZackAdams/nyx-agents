import tweepy
import os
import logging

logger = logging.getLogger(__name__)


def setup_twitter_client():
    """
    Authenticate with the Twitter API and return a Tweepy client instance.
    """
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    bearer_token = os.getenv('BEARER_TOKEN')
    access_token = os.getenv('ACCESS_TOKEN')
    access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')

    if not all([api_key, api_secret, bearer_token, access_token, access_token_secret]):
        raise ValueError("Missing Twitter API credentials in environment variables.")

    return tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )


def post_image_with_tweet(client, api, tweet_text, image_path, logger):
    """
    Posts a tweet with an image attachment.
    
    Args:
        client: Twitter v2 API client
        api: Twitter v1.1 API instance
        tweet_text: Text content for the tweet
        image_path: Path to the image file
        logger: Logger instance
    """
    try:
        # Upload media using v1.1 API
        media = api.media_upload(image_path)
        logger.info(f"Image uploaded. Media ID: {media.media_id}")
        
        # Create tweet with media using v2 API
        # Convert media_id to string as required by v2 API
        result = client.create_tweet(
            text=tweet_text, 
            media_ids=[str(media.media_id)]
        )
        logger.info("Tweet with image posted successfully.")
        return result.data.get('id')
        
    except Exception as e:
        logger.error("Failed to post tweet with image.", exc_info=True)
        return None


def search_replies_to_tweet(client, tweet_id, bot_user_id):
    """
    Search replies to a specific tweet, excluding those from the bot.
    """
    query = f"conversation_id:{tweet_id} -from:{bot_user_id}"
    try:
        results = client.search_recent_tweets(query=query, tweet_fields=["author_id", "text", "id"])
        return results.data or []
    except Exception as e:
        logger.error("Failed to fetch replies.", exc_info=True)
        return []