# bot/processors/validators.py
"""
Validation utilities for tweet processing.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

from ..configs.posting_config import MIN_TWEET_LENGTH, MAX_TWEET_LENGTH

@dataclass
class TweetValidation:
    """Result of tweet validation"""
    is_valid: bool
    message: Optional[str] = None
    cleaned_tweet: Optional[str] = None

def validate_tweet_length(tweet: str) -> Tuple[bool, Optional[str]]:
    """
    Validate tweet length according to config constraints
    
    Args:
        tweet: The tweet to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message if any)
    """
    if not tweet or not tweet.strip():
        return False, "Empty tweet content"
        
    length = len(tweet.strip())
    
    if length < MIN_TWEET_LENGTH:
        return False, f"Tweet too short ({length} chars, minimum {MIN_TWEET_LENGTH})"
        
    if length > MAX_TWEET_LENGTH:
        return False, f"Tweet too long ({length} chars, maximum {MAX_TWEET_LENGTH})"
        
    return True, None

def clean_tweet_text(text: str) -> str:
    """
    Clean tweet text by removing common artifacts
    
    Args:
        text: Raw tweet text
        
    Returns:
        str: Cleaned tweet text
    """
    # Handle empty input
    if not text:
        return ""
        
    # Extract core content if "Tweet:" is present
    if "Tweet:" in text:
        text = text.split("Tweet:")[-1]
    
    # Remove common artifacts
    cleanup_markers = [
        "Note:", 
        "Your response:", 
        "(Feel free", 
        "**Note",
        "System:",
        "User:",
        "Assistant:"
    ]
    
    for marker in cleanup_markers:
        if marker in text:
            text = text.split(marker)[0]
    
    # Clean up formatting
    text = text.strip(' \'"')  # Remove quotes and extra spaces
    text = text.split('\n')[0]  # Take only first line
    
    return text.strip()