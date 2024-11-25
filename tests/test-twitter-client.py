import os
import logging
import tweepy
from dotenv import load_dotenv
from bot.twitter_client import (
    setup_twitter_client,
    post_to_twitter,
    search_replies_to_tweet,
    get_last_reply_id,
    fetch_reply_details
)

# Load environment variables
load_dotenv()

# Configure logger for testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_post_to_twitter(client):
    """Test posting a tweet."""
    logger.info("Testing post_to_twitter...")
    tweet_content = "This is a test tweet! #TestingTwitterAPI"
    tweet_id = post_to_twitter(tweet_content, client, logger)
    if tweet_id:
        logger.info(f"Test Tweet Posted Successfully. Tweet ID: {tweet_id}")
    else:
        logger.error("Failed to post test tweet.")


def test_search_replies_to_tweet(client, tweet_id, bot_user_id):
    """Test fetching replies to a tweet."""
    logger.info("Testing search_replies_to_tweet...")
    replies = search_replies_to_tweet(client, tweet_id, bot_user_id)
    if replies:
        logger.info(f"Fetched {len(replies)} replies:")
        for reply in replies:
            logger.info(f"Reply ID: {reply.id}, Author ID: {reply.author_id}, Text: {reply.text}")
    else:
        logger.info("No replies found for the test tweet.")


def test_get_last_reply_id(client, tweet_id, bot_user_id):
    """Test fetching the most recent reply ID to a tweet."""
    logger.info("Testing get_last_reply_id...")
    reply_id = get_last_reply_id(client, tweet_id, bot_user_id)
    if reply_id:
        logger.info(f"Latest Reply ID: {reply_id}")
    else:
        logger.info("No replies found for the test tweet.")


def test_fetch_reply_details(client, reply_id):
    """Test fetching details of a specific reply."""
    logger.info("Testing fetch_reply_details...")
    reply_details = fetch_reply_details(client, reply_id)
    if reply_details:
        logger.info(f"Fetched Reply Details: {reply_details}")
    else:
        logger.info("Failed to fetch details for the given reply ID.")


def main():
    # Initialize Twitter Client
    logger.info("Setting up Twitter client...")
    client = setup_twitter_client()

    # Replace with known values for testing
    bot_user_id = os.getenv("BOT_USER_ID")  # Bot's Twitter User ID
    test_tweet_id = "1861007253676908999"  # Replace with a real Tweet ID for testing
    test_reply_id = "1861009182771519679"  # Replace with a real Reply ID for testing

    # Uncomment the tests you want to run
    # Test posting a tweet
    # test_post_to_twitter(client)

    # Test fetching replies to a tweet
    test_search_replies_to_tweet(client, test_tweet_id, bot_user_id)

    # Test fetching the most recent reply ID
    # test_get_last_reply_id(client, test_tweet_id, bot_user_id)

    # Test fetching details of a specific reply
    # test_fetch_reply_details(client, test_reply_id)


if __name__ == "__main__":
    main()
