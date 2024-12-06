import os
import time
import logging
from typing import Optional
from bot.twitter_client import search_replies_to_tweet
from bot.configs.config import (
    REPLY_DELAY_SECONDS,
    REPLIES_PER_CYCLE,
    INITIAL_REPLY_DELAY,
    REPLY_CYCLE_DELAY,
    REPLY_CYCLES,
    FINAL_CHECK_DELAY
)

class ReplyHandler:
    """Handles monitoring and responding to replies on tweets."""
    
    def __init__(self, client, tweet_generator, logger: Optional[logging.Logger] = None):
        self.client = client
        self.tweet_generator = tweet_generator
        self.logger = logger or logging.getLogger(__name__)
        self.bot_user_id = os.getenv("BOT_USER_ID")

    def _get_new_replies(self, tweet_id: str, since_id: Optional[str] = None):
        """Get new replies to a tweet, sorted by ID."""
        try:
            replies = search_replies_to_tweet(self.client, tweet_id, self.bot_user_id)
            if not replies:
                return []
                
            sorted_replies = sorted(replies, key=lambda x: x.id)
            if since_id:
                return [reply for reply in sorted_replies if reply.id > since_id]
            return sorted_replies
            
        except Exception as e:
            self.logger.error(f"Error fetching replies: {str(e)}")
            return []

    def _generate_reply(self, tweet_text: str) -> str:
        """Generate a reply to a tweet."""
        try:
            response = self.tweet_generator.generate_tweet(tweet_text)
            if not response:
                return None
            return response
        except Exception as e:
            self.logger.error(f"Error generating reply: {str(e)}")
            return None

    def process_replies(self, tweet_id: str, since_id: Optional[str] = None) -> Optional[str]:
        """Process new replies to a tweet and respond to them."""
        try:
            self.logger.info(f"Checking replies for tweet {tweet_id}")
            new_replies = self._get_new_replies(tweet_id, since_id)
            
            if not new_replies:
                self.logger.info("No new replies found")
                return since_id

            latest_replies = new_replies[-REPLIES_PER_CYCLE:]
            
            for reply in latest_replies:
                try:
                    self.logger.info(f"Processing reply: {reply.text}")
                    response = self._generate_reply(reply.text)
                    
                    if not response:
                        response = f"@{reply.author.username} Thanks for engaging! 🤔"
                    
                    self.client.create_tweet(
                        text=response,
                        in_reply_to_tweet_id=reply.id
                    )
                    
                    time.sleep(REPLY_DELAY_SECONDS)
                    
                except Exception as e:
                    self.logger.error(f"Error replying to tweet {reply.id}: {str(e)}")
                    continue

            return max(reply.id for reply in latest_replies)

        except Exception as e:
            self.logger.error(f"Error in reply process: {str(e)}", exc_info=True)
            return since_id

    def monitor_tweet(self, tweet_id: str) -> None:
        """Monitor a tweet for replies following specific timing pattern.
        
        Cycle:
        1. Wait 10 minutes after posting
        2. Check replies
        3. Do 3 cycles of 15-minute checks
        4. Wait 1 hour
        5. Final check
        """
        since_id = None
        
        # Initial 10-minute wait
        self.logger.info(f"Waiting {INITIAL_REPLY_DELAY // 60} minutes before first reply check...")
        time.sleep(INITIAL_REPLY_DELAY)
        
        # First reply check
        self.logger.info("Performing initial reply check...")
        since_id = self.process_replies(tweet_id, since_id)
        
        # 3 cycles of 15-minute checks
        for cycle in range(REPLY_CYCLES):
            self.logger.info(f"Waiting {REPLY_CYCLE_DELAY // 60} minutes before cycle {cycle + 1}/{REPLY_CYCLES}")
            time.sleep(REPLY_CYCLE_DELAY)
            
            self.logger.info(f"Starting reply cycle {cycle + 1}")
            since_id = self.process_replies(tweet_id, since_id)
            self.logger.info(f"Completed reply cycle {cycle + 1}")
        
        # Final check after 1 hour
        self.logger.info(f"Waiting {FINAL_CHECK_DELAY // 60} minutes before final check...")
        time.sleep(FINAL_CHECK_DELAY)
        
        self.logger.info("Performing final reply check...")
        self.process_replies(tweet_id, since_id)
        self.logger.info("Reply monitoring complete")