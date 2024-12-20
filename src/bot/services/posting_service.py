"""
Service module handling all tweet posting logic.
"""

import random
import logging
from typing import Optional, List

from bot.services.news.news_service import NewsService
from bot.posters.tweet_generator import TweetGenerator
from bot.posters.meme_poster import MemePoster
from bot.prompts import get_all_prompts, FALLBACK_TWEETS
from bot.utilities.tweet_utils import format_tweet, validate_tweet
from bot.configs.posting_config import (
    MAX_PROMPT_ATTEMPTS,
    NEWS_POSTING_CHANCE,
    MEME_POSTING_CHANCE,
)


class PostingService:
    """Handles all tweet posting logic."""

    def __init__(
        self,
        client,
        tweet_generator: TweetGenerator,
        news_service: NewsService,
        meme_handler: MemePoster,
        logger: Optional[logging.Logger] = None
    ):
        self.client = client
        self.tweet_generator = tweet_generator
        self.news_service = news_service
        self.meme_handler = meme_handler
        self.logger = logger or logging.getLogger(__name__)

    def _post_to_twitter(self, text: str) -> Optional[str]:
        """Posts a tweet to Twitter and returns the tweet ID."""
        try:
            response = self.client.create_tweet(text=text)
            return response.data.get('id')
        except Exception as e:
            self.logger.error(f"Failed to post tweet: {e}")
            return None

    def _generate_news_prompt(self, article) -> str:
        """Generates a prompt for news tweets."""
        return (
            f"You are Athena (@Athena_TBALL), queen of crypto Twitter.\n"
            f"Title: {article.title}\nContent: {article.content[:200]}\n\n"
            "Write a sassy tweet summarizing this news. Include #CryptoNewsQueen and end with 💅 or ✨."
        )

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
                        self.news_service.mark_article_as_posted(article)
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