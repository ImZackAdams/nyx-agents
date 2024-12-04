from typing import Optional
import random
import logging
from bot.text_cleaner import TextCleaner
from bot.prompts import FALLBACK_TWEETS

class TweetGenerator:
    """Handles tweet generation and cleaning logic."""
    
    def __init__(self, personality_bot, logger: Optional[logging.Logger] = None):
        self.bot = personality_bot
        self.logger = logger or logging.getLogger(__name__)
        self.tweet_cleaner = TextCleaner()
        self.max_length = 220
        self.min_length = 100
        
    def _extract_tweet_content(self, text: str) -> str:
        """Extract the actual tweet content from the generated text."""
        # Split by "Tweet:" if present
        if "Tweet:" in text:
            text = text.split("Tweet:")[-1].strip()
            # Take only the first line
            text = text.split('\n')[0].strip()
        
        # Remove any generated usernames
        text = text.strip('"').strip()
        text = text.split("-Athena")[0].strip() if "-Athena" in text else text
        text = text.split("#CryptoTeaWithAthena")[0].strip()
        
        return text.strip()
        
    def generate_tweet(self, prompt: str, max_attempts: int = 3) -> str:
        """Generate a tweet response with retry logic."""
        for attempt in range(max_attempts):
            try:
                response = self.bot.generate_response(prompt)
                if not response:
                    continue
                    
                cleaned_response = self.tweet_cleaner.clean_text(response)
                extracted_tweet = self._extract_tweet_content(cleaned_response)
                
                if (self.min_length <= len(extracted_tweet) <= self.max_length and
                    any(char.isalpha() for char in extracted_tweet)):
                    self.logger.info(f"Successfully generated tweet: {extracted_tweet}")
                    return extracted_tweet
                    
                self.logger.warning(
                    f"Generated response failed validation - Length: {len(extracted_tweet)}"
                )
                
            except Exception as e:
                self.logger.warning(f"Generation attempt {attempt + 1} failed: {str(e)}")
        
        return self.get_fallback_tweet()
        
    def get_fallback_tweet(self) -> str:
        """Return a fallback tweet when generation fails."""
        tweet = random.choice(FALLBACK_TWEETS)
        self.logger.info(f"Using fallback tweet: {tweet}")
        return tweet