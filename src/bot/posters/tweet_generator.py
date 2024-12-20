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
    if MIN_TWEET_LENGTH <= len(tweet) <= MAX_TWEET_LENGTH:
        return True
    return False


class TweetGenerator:
    def __init__(self, personality_bot, cleaner=None, logger=None):
        self.bot = personality_bot
        self.cleaner = cleaner or TextCleaner()
        self.logger = logger or logging.getLogger(__name__)

    def generate_tweet(self, prompt: str) -> str:
        """Generate a tweet response with retry logic."""
        for attempt in range(MAX_GENERATION_ATTEMPTS):
            try:
                self.logger.info(f"Generating tweet, attempt {attempt + 1}...")
                response = self.bot.generate_response(prompt)
                cleaned_response = self.cleaner.clean_text(response)

                if len(cleaned_response) > MAX_TWEET_LENGTH:
                    self.logger.warning(
                        f"Generated tweet too long ({len(cleaned_response)} chars). Truncating..."
                    )
                    cleaned_response = cleaned_response[:MAX_TWEET_LENGTH].strip()

                if validate_tweet(cleaned_response):
                    self.logger.info(
                        f"Generated valid tweet: {cleaned_response} ({len(cleaned_response)} chars)"
                    )
                    return cleaned_response
                else:
                    self.logger.warning(
                        f"Generated tweet invalid: {cleaned_response} ({len(cleaned_response)} chars)"
                    )
            except Exception as e:
                self.logger.warning(f"Error generating tweet: {e}", exc_info=True)

        # If all attempts fail, use a fallback tweet
        fallback_tweet = random.choice(FALLBACK_TWEETS)
        self.logger.info(f"Using fallback tweet: {fallback_tweet}")
        return fallback_tweet
