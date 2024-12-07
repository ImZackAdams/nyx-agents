import os
import time
import random
import logging
import warnings
import tweepy
from typing import Optional  # Add this line
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logger
from bot.services.utils import setup_twitter_client
from bot.services.rate_limiter import RateLimitTracker
from bot.prompts import get_all_prompts, FALLBACK_TWEETS
from bot.services.tweet_generator import TweetGenerator
from bot.services.reply_handler import ReplyHandler
from bot.services.meme_handler import MemeHandler
from bot.configs.posting_config import (
    POST_COOLDOWN,
    RETRY_DELAY,
    MAX_PROMPT_ATTEMPTS
)


class TwitterBot:
    """Main Twitter bot implementation."""
    
    def __init__(self):
        self.logger = setup_logger("athena")
        self.logger.info("Starting the bot...")
        self._initialize_components()
        
    def _initialize_components(self) -> None:
        """Initialize all required components and connections."""
        self._validate_env_variables()
        
        # Set up main components and API
        self.client = setup_twitter_client()
        self.api = tweepy.API(tweepy.OAuth1UserHandler(
            consumer_key=os.getenv('API_KEY'),
            consumer_secret=os.getenv('API_SECRET'),
            access_token=os.getenv('ACCESS_TOKEN'),
            access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
        ))
        self.rate_limit_tracker = RateLimitTracker()
        
        # Initialize personality bot and handlers
        personality_bot = PersonalityBot(
            model_path="athena_8bit_model", 
            logger=self.logger
        )
        
        self.tweet_generator = TweetGenerator(personality_bot, logger=self.logger)  # Fixed
        self.reply_handler = ReplyHandler(self.client, self.tweet_generator, logger=self.logger)
        self.meme_handler = MemeHandler(client=self.client, api=self.api, logger=self.logger)

    def _validate_env_variables(self) -> None:
        """Ensure all required environment variables are set."""
        required_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BOT_USER_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def post_tweet(self) -> Optional[str]:
        """Post a new tweet, either text or meme."""
        self.logger.info("Starting tweet posting process...")
        
        try:
            # Check if we should post a meme
            if self.meme_handler.should_post_meme():
                self.logger.info("Attempting to post a meme...")
                tweet_id = self.meme_handler.post_meme()
                if tweet_id:
                    return tweet_id
                self.logger.warning("Meme posting failed, falling back to text tweet")
            
            # Handle text tweet
            prompts = get_all_prompts()
            all_prompts = [p for prompts_list in prompts.values() for p in prompts_list]
            
            # Try prompts up to MAX_PROMPT_ATTEMPTS times
            for attempt in range(MAX_PROMPT_ATTEMPTS):
                if not all_prompts:
                    break
                    
                prompt = random.choice(all_prompts)
                all_prompts.remove(prompt)
                
                self.logger.info(f"Trying prompt {attempt + 1}/{MAX_PROMPT_ATTEMPTS}: {prompt}")
                tweet = self.tweet_generator.generate_tweet(prompt)
                
                if tweet:
                    result = self.client.create_tweet(text=tweet)
                    return result.data.get('id')
                    
                self.logger.warning("Tweet generation failed, trying next prompt...")
            
            # If all prompts fail, use fallback
            tweet = random.choice(FALLBACK_TWEETS)
            self.logger.info(f"Using fallback tweet: {tweet}")
            result = self.client.create_tweet(text=tweet)
            return result.data.get('id')

        except Exception as e:
            self.logger.error(f"Error posting tweet: {str(e)}", exc_info=True)
            return None

    def run(self):
        """Main bot running loop."""
        while True:
            try:
                self.logger.info("Starting new bot cycle...")
                tweet_id = self.post_tweet()
                
                if tweet_id:
                    self.logger.info(f"Posted tweet: {tweet_id}")
                    
                    # Monitor for replies (this will do the 3 cycles + 60 min final check)
                    self.reply_handler.monitor_tweet(tweet_id)
                    
                    # After final check, immediately start next cycle
                    self.logger.info("Reply monitoring complete")
                    # No sleep here - go straight to next tweet
                else:
                    self.logger.error("Tweet posting failed. Retrying after delay...")
                    time.sleep(RETRY_DELAY)

            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                self.logger.info(f"Retrying after {RETRY_DELAY // 60} minutes...")
                time.sleep(RETRY_DELAY)

def main():
    """Main entry point for the bot."""
    try:
        # Suppress specific warnings
        warnings.filterwarnings("ignore", message=".*MatMul8bitLt.*")
        warnings.filterwarnings("ignore", message=".*quantization_config.*")
        warnings.filterwarnings("ignore", message=".*Unused kwargs.*")

        # Load environment variables
        load_dotenv()
        
        bot = TwitterBot()
        bot.run()
    except Exception as e:
        logging.error("Fatal error in main", exc_info=True)
        raise

if __name__ == "__main__":
    main()
