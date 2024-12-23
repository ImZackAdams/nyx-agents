"""
Prompt templates for the Athena bot.

This file no longer defines persona or style data. Instead, it imports
all configuration from `personality_config.py`. It focuses solely on
building prompts using the configuration provided.
"""

from typing import Optional

# UPDATED import:
# Was: from ..configs.personality_config import AthenaPersonalityConfig, Category
from config.personality_config import AthenaPersonalityConfig, Category


class PromptManager:
    """Handles prompt generation and management."""
    
    def __init__(self, config: Optional[AthenaPersonalityConfig] = None):
        # Use a default configuration if none is provided
        self.config = config or AthenaPersonalityConfig.default()

    def get_sentiment_guidance(self, sentiment: str) -> str:
        """Get appropriate guidance based on sentiment."""
        return self.config.sentiment_templates.get(
            sentiment,
            self.config.sentiment_templates["default"]
        )

    def get_category_guidance(self, category: Category) -> str:
        """Get appropriate guidance based on category."""
        return self.config.category_templates.get(
            category,
            self.config.category_templates[Category.GENERAL]
        )

    def build_prompt(self,
                     user_prompt: str,
                     opener: str,
                     sentiment: str,
                     category: Category) -> str:
        """Build the complete prompt with all components."""
        # Using the unified BASE_PERSONA from the config
        return (
            f"{opener} {user_prompt}\n\n"
            f"{self.config.BASE_PERSONA}\n"
            f"{self.get_category_guidance(category)}\n"
            f"{self.get_sentiment_guidance(sentiment)}\n"
            "Tweet:"
        )
