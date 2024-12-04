import os
import time
import logging
from typing import Optional
from bot.twitter_client import search_replies_to_tweet

class ReplyHandler:
    """Handles monitoring and responding to replies on tweets."""
    
    def __init__(self, client, tweet_generator, logger: Optional[logging.Logger] = None):
        self.client = client
        self.tweet_generator = tweet_generator
        self.logger = logger or logging.getLogger(__name__)
        self.bot_user_id = os.getenv("BOT_USER_ID")
        self.reply_delay = 2  # seconds between replies
        
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
        """Process new replies to a tweet and respond to them.
        
        Args:
            tweet_id: The ID of the tweet to check replies for
            since_id: Only process replies newer than this ID
            
        Returns:
            The ID of the latest reply processed, or None if no replies were processed
        """
        try:
            self.logger.info(f"Checking replies for tweet {tweet_id}")
            new_replies = self._get_new_replies(tweet_id, since_id)
            
            if not new_replies:
                self.logger.info("No new replies found")
                return since_id

            # Take the last 3 replies to process
            latest_replies = new_replies[-3:]
            
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
                    
                    # Sleep between replies to avoid rate limits
                    time.sleep(self.reply_delay)
                    
                except Exception as e:
                    self.logger.error(f"Error replying to tweet {reply.id}: {str(e)}")
                    continue

            return max(reply.id for reply in latest_replies)

        except Exception as e:
            self.logger.error(f"Error in reply process: {str(e)}", exc_info=True)
            return since_id

    def monitor_tweet(self, tweet_id: str, cycles: int = 3, cycle_interval: int = 900) -> None:
        """Monitor a tweet for replies over multiple cycles.
        
        Args:
            tweet_id: The ID of the tweet to monitor
            cycles: Number of cycles to monitor for (default: 3)
            cycle_interval: Seconds between cycles (default: 900 [15 minutes])
        """
        since_id = None
        
        # Wait initial period before starting reply cycles
        initial_wait = 600  # 10 minutes
        self.logger.info(f"Waiting {initial_wait // 60} minutes before starting reply cycles...")
        time.sleep(initial_wait)
        
        for cycle in range(cycles):
            self.logger.info(f"Starting reply cycle {cycle + 1}/{cycles}")
            since_id = self.process_replies(tweet_id, since_id)
            self.logger.info(f"Completed reply cycle {cycle + 1}")
            
            if cycle < cycles - 1:  # Don't sleep after the last cycle
                self.logger.info(f"Sleeping for {cycle_interval // 60} minutes...")
                time.sleep(cycle_interval)