import tweepy
import os
from datetime import datetime, timedelta


class RateLimiter:
    def __init__(self, limit, interval_hours):
        self.limit = limit
        self.interval_hours = interval_hours
        self.next_allowed_time = datetime.utcnow()

    def can_post(self):
        """Check if the next action can occur."""
        return datetime.utcnow() >= self.next_allowed_time

    def record_post(self):
        """Record an action and update the next allowed time."""
        self.next_allowed_time = datetime.utcnow() + timedelta(hours=self.interval_hours)


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


def search_replies_to_tweet(client, tweet_id, bot_user_id):
    """
    Search for replies to a specific tweet, excluding the bot's own tweets.
    """
    try:
        query = f"conversation_id:{tweet_id} -from:{bot_user_id}"
        replies = client.search_recent_tweets(query=query, max_results=10, tweet_fields=["author_id", "text", "id"])
        return replies.data if replies.data else []
    except tweepy.TweepError as e:
        logger.error(f"Failed to fetch replies: {str(e)}")
        return []


def get_last_reply_id(client, tweet_id, bot_user_id, logger):
    """
    Fetch the ID of the last reply to a specific tweet.
    """
    try:
        # Search for replies to the tweet
        replies = search_replies_to_tweet(client, tweet_id, bot_user_id)
        if not replies:
            logger.info("No replies found for this tweet.")
            return None

        # Get the most recent reply
        latest_reply = replies[0]
        logger.info(f"Found latest reply: {latest_reply.text} (ID: {latest_reply.id})")
        return latest_reply.id
    except Exception as e:
        logger.error(f"Error fetching last reply: {str(e)}")
        return None


def fetch_reply_details(client, reply_id, logger):
    """
    Fetch details of a specific reply by its ID.
    """
    try:
        reply = client.get_tweet(reply_id, tweet_fields=["text", "author_id"])
        if reply.data:
            logger.info(f"Fetched reply details: {reply.data}")
            return reply.data
        else:
            logger.info("No details found for the given reply ID.")
            return None
    except tweepy.TweepError as e:
        logger.error(f"Failed to fetch reply details: {str(e)}")
        return None
