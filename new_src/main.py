"""
Main entry point for the Twitter bot.
"""
import time
import warnings
import logging
from typing import List
from dotenv import load_dotenv

# Updated imports for the new structure
from utils.logger import setup_logger
from api.twitter.client import TwitterClient

# If you define a function named setup_twitter_api in bot/initializers, that's fine
from bot.initializers import (
    validate_env_variables,
    initialize_diffusion_pipeline,
    setup_twitter_api
)

from bot.posting.posting_service import PostingService
# Use the class from bot/main_bot.py instead of bot/prompts:
from bot.main_bot import PersonalityBot
from bot.posting.tweet_generator import TweetGenerator
from bot.posting.meme_poster import MemePoster
from bot.posting.reply_poster import ReplyPoster
from bot.news.news_service import NewsService

# Config location changed
from config.posting_config import POST_COOLDOWN, RETRY_DELAY


class TwitterBot:
    """
    Main Twitter Bot orchestrator.
    """
    def __init__(self):
        self.logger = setup_logger("athena")
        self.logger.info("Initializing TwitterBot...")
        
        # Initialize the raw Twitter client here
        self.client = TwitterClient().client
        
        # Initialize other components (API, pipeline, services, etc.)
        self._initialize_components()

    def _initialize_components(self) -> None:
        """
        Sets up environment, Twitter API, model-based services, and specialized handlers.
        """
        try:
            # Validate environment
            validate_env_variables(self.logger)

            # Initialize the older Twitter API wrapper (if needed)
            self.api = setup_twitter_api()

            # Initialize core services
            personality_bot = PersonalityBot(
                model_path="./mistral_qlora_finetuned",
                logger=self.logger
            )
            tweet_generator = TweetGenerator(personality_bot, logger=self.logger)

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
        Main bot execution loop. Continuously posts tweets and monitors replies,
        sleeping in between or on error.
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
    Application entry point. Initializes the bot and starts the loop.
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
