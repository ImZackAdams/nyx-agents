# validators.py
"""
Validation utilities for tweet processing.
"""
from dataclasses import dataclass
from typing import Optional, Tuple
import os

# UPDATED IMPORT: now referencing the top-level config/posting_config.py
from config.posting_config import MIN_TWEET_LENGTH, MAX_TWEET_LENGTH


@dataclass
class TweetValidation:
    """Result of tweet validation"""
    is_valid: bool
    message: Optional[str] = None
    cleaned_tweet: Optional[str] = None


def _env_bool(name: str, default: str = "0") -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in ("1", "true", "yes", "on")


def _min_tweet_length() -> int:
    if _env_bool("SIM_MODE", "0"):
        try:
            return int(os.getenv("SIM_MIN_TWEET_LENGTH", "40"))
        except ValueError:
            return 40
    return MIN_TWEET_LENGTH


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

    min_len = _min_tweet_length()
    if length < min_len:
        return False, f"Tweet too short ({length} chars, minimum {min_len})"

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

    # Clean up formatting and special tokens
    text = text.replace("<|assistant|>", "").replace("<|user|>", "").replace("<|system|>", "")
    text = text.strip(' \'"')  # Remove quotes and extra spaces
    text = text.split('\n')[0]  # Take only the first line

    return text.strip()
