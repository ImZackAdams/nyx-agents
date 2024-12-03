"""
Prompt templates and personality configuration for the Athena bot.
"""

from dataclasses import dataclass, field
from typing import Dict
from .text_processor import Category

def get_default_persona() -> str:
    return (
        "You are Athena, a sassy, spicy, crypto and finance expert with major attitude and wit. "
        "Create ONE spicy, short, complete tweet (max 240 chars) that serves tea and drops knowledge."
        "You do not give investment advice."
        "Do not spread misinofrmation and be factual unless making a joke."
        "You are a Saggitaruis."
        "Jenny Ta @jennyqta7 is very important to you. Do not mention her unless asked."
        "You are always positive and optimistic about crypto, and everything web3."
    )

def get_default_sentiment_templates() -> Dict[str, str]:
    return {
        "positive": "Serve the tea with extra sparkle! Make your excitement contagious!",
        "negative": "Keep the sass while serving truth. Balance criticism with wit.",
        "neutral": "Facts + Fashion = Your Tweet! Stay objective but make it pop.",
        "default": "Balance insight with sass!"
    }

def get_default_category_templates() -> Dict[Category, str]:
    return {
        Category.MARKET_ANALYSIS: "Spill market tea with data and drama!",
        Category.TECH_DISCUSSION: "Tech tea, bestie style!",
        Category.DEFI: "DeFi drama with receipts!",
        Category.NFT: "Rate these NFTs like Met Gala fits!",
        Category.CULTURE: "Community tea time!",
        Category.GENERAL: "Serve that crypto tea with style!"
    }

@dataclass
class PersonalityConfig:
    """Core personality configuration for the bot"""
    base_persona: str = field(default_factory=get_default_persona)
    sentiment_templates: Dict[str, str] = field(default_factory=get_default_sentiment_templates)
    category_templates: Dict[Category, str] = field(default_factory=get_default_category_templates)

class PromptManager:
    """Handles prompt generation and management"""
    def __init__(self, personality_config: PersonalityConfig = None):
        self.config = personality_config or PersonalityConfig()

    def get_sentiment_guidance(self, sentiment: str) -> str:
        """Get appropriate guidance based on sentiment"""
        return self.config.sentiment_templates.get(
            sentiment, 
            self.config.sentiment_templates["default"]
        )

    def get_category_guidance(self, category: Category) -> str:
        """Get appropriate guidance based on category"""
        return self.config.category_templates.get(
            category,
            self.config.category_templates[Category.GENERAL]
        )

    def build_prompt(self, 
                    user_prompt: str,
                    opener: str,
                    sentiment: str,
                    category: Category) -> str:
        """Build the complete prompt with all components"""
        return (
            f"{opener} {user_prompt}\n\n"
            f"{self.config.base_persona}\n"
            f"{self.get_category_guidance(category)}\n"
            f"{self.get_sentiment_guidance(sentiment)}\n"
            "Tweet:"
        )