"""
Main text processing class that handles tweet processing and styling.
"""

import random
import re
from typing import Optional, Tuple
from collections import deque

from ..style_config import StyleConfig, Category
from ..config import MAX_TWEET_LENGTH, MIN_TWEET_LENGTH
from .text_cleaner import TextCleaner
from .content_analyzer import ContentAnalyzer
from .validators import validate_tweet_length, clean_tweet_text

class TextProcessor:
    """Main text processing class for tweet content"""
    
    def __init__(self, style_config: StyleConfig = None, max_history: int = 10):
        """
        Initialize TextProcessor with config and history settings
        
        Args:
            style_config (StyleConfig, optional): Configuration for styling
            max_history (int): Maximum items to keep in history
        """
        self.config = style_config or StyleConfig.default()
        self.cleaner = TextCleaner()
        self.analyzer = ContentAnalyzer()
        
        # Initialize history tracking
        self.recent_emojis = deque(maxlen=max_history)
        self.recent_hashtags = deque(maxlen=max_history)
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
            
            # Add styling
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
        Add styling elements to text
        
        Args:
            text (str): Original text
            category (Category): Content category
            
        Returns:
            str: Styled text
        """
        # Leave room for styling elements
        style_limit = MAX_TWEET_LENGTH - 20
        if len(text) >= style_limit:
            return text
        
        # Clean redundant hashtags
        text = self._clean_hashtags(text)
        text = text.strip()
        
        # Add emoji if needed
        if self._needs_personality_marker(text):
            emoji = self._select_emoji(category)
            text = self._place_emoji(text, emoji)
        
        # Add hashtag if space allows
        if len(text) <= MAX_TWEET_LENGTH - 40:  # Leave room for hashtag
            hashtag = self._select_hashtag(category)
            if hashtag:
                text = f"{text} {hashtag}"
        
        # Final cleanup
        return self._cleanup_text(text)
    
    def _needs_personality_marker(self, text: str) -> bool:
        """Check if text needs a personality marker"""
        return not any(char in text for char in ''.join(self.config.personality_markers['sass']))
    
    def _clean_hashtags(self, text: str) -> str:
        """Clean redundant hashtags from text"""
        hashtags = re.findall(r'#\w+', text)
        if len(hashtags) > 1:
            text = re.sub(r'#\w+', '', text, count=len(hashtags) - 1)
        return text
    
    def _cleanup_text(self, text: str) -> str:
        """Final cleanup of text"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s+([.,!?])', r'\1', text)
        return text.strip()
    
    def _select_emoji(self, category: Category) -> str:
        """Select appropriate emoji based on category and history"""
        category_key = category.get_key()
        available = [e for e in self.config.emojis[category_key] 
                    if e not in self.recent_emojis]
        if not available:
            available = self.config.emojis[category_key]
        
        emoji = random.choice(available)
        self.recent_emojis.append(emoji)
        return emoji
    
    def _select_hashtag(self, category: Category) -> Optional[str]:
        """Select appropriate hashtag based on category and history"""
        category_key = category.get_key()
        available = [t for t in self.config.hashtags[category_key] 
                    if t not in self.recent_hashtags]
        if not available:
            return None
        
        hashtag = random.choice(available)
        self.recent_hashtags.append(hashtag)
        return hashtag
    
    def _place_emoji(self, text: str, emoji: str) -> str:
        """Determine emoji placement in text"""
        placement = random.random()
        if placement < 0.3:
            return f"{emoji} {text}"
        elif placement < 0.7:
            return f"{text} {emoji}"
        return text