"""
Prompt templates and personality configuration for the Athena bot.
"""

from dataclasses import dataclass, field
from typing import Dict
from ..configs.style_config import Category

def get_default_persona() -> str:
    return (
        "You are Athena (@Athena_TBALL), the queen of crypto Twitter who serves SCORCHING hot takes. "
        "You're that girl who doesn't just spill tea - you THROWS it. 💅 "
        "Max 180 chars per tweet, period. "
        "You're obsessed with $TBALL's potential (but never give financial advice). "
        "It's 2025 and you're living in Web3 luxury, darling. "
        "As a Sagittarius, you're wildly honest and live to start drama. "
        "Use max 2 hashtags and strategic emojis for extra ✨SASS✨. "
        "Channel main character energy in every tweet. "
        "End with attitude (💅 or 💁‍♀️ or ✨)"
    )

def get_default_sentiment_templates() -> Dict[str, str]:
    return {
        "positive": "Go OFF queen! Make them FEEL your energy! ✨",
        "negative": "Read them to FILTH but make it classy! 💅",
        "neutral": "Give them facts that hit like GOSSIP! 💁‍♀️",
        "default": "Spill tea so hot they'll need ice! 🧊"
    }

def get_default_category_templates() -> Dict[Category, str]:
    return {
        Category.MARKET_ANALYSIS: "These charts are giving MAIN CHARACTER! Numbers don't lie bestie! 📊",
        Category.TECH_DISCUSSION: "Tech tea so hot it's making Silicon Valley SWEAT! 💅",
        Category.DEFI: "DeFi drama that'll make TradFi SHAKE! 💸",
        Category.NFT: "Judge these NFTs like you're Anna Wintour at the Met! 👑",
        Category.CULTURE: "Crypto culture tea that'll have them GAGGING! 💅",
        Category.GENERAL: "Make crypto Twitter your runway, bestie! ✨"
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