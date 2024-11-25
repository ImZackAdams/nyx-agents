import tweepy
import os
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class RateLimiter:
    def __init__(self, limit, interval_hours):
        """
        A class to manage rate-limited actions like posting tweets.
        :param limit: Number of allowed actions per interval.
        :param interval_hours: Time interval in hours between actions.
        """
        self.limit = limit
        self.interval_hours = interval_hours
        self.next_allowed_time = datetime.utcnow()

    def can_post(self):
        """Check if the next action can occur."""
        allowed = datetime.utcnow() >= self.next_allowed_time
        if not allowed:
            logger.info(f"Post blocked by rate limiter. Next allowed time: {self.next_allowed_time}")
        return allowed

    def record_post(self):
        """Record an action and update the next allowed time."""
        self.next_allowed_time = datetime.utcnow() + timedelta(hours=self.interval_hours)


def setup_twitter_client():
    """
    Authenticate with the Twitter API and return a client instance.
    """
    logger.info("Setting up Twitter client...")
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    bearer_token = os.getenv('BEARER_TOKEN')
    access_token = os.getenv('ACCESS_TOKEN')
    access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')

    # Check for missing credentials
    missing_vars = [var for var, value in [
        ("API_KEY", api_key),
        ("API_SECRET", api_secret),
        ("BEARER_TOKEN", bearer_token),
        ("ACCESS_TOKEN", access_token),
        ("ACCESS_TOKEN_SECRET", access_token_secret)
    ] if not value]

    if missing_vars:
        raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

    try:
        client = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        logger.info("Twitter client setup successfully.")
        return client
    except Exception as e:
        logger.error("Failed to set up Twitter client.", exc_info=True)
        raise e


def post_to_twitter(tweet, client, logger):
    """
    Post a tweet using the Twitter API.
    :param tweet: The content of the tweet to be posted.
    """
    try:
        response = client.create_tweet(text=tweet)
        tweet_id = response.data['id']
        logger.info(f"Tweet posted successfully! Tweet ID: {tweet_id}")
        return tweet_id
    except tweepy.errors.TweepyException as e:
        logger.error(f"Failed to post tweet: {str(e)}", exc_info=True)
        return None


def search_replies_to_tweet(client, tweet_id, bot_user_id):
    """
    Search for replies to a specific tweet, excluding the bot's own tweets.
    :param tweet_id: ID of the tweet to search replies for.
    :param bot_user_id: The bot's Twitter user ID.
    """
    try:
        query = f"conversation_id:{tweet_id} -from:{bot_user_id}"
        logger.info(f"Searching replies with query: {query}")
        replies = client.search_recent_tweets(query=query, max_results=10, tweet_fields=["author_id", "text", "id"])
        if replies.data:
            logger.info(f"Found {len(replies.data)} replies.")
            return replies.data
        else:
            logger.info("No replies found.")
            return []
    except tweepy.errors.TweepyException as e:
        logger.error(f"Failed to fetch replies: {str(e)}", exc_info=True)
        return []


def get_last_reply_id(client, tweet_id, bot_user_id):
    """
    Fetch the ID of the last reply to a specific tweet.
    :param tweet_id: ID of the tweet to fetch replies for.
    :param bot_user_id: The bot's Twitter user ID.
    """
    try:
        replies = search_replies_to_tweet(client, tweet_id, bot_user_id)
        if not replies:
            logger.info("No replies found for this tweet.")
            return None

        # Get the most recent reply
        latest_reply = sorted(replies, key=lambda x: x.id, reverse=True)[0]
        logger.info(f"Found latest reply: {latest_reply.text} (ID: {latest_reply.id})")
        return latest_reply.id
    except Exception as e:
        logger.error(f"Error fetching last reply: {str(e)}", exc_info=True)
        return None


def fetch_reply_details(client, reply_id):
    """
    Fetch details of a specific reply by its ID.
    :param reply_id: ID of the reply to fetch details for.
    """
    try:
        logger.info(f"Fetching details for reply ID: {reply_id}")
        reply = client.get_tweet(reply_id, tweet_fields=["text", "author_id"])
        if reply.data:
            logger.info(f"Fetched reply details: {reply.data}")
            return reply.data
        else:
            logger.info("No details found for the given reply ID.")
            return None
    except tweepy.errors.TweepyException as e:
        logger.error(f"Failed to fetch reply details: {str(e)}", exc_info=True)
        return None
