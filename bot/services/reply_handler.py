import time
import logging
import os
import json
from typing import Optional, List, Dict
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
        results = client.search_recent_tweets(
            query=query,
            tweet_fields=["author_id", "text", "id"],
            since_id=since_id
        )
        return results.data or []
    except Exception as e:
        if logger:
            logger.error(f"Failed to fetch replies for tweet ID {tweet_id}.", exc_info=True)
        return []


class ReplyHandler:
    def __init__(self, client, tweet_generator, logger=None, state_file="reply_state.json"):
        self.client = client
        self.tweet_generator = tweet_generator
        self.logger = logger or logging.getLogger(__name__)
        self.bot_user_id = os.getenv("BOT_USER_ID")
        self.state_file = state_file
        self.last_processed_ids = self._load_state()

    def _load_state(self) -> Dict[str, Optional[str]]:
        """Load the last processed IDs from a JSON file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as file:
                    return json.load(file)
            except Exception as e:
                self.logger.error(f"Error loading state file: {e}")
        return {}

    def _save_state(self) -> None:
        """Save the last processed IDs to a JSON file."""
        try:
            with open(self.state_file, "w") as file:
                json.dump(self.last_processed_ids, file)
            self.logger.info("Reply state saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving state file: {e}")

    def process_replies(self, tweet_id: str, since_id: Optional[str] = None) -> Optional[str]:
        """Process new replies for a single tweet and respond."""
        try:
            replies = search_replies_to_tweet(
                self.client, tweet_id, self.bot_user_id, since_id=since_id, logger=self.logger
            )
            if not replies:
                self.logger.info(f"No new replies found for tweet ID {tweet_id}.")
                return since_id

            # Track the maximum reply ID processed
            max_reply_id = since_id or 0

            for reply in sorted(replies, key=lambda x: x.id):
                if reply.id <= max_reply_id:
                    self.logger.info(f"Skipping already processed reply ID: {reply.id} for tweet ID {tweet_id}.")
                    continue

                try:
                    self.logger.info(f"Processing reply: {reply.text} for tweet ID {tweet_id}.")
                    response = self.tweet_generator.generate_tweet(reply.text)
                    if response:
                        self.client.create_tweet(text=response, in_reply_to_tweet_id=reply.id)
                        self.logger.info(f"Replied to tweet ID: {reply.id} for original tweet {tweet_id}.")
                        max_reply_id = max(max_reply_id, reply.id)  # Update max_reply_id
                        self._save_state()  # Persist state after updating
                    else:
                        self.logger.warning(f"Generated response was empty for reply ID: {reply.id}.")

                    time.sleep(REPLY_DELAY_SECONDS)
                except Exception as e:
                    self.logger.error(f"Error replying to tweet {reply.id}: {e}", exc_info=True)

            return max_reply_id
        except Exception as e:
            self.logger.error(f"Error processing replies for tweet ID {tweet_id}: {e}", exc_info=True)
            return since_id

    def monitor_tweets(self, tweet_ids: List[str]):
        """Monitor multiple tweets for replies."""
        delays = [INITIAL_REPLY_DELAY] + [REPLY_CYCLE_DELAY] * REPLY_CYCLES + [FINAL_CHECK_DELAY]
        self.logger.info(f"Monitoring tweets: {tweet_ids}")

        # Ensure all tweet IDs are tracked
        for tweet_id in tweet_ids:
            if tweet_id not in self.last_processed_ids:
                self.last_processed_ids[tweet_id] = None

        for delay in delays:
            apply_delay(delay, self.logger)
            for tweet_id in tweet_ids:
                since_id = self.last_processed_ids.get(tweet_id)
                new_since_id = self.process_replies(tweet_id, since_id)
                if new_since_id:
                    self.last_processed_ids[tweet_id] = new_since_id

        self.logger.info("Reply monitoring complete for all tweets.")
        self._save_state()
