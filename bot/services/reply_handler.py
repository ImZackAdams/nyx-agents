import time
import logging
import os
from typing import Optional
from bot.configs.posting_config import (
    REPLY_DELAY_SECONDS,
    REPLIES_PER_CYCLE,
    INITIAL_REPLY_DELAY,
    REPLY_CYCLE_DELAY,
    REPLY_CYCLES,
    FINAL_CHECK_DELAY,
)


def apply_delay(duration, logger=None):
    """Apply a delay and log it."""
    if logger:
        logger.info(f"Waiting {duration // 60} minutes...")
    time.sleep(duration)


def search_replies_to_tweet(client, tweet_id, bot_user_id, since_id=None, logger=None):
    """Search replies to a specific tweet, excluding those from the bot."""
    query = f"conversation_id:{tweet_id} -from:{bot_user_id}"

    try:
        # Pass `since_id` as a parameter to the method
        results = client.search_recent_tweets(
            query=query,
            tweet_fields=["author_id", "text", "id"],
            since_id=since_id  # Use the since_id parameter correctly
        )
        return results.data or []
    except Exception as e:
        if logger:
            logger.error("Failed to fetch replies.", exc_info=True)
        return []


class ReplyHandler:
    def __init__(self, client, tweet_generator, logger=None):
        self.client = client
        self.tweet_generator = tweet_generator
        self.logger = logger or logging.getLogger(__name__)
        self.bot_user_id = os.getenv("BOT_USER_ID")
        self.last_processed_id = None  # Track the last processed reply ID

    def process_replies(self, tweet_id: str, since_id: Optional[str] = None) -> Optional[str]:
        """Process new replies and respond."""
        try:
            replies = search_replies_to_tweet(
                self.client, tweet_id, self.bot_user_id, since_id=since_id, logger=self.logger
            )
            if not replies:
                self.logger.info("No new replies found.")
                return since_id

            # Process replies in chronological order
            for reply in sorted(replies, key=lambda x: x.id):
                if self.last_processed_id and reply.id <= self.last_processed_id:
                    self.logger.info(f"Skipping already processed reply ID: {reply.id}")
                    continue

                try:
                    self.logger.info(f"Processing reply: {reply.text}")
                    response = self.tweet_generator.generate_tweet(reply.text)
                    if response:
                        self.client.create_tweet(text=response, in_reply_to_tweet_id=reply.id)
                        self.logger.info(f"Replied to tweet ID: {reply.id}")

                        # Update the last processed ID
                        self.last_processed_id = reply.id
                    else:
                        self.logger.warning(f"Generated response was empty for tweet ID: {reply.id}")

                    time.sleep(REPLY_DELAY_SECONDS)
                except Exception as e:
                    self.logger.error(f"Error replying to tweet {reply.id}: {e}", exc_info=True)

            # Return the ID of the most recent reply processed
            return max(reply.id for reply in replies if reply.id > (since_id or 0))
        except Exception as e:
            self.logger.error(f"Error processing replies: {e}", exc_info=True)
            return since_id

    def monitor_tweet(self, tweet_id: str):
        """Monitor a tweet for replies."""
        since_id = self.last_processed_id  # Start from the last known reply ID
        delays = [INITIAL_REPLY_DELAY] + [REPLY_CYCLE_DELAY] * REPLY_CYCLES + [FINAL_CHECK_DELAY]
        for delay in delays:
            apply_delay(delay, self.logger)
            since_id = self.process_replies(tweet_id, since_id)
        self.logger.info("Reply monitoring complete.")
