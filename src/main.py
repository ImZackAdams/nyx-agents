import os
import time
import random
import logging
import warnings
from typing import Optional
from dotenv import load_dotenv

import tweepy

from bot.bot import PersonalityBot
from bot.utilities.logger import setup_logger
from bot.services.utils import setup_twitter_client
from bot.services.rate_limiter import RateLimitTracker
from bot.prompts import get_all_prompts, FALLBACK_TWEETS
from bot.services.tweet_generator import TweetGenerator
from bot.services.reply_handler import ReplyHandler
from bot.services.meme_handler import MemeHandler
from bot.services.news.news_service import NewsService
from bot.configs.posting_config import (
    POST_COOLDOWN,
    RETRY_DELAY,
    MAX_PROMPT_ATTEMPTS,
    NEWS_POSTING_CHANCE,
    MEME_POSTING_CHANCE,
)
from bot.initializers import validate_env_variables, initialize_diffusion_pipeline
from bot.utilities.tweet_utils import format_tweet, validate_tweet


class TwitterBot:
    """Main Twitter Bot class responsible for posting tweets and interacting with the Twitter API."""

    def __init__(self):
        self.logger = setup_logger("athena")
        self.logger.info("Initializing TwitterBot...")
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize all components required by the bot."""
        validate_env_variables(self.logger)
        self.client = setup_twitter_client()
        self.api = tweepy.API(tweepy.OAuth1UserHandler(
            consumer_key=os.getenv('API_KEY'),
            consumer_secret=os.getenv('API_SECRET'),
            access_token=os.getenv('ACCESS_TOKEN'),
            access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
        ))
        self.rate_limit_tracker = RateLimitTracker()

        self.personality_bot = PersonalityBot(
            model_path="./mistral_qlora_finetuned",
            logger=self.logger
        )
        self.tweet_generator = TweetGenerator(self.personality_bot, logger=self.logger)
        self.pipe = initialize_diffusion_pipeline(self.logger)

        self.reply_handler = ReplyHandler(
            self.client, self.tweet_generator, logger=self.logger, pipe=self.pipe, api=self.api
        )
        self.meme_handler = MemeHandler(client=self.client, api=self.api, logger=self.logger)
        self.news_service = NewsService(logger=self.logger)

    def post_news(self) -> Optional[str]:
        """Posts a news-related tweet."""
        try:
            self.logger.info("Fetching the latest crypto news...")
            article = self.news_service.get_latest_article()

            if not article:
                self.logger.info("No new articles found.")
                return None

            self.logger.info(f"Processing article: {article.title}")
            article.content = self.news_service.get_article_content(article.url)

            if not article.content:
                self.logger.warning("Failed to extract article content.")
                return None

            for attempt in range(MAX_PROMPT_ATTEMPTS):
                self.logger.info(f"Generating news tweet, attempt {attempt + 1}/{MAX_PROMPT_ATTEMPTS}...")
                prompt = self._generate_news_prompt(article)
                raw_tweet = self.tweet_generator.generate_tweet(prompt)

                if not raw_tweet:
                    continue

                formatted_tweet = format_tweet(raw_tweet)
                if validate_tweet(formatted_tweet, article.title, article.content):
                    tweet_id = self._post_to_twitter(formatted_tweet)
                    if tweet_id:
                        self.news_service.mark_as_posted(article)
                        self.logger.info(f"Successfully posted news tweet: {formatted_tweet}")
                        return tweet_id

            self.logger.warning("Failed to generate a valid news tweet.")
            return None

        except Exception as e:
            self.logger.error(f"Error posting news tweet: {e}", exc_info=True)
            return None

    def post_tweet(self) -> Optional[str]:
        """Determines the type of tweet to post and posts it."""
        try:
            roll = random.random()
            if roll < NEWS_POSTING_CHANCE:
                return self.post_news()
            elif roll < NEWS_POSTING_CHANCE + MEME_POSTING_CHANCE:
                return self.meme_handler.post_meme()

            return self._post_text_tweet()

        except Exception as e:
            self.logger.error(f"Error during tweet posting: {e}", exc_info=True)
            return None

    def run(self):
        """Main loop for running the bot."""
        posted_tweet_ids = []
        while True:
            try:
                tweet_id = self.post_tweet()
                if tweet_id:
                    posted_tweet_ids.append(tweet_id)
                    self.reply_handler.monitor_tweets(posted_tweet_ids)

                self.logger.info(f"Cooldown for {POST_COOLDOWN} seconds...")
                time.sleep(POST_COOLDOWN)
            except Exception as e:
                self.logger.error(f"Error in bot loop: {e}", exc_info=True)
                self.logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)

    # Helper methods

    def _generate_news_prompt(self, article) -> str:
        """Generates a prompt for news tweets."""
        return (
            f"You are Athena (@Athena_TBALL), queen of crypto Twitter.\n"
            f"Title: {article.title}\nContent: {article.content[:200]}\n\n"
            "Write a sassy tweet summarizing this news. Include #CryptoNewsQueen and end with 💅 or ✨."
        )

    def _post_to_twitter(self, text: str) -> Optional[str]:
        """Posts a tweet to Twitter and returns the tweet ID."""
        try:
            response = self.client.create_tweet(text=text)
            return response.data.get('id')
        except Exception as e:
            self.logger.error(f"Failed to post tweet: {e}")
            return None

    def _post_text_tweet(self) -> Optional[str]:
        """Posts a text-based tweet."""
        prompts = get_all_prompts()
        all_prompts = [p for prompt_list in prompts.values() for p in prompt_list]
        for _ in range(MAX_PROMPT_ATTEMPTS):
            if not all_prompts:
                break
            prompt = random.choice(all_prompts)
            tweet = self.tweet_generator.generate_tweet(prompt)
            if tweet:
                return self._post_to_twitter(tweet)
        return self._post_to_twitter(random.choice(FALLBACK_TWEETS))


def main():
    """Main entry point for the bot."""
    try:
        warnings.filterwarnings("ignore")
        load_dotenv()
        bot = TwitterBot()
        bot.run()
    except Exception as e:
        logging.error("Fatal error in bot execution", exc_info=True)


if __name__ == "__main__":
    main()
