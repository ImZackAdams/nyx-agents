from typing import Optional, Tuple
import random
import logging
from bot.text_cleaner import TextCleaner
from bot.prompts import FALLBACK_TWEETS
from bot.config import (
    MAX_TWEET_LENGTH,
    MIN_TWEET_LENGTH,
    MAX_GENERATION_ATTEMPTS
)

class TweetGenerator:
    """Handles tweet generation and cleaning logic."""
    
    def __init__(self, personality_bot, logger: Optional[logging.Logger] = None):
        self.bot = personality_bot
        self.logger = logger or logging.getLogger(__name__)
        self.tweet_cleaner = TextCleaner()

    def _is_valid_tweet(self, tweet: str) -> Tuple[bool, str]:
        """
        Check if the tweet meets our criteria.
        Returns (is_valid, reason_if_invalid)
        """
        if len(tweet) < MIN_TWEET_LENGTH:
            return False, f"Tweet too short ({len(tweet)} chars)"
        if len(tweet) > MAX_TWEET_LENGTH:
            return False, f"Tweet too long ({len(tweet)} chars)"
        if not any(char.isalpha() for char in tweet):
            return False, "Tweet contains no letters"
            
        return True, ""
        
    def generate_tweet(self, prompt: str) -> str:
        """Generate a tweet response with retry logic."""
        for attempt in range(MAX_GENERATION_ATTEMPTS):
            try:
                response = self.bot.generate_response(prompt)
                if not response:
                    continue
                    
                cleaned_response = self.tweet_cleaner.clean_text(response)
                is_valid, reason = self._is_valid_tweet(cleaned_response)
                
                if is_valid:
                    self.logger.info(f"Successfully generated tweet: {cleaned_response}")
                    return cleaned_response
                    
                self.logger.warning(
                    f"Generated response failed validation - {reason}"
                )
                
            except Exception as e:
                self.logger.warning(f"Generation attempt {attempt + 1} failed: {str(e)}")
        
        return self.get_fallback_tweet()
        
    def get_fallback_tweet(self) -> str:
        """Return a fallback tweet when generation fails."""
        tweet = random.choice(FALLBACK_TWEETS)
        self.logger.info(f"Using fallback tweet: {tweet}")
        return tweet