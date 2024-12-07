import random
import logging
from typing import Optional
from bot.processors.text_cleaner import TextCleaner
from bot.prompts import FALLBACK_TWEETS
from bot.configs.posting_config import (
    MAX_TWEET_LENGTH,
    MIN_TWEET_LENGTH,
    MAX_GENERATION_ATTEMPTS,
)


def validate_tweet(tweet: str) -> bool:
    """Validate the tweet's length and content."""
    return MIN_TWEET_LENGTH <= len(tweet) <= MAX_TWEET_LENGTH


class TweetGenerator:
    def __init__(self, personality_bot, cleaner=None, logger=None):
        self.bot = personality_bot
        self.cleaner = cleaner or TextCleaner()
        self.logger = logger or logging.getLogger(__name__)

    def generate_tweet(self, prompt: str) -> str:
        """Generate a tweet response with retry logic."""
        for _ in range(MAX_GENERATION_ATTEMPTS):
            try:
                response = self.bot.generate_response(prompt)
                cleaned_response = self.cleaner.clean_text(response)
                if len(cleaned_response) > MAX_TWEET_LENGTH:
                    cleaned_response = cleaned_response[:MAX_TWEET_LENGTH]  # Truncate long tweets
                if validate_tweet(cleaned_response):
                    return cleaned_response
            except Exception as e:
                self.logger.warning(f"Error generating tweet: {e}", exc_info=True)
        return random.choice(FALLBACK_TWEETS)
