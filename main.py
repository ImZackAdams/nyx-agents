import os
import schedule
import time
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logging
from bot.twitter_client import setup_twitter_client, post_to_twitter, search_replies_to_tweet, RateLimiter
import logging

# Load environment variables
load_dotenv()


def post_tweet_job(bot, client, logger):
    """Job to post a tweet with a user-provided prompt."""
    try:
        prompt = input("Enter a prompt for the tweet: ").strip()
        if not prompt:
            logger.warning("Prompt is empty. Skipping tweet.")
            return

        tweet = bot.generate_response(prompt)
        post_to_twitter(tweet, client, logger)
    except Exception as e:
        logger.error(f"Error posting tweet: {str(e)}")


def reply_to_last_comment(bot, client, logger, since_id=None):
    """Replies to the last user who commented on the bot's tweet."""
    try:
        # Fetch the bot's user ID from environment variables
        bot_user_id = os.getenv("BOT_USER_ID")
        if not bot_user_id:
            raise ValueError("BOT_USER_ID is not set in the .env file")

        # Fetch the bot's recent tweets
        tweets = client.get_users_tweets(id=bot_user_id, max_results=5)
        if not tweets or not tweets.data:
            logger.info("No recent tweets to fetch replies for.")
            return since_id

        latest_tweet = tweets.data[0]
        tweet_id = latest_tweet.id

        # Fetch replies to the latest tweet
        replies = search_replies_to_tweet(client, tweet_id, bot_user_id)
        if not replies:
            logger.info("No replies to the latest tweet.")
            return since_id

        # Respond to the most recent reply
        # Sort replies by ID (assuming higher ID = more recent)
        latest_reply = sorted(replies, key=lambda x: x.id, reverse=True)[0]

        if since_id and latest_reply.id <= since_id:
            logger.info("No new replies to respond to.")
            return since_id

        reply_text = latest_reply.text
        reply_id = latest_reply.id

        # Generate a reply
        response = bot.generate_response(reply_text)
        reply_message = response  # The bot's reply text without mentioning the user

        # Post the reply using `in_reply_to_tweet_id`
        try:
            client.create_tweet(
                text=reply_message,
                in_reply_to_tweet_id=reply_id
            )
            logger.info(f"Replied to tweet ID {reply_id} successfully!")
        except Exception as e:
            logger.error(f"Failed to post reply: {str(e)}")

        return latest_reply.id
    except Exception as e:
        logger.error(f"Error replying to last comment: {str(e)}")
        return since_id


def main():
    logger = setup_logging()
    bot = PersonalityBot(model_path="./fine_tuned_personality_bot/", logger=logger)
    client = setup_twitter_client()
    rate_limiter_tweet = RateLimiter(limit=1, interval_hours=3)
    rate_limiter_reply = RateLimiter(limit=1, interval_hours=12)

    # Use a global variable to track the latest reply ID
    global since_id
    since_id = None

    # Schedule tasks
    def reply_task():
        global since_id
        since_id = reply_to_last_comment(bot, client, logger, since_id)

    # Run the reply job first
    reply_task()

    # Schedule reply and post tasks
    schedule.every(12).hours.do(reply_task)
    schedule.every(3).hours.do(lambda: post_tweet_job(bot, client, logger))

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
