"""
Main text processing class that handles tweet processing and styling.
"""

import random
import re
from typing import Optional, Tuple
from collections import deque

# Replace the relative import (..configs.personality_config) 
# with an absolute import from config.personality_config
from config.personality_config import AthenaPersonalityConfig, Category
from config.posting_config import MAX_TWEET_LENGTH, MIN_TWEET_LENGTH

from .text_cleaner import TextCleaner
from .content_analyzer import ContentAnalyzer
from .validators import validate_tweet_length, clean_tweet_text


class TextProcessor:
    """Main text processing class for tweet content"""
    
    def __init__(self, config: AthenaPersonalityConfig = None, max_history: int = 10):
        """
        Initialize TextProcessor with config and history settings
        
        Args:
            config (AthenaPersonalityConfig, optional): Configuration for styling and personality
            max_history (int): Maximum items to keep in history
        """
        self.config = config or AthenaPersonalityConfig.default()
        self.cleaner = TextCleaner()
        self.analyzer = ContentAnalyzer()
        
        # REMOVED references to storing recent emojis/hashtags.
        # We no longer track them, since we’ve removed them entirely.
        self.recent_openers = deque(maxlen=max_history)
    
    def process_tweet(self, prompt: str, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Process and style tweet content
        
        Args:
            prompt (str): The input prompt
            text (str): Raw tweet text
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (processed_tweet, error_message)
        """
        try:
            # Clean and validate initial text
            tweet = clean_tweet_text(text)
            is_valid, error_msg = validate_tweet_length(tweet)
            
            if not is_valid:
                return None, error_msg
            
            # Clean text
            tweet = self.cleaner.clean_text(tweet)
            
            # Revalidate after cleaning
            is_valid, error_msg = validate_tweet_length(tweet)
            if not is_valid:
                return None, error_msg
            
            # Add minimal styling (no hashtags/emojis)
            category = self.analyzer.categorize_prompt(prompt)
            tweet = self._add_style(tweet, category)
            
            # Final length validation after styling
            is_valid, error_msg = validate_tweet_length(tweet)
            if not is_valid:
                return None, error_msg
            
            return tweet, None
            
        except Exception as e:
            return None, f"Error processing tweet: {str(e)}"
    
    def _add_style(self, text: str, category: Category) -> str:
        """
        Add minimal styling elements to text (no emojis or hashtags).
        
        Args:
            text (str): Original text
            category (Category): Content category
            
        Returns:
            str: Styled text
        """
        # We won't add any hashtags or emojis here.
        # Just ensure the tweet doesn't exceed the length limit after basic cleanup.
        style_limit = MAX_TWEET_LENGTH - 20
        if len(text) >= style_limit:
            return self._cleanup_text(text)
        
        # Final cleanup
        return self._cleanup_text(text)
    
    def _cleanup_text(self, text: str) -> str:
        """Final cleanup of text"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s+([.,!?])', r'\1', text)
        return text.strip()

    # REMOVED these methods:
    #
    #  - _select_emoji
    #  - _select_hashtag
    #  - _place_emoji
    #  - _clean_hashtags
    #
    # because we no longer insert or manage emojis/hashtags.
