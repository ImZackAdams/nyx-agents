"""
Main entry point for the Twitter bot.

This module initializes and runs the Twitter bot, handling all core orchestration
and component management. It sets up logging, initializes services, and maintains
the main execution loop.
"""

import time
import warnings
import logging
from typing import List
from dotenv import load_dotenv

# Bot utilities and initialization
from bot.utilities.logger import setup_logger
from bot.services.utils import setup_twitter_client
from bot.initializers import (
    validate_env_variables,
    initialize_diffusion_pipeline,
    setup_twitter_api
)

# Core services and components
from bot.services.posting_service import PostingService
from bot.bot import PersonalityBot
from bot.posters.tweet_generator import TweetGenerator
from bot.posters.meme_poster import MemePoster
from bot.posters.reply_poster import ReplyPoster
from bot.services.news.news_service import NewsService

# Configuration
from bot.configs.posting_config import POST_COOLDOWN, RETRY_DELAY


class TwitterBot:
    """
    Main Twitter Bot orchestrator.
    
    This class handles the initialization and coordination of all bot components,
    including the posting service, personality bot, and various handlers.
    """

    def __init__(self):
        """Initialize the TwitterBot with all necessary components."""
        self.logger = setup_logger("athena")
        self.logger.info("Initializing TwitterBot...")
        self._initialize_components()

    def _initialize_components(self) -> None:
        """
        Initialize all bot components and services.
        
        This includes Twitter clients, core services, handlers, and the
        posting service. Any initialization errors are logged and re-raised.
        """
        try:
            # Validate environment
            validate_env_variables(self.logger)
            
            # Initialize Twitter clients
            self.client = setup_twitter_client()
            self.api = setup_twitter_api()
            
            # Initialize core services
            personality_bot = PersonalityBot(
                model_path="./mistral_qlora_finetuned",
                logger=self.logger
            )
            tweet_generator = TweetGenerator(
                personality_bot, 
                logger=self.logger
            )
            
            # Initialize diffusion pipeline
            self.pipe = initialize_diffusion_pipeline(self.logger)
            
            # Initialize specialized handlers
            self.reply_handler = ReplyPoster(
                self.client, 
                tweet_generator,
                logger=self.logger,
                pipe=self.pipe,
                api=self.api
            )
            meme_handler = MemePoster(
                client=self.client,
                api=self.api,
                logger=self.logger
            )
            news_service = NewsService(logger=self.logger)
            
            # Initialize main posting service
            self.posting_service = PostingService(
                self.client,
                tweet_generator,
                news_service,
                meme_handler,
                self.logger
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}", exc_info=True)
            raise

    def run(self) -> None:
        """
        Main bot execution loop.
        
        Continuously posts tweets and monitors responses, handling any errors
        that occur during execution. The loop includes cooldown periods between
        posts and retry delays after errors.
        """
        posted_tweet_ids: List[str] = []
        
        while True:
            try:
                tweet_id = self.posting_service.post_tweet()
                if tweet_id:
                    posted_tweet_ids.append(tweet_id)
                    self.reply_handler.monitor_tweets(posted_tweet_ids)

                self.logger.info(f"Cooldown for {POST_COOLDOWN} seconds...")
                time.sleep(POST_COOLDOWN)
                
            except Exception as e:
                self.logger.error(f"Error in bot loop: {e}", exc_info=True)
                self.logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)


def main() -> None:
    """
    Application entry point.
    
    Sets up the environment, initializes the bot, and starts the main
    execution loop. Any fatal errors are logged before program termination.
    """
    try:
        warnings.filterwarnings("ignore")
        load_dotenv()
        bot = TwitterBot()
        bot.run()
    except Exception as e:
        logging.error("Fatal error in bot execution", exc_info=True)


if __name__ == "__main__":
    main()