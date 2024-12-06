"""
Main text processing class that handles tweet processing and styling.
"""

import random
import re
from typing import Optional
from collections import deque

from ..style_config import StyleConfig, Category  # Added Category import
from .text_cleaner import TextCleaner
from .content_analyzer import ContentAnalyzer

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
    
    def process_tweet(self, prompt: str, text: str) -> str:
        """
        Process and style tweet content
        
        Args:
            prompt (str): The input prompt
            text (str): Raw tweet text
            
        Returns:
            str: Processed and styled tweet
        """
        try:
            # Extract and clean tweet
            tweet = self._extract_tweet(text)
            tweet = self.cleaner.clean_text(tweet)
            
            if len(tweet) < 20:
                return self._get_fallback_response()
            
            # Handle length constraints
            if len(tweet) > 240:
                tweet = self._truncate_tweet(tweet)
            
            # Add styling
            category = self.analyzer.categorize_prompt(prompt)
            tweet = self._add_style(tweet, category.name.lower())
            
            return tweet
            
        except Exception as e:
            print(f"Error processing tweet: {str(e)}")
            return self._get_fallback_response()
    
    def _extract_tweet(self, text: str) -> str:
        """Extract tweet content from text"""
        return text.split("Tweet:")[-1].strip().split('\n')[0].strip()
    
    def _get_fallback_response(self) -> str:
        """Get random fallback response"""
        return random.choice(self.config.fallback_responses)
    
    def _truncate_tweet(self, tweet: str) -> str:
        """
        Smartly truncate tweet to fit length limit
        
        Args:
            tweet (str): Original tweet text
            
        Returns:
            str: Truncated tweet
        """
        sentences = re.split(r'(?<=[.!?])\s+', tweet)
        result = []
        current_length = 0
        
        for sentence in sentences:
            if current_length + len(sentence) <= 237:
                result.append(sentence)
                current_length += len(sentence) + 1
            else:
                break
        
        truncated_tweet = ' '.join(result).strip()
        if len(truncated_tweet) < len(tweet):
            truncated_tweet += '...'
        
        return truncated_tweet
    
    def _add_style(self, text: str, category: str) -> str:
        """
        Add styling elements to text
        
        Args:
            text (str): Original text
            category (str): Content category
            
        Returns:
            str: Styled text
        """
        if len(text) >= 220:
            return text
        
        # Clean redundant hashtags
        text = self._clean_hashtags(text)
        text = text.strip()
        
        # Add emoji if needed
        if self._needs_personality_marker(text):
            emoji = self._select_emoji(category)
            text = self._place_emoji(text, emoji)
        
        # Add hashtag if space allows
        if len(text) <= 200:
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
    
    def _select_emoji(self, category: str) -> str:
        """
        Select appropriate emoji based on category and history
        
        Args:
            category (str): Content category
            
        Returns:
            str: Selected emoji
        """
        available = [e for e in self.config.emojis[category] 
                    if e not in self.recent_emojis]
        if not available:
            available = self.config.emojis[category]
        
        emoji = random.choice(available)
        self.recent_emojis.append(emoji)
        return emoji
    
    def _select_hashtag(self, category: str) -> Optional[str]:
        """
        Select appropriate hashtag based on category and history
        
        Args:
            category (str): Content category
            
        Returns:
            Optional[str]: Selected hashtag or None
        """
        available = [t for t in self.config.hashtags[category] 
                    if t not in self.recent_hashtags]
        if not available:
            return None
        
        hashtag = random.choice(available)
        self.recent_hashtags.append(hashtag)
        return hashtag
    
    def _place_emoji(self, text: str, emoji: str) -> str:
        """
        Determine emoji placement in text
        
        Args:
            text (str): Original text
            emoji (str): Emoji to place
            
        Returns:
            str: Text with placed emoji
        """
        placement = random.random()
        if placement < 0.3:
            return f"{emoji} {text}"
        elif placement < 0.7:
            return f"{text} {emoji}"
        return text