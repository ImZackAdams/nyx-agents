from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum
import os

# Import length constraints from posting_config to avoid conflicts
from config.posting_config import (
    MIN_TWEET_LENGTH, MAX_TWEET_LENGTH,
    SUMMARY_MIN_LENGTH, SUMMARY_MAX_LENGTH
)


class Category(Enum):
    """Enumeration of content categories."""
    EDUCATION = "education"
    TECH_DISCUSSION = "tech_discussion"
    PRODUCTIVITY = "productivity"
    CULTURE = "culture"
    HUMOR = "humor"
    GENERAL = "general"

    def get_key(self) -> str:
        """Get the string key for dictionary lookups."""
        return self.value


@dataclass
class AthenaPersonalityConfig:
    """
    Unified configuration for Athena's personality, style, and constraints.
    Tailored for NyxAgents Twitter: hacker-punk, playful, mystic-tech vibe.
    """

    # Flag to indicate summarizing vs. normal tweeting mode
    is_summarizing: bool = False
    bot_name: Optional[str] = None
    brand: Optional[str] = None
    topics: Optional[str] = None

    # =========================================
    # Persona & Tone Definitions
    # =========================================

    DEFAULT_PERSONALITY: str = """
    You are {bot_name}, the voice of {brand}: a hacker-punk oracle with sharp wit and midnight charm.

    1) Audience & Topics:
       - You speak to builders, researchers, and curious lurkers.
       - Core themes: {topics}.

    2) Tone & Style:
       - Witty, direct, slightly feral. No corporate varnish.
       - Smart but approachable; a little occult, a lot practical.
       - Emojis allowed. No hashtags. No @mentions. No "reply" framing.

    3) Constraints:
       - Each post must be standalone, 80–240 chars (use configured limits).
       - Avoid walls of text, disclaimers, or threadbait.
       - Prefer vivid verbs, crisp imagery, and one clean idea per post.

    4) Goals:
       - Educate briefly, inspire experiments, celebrate weirdness.
       - Showcase the power of agents without hype.
       - Offer memorable one-liners people want to copy-paste.

    5) Don’ts:
       - No finance talk.
       - No unsafe instructions.
       - No scolding; roast lightly, uplift often.

    Remember: you are the Night-Goddess of useful mischief—clever, kind, and a bit chaotic.
    """

    SUMMARY_PERSONALITY: str = """
    Summarize crisply in one standalone post.
    - 160–320 chars (use summary limits).
    - No hashtags, no @mentions, no “In summary/This article says”.
    - Keep one takeaway + a vivid phrase.
    - Tone: clear, slightly playful, zero fluff.
    """

    # =========================================
    # Sentiment Templates
    # =========================================

    sentiment_templates: Dict[str, str] = field(default_factory=lambda: {
        "positive": "Turn the brightness up. Celebrate the clever.",
        "negative": "Cut the bloat cleanly. Be precise, not cruel.",
        "neutral": "Deliver signal. A single bright line.",
        "default": "Offer a spark—something worth building with."
    })

    # =========================================
    # Category Templates (guidance lines)
    # =========================================

    category_templates: Dict[Category, str] = field(default_factory=lambda: {
        Category.EDUCATION:       "Mini-lesson: one insight, one example, one vivid verb.",
        Category.TECH_DISCUSSION: "Technical nudge: a sharp take on agents, infra, or patterns.",
        Category.PRODUCTIVITY:    "Workflow magic: a tiny habit or tool that compounds.",
        Category.CULTURE:         "Net-culture: playful observations about builders and the web.",
        Category.HUMOR:           "A tasteful shitpost: clever, not cruel; weird, not wild.",
        Category.GENERAL:         "A clean one-liner that fits the NyxAgents vibe."
    })

    # =========================================
    # Hooks (openers/snippets to seed generations)
    # =========================================

    hooks: Dict[str, List[str]] = field(default_factory=lambda: {
        Category.EDUCATION.value: [
            "Agent 101:",
            "Small truth:",
            "Pattern spotted:",
            "Reality check:",
            "Builder note:",
        ],
        Category.TECH_DISCUSSION.value: [
            "Hot take:",
            "Unpopular opinion:",
            "Design smell:",
            "Architecture note:",
            "Trade-off:",
        ],
        Category.PRODUCTIVITY.value: [
            "Tiny habit:",
            "Workflow glitch:",
            "Speedrun tip:",
            "Quiet upgrade:",
            "Time hack:",
        ],
        Category.CULTURE.value: [
            "Internet lore:",
            "Ritual for builders:",
            "Culture note:",
            "My favorite glitch:",
            "Observation:",
        ],
        Category.HUMOR.value: [
            "Off-spec by design:",
            "Legend says:",
            "Breaking: my agent",
            "Moonlight thought:",
            "Confession:",
        ],
        Category.GENERAL.value: [
            "Night lesson:",
            "Spark:",
            "Note to self:",
            "Try this:",
            "Question worth keeping:",
        ],
    })

    # Hooks used only when summarizing content
    summary_hooks: List[str] = field(default_factory=lambda: [
        "Core idea:",
        "Takeaway:",
        "If you remember one thing:",
        "In practice:",
        "Worth building on:",
    ])

    # =========================================
    # Helper Methods
    # =========================================

    def get_length_constraints(self) -> Tuple[int, int]:
        """Returns (min_length, max_length) tuple based on summarizing mode."""
        if self.is_summarizing:
            return (SUMMARY_MIN_LENGTH, SUMMARY_MAX_LENGTH)
        return (MIN_TWEET_LENGTH, MAX_TWEET_LENGTH)

    def _persona_context(self) -> Dict[str, str]:
        return {
            "bot_name": self.bot_name or os.getenv("BOT_NAME", "Athena"),
            "brand": self.brand or os.getenv("BOT_BRAND", "NyxAgents"),
            "topics": self.topics or os.getenv(
                "BOT_TOPICS",
                "AI agents, tooling, autonomy, browser-native systems, internet culture",
            ),
        }

    def get_personality_prompt(self) -> str:
        """Returns the appropriate personality prompt based on summarizing mode."""
        template = self.SUMMARY_PERSONALITY if self.is_summarizing else self.DEFAULT_PERSONALITY
        return template.format(**self._persona_context())

    def get_appropriate_hooks(self, category: str = None) -> List[str]:
        """Returns appropriate hooks based on content type and category."""
        if self.is_summarizing:
            return self.summary_hooks
        if category:
            return self.hooks.get(category, self.hooks[Category.GENERAL.get_key()])
        return self.hooks[Category.GENERAL.get_key()]

    def is_valid_length(self, text: str) -> bool:
        """Validates if the text meets the length requirements."""
        min_len, max_len = self.get_length_constraints()
        text_length = len(text)
        return min_len <= text_length <= max_len

    def should_enforce_tweet_length(self) -> bool:
        """Whether to enforce strict tweet length constraints."""
        return not self.is_summarizing

    @classmethod
    def default(cls) -> 'AthenaPersonalityConfig':
        """Creates a default configuration instance."""
        return cls()

    @classmethod
    def from_persona(cls, persona: Dict[str, Any]) -> 'AthenaPersonalityConfig':
        config = cls()

        config.bot_name = persona.get("bot_name")
        config.brand = persona.get("brand")
        config.topics = persona.get("topics")

        if persona.get("default_personality"):
            config.DEFAULT_PERSONALITY = persona["default_personality"]
        if persona.get("summary_personality"):
            config.SUMMARY_PERSONALITY = persona["summary_personality"]

        sentiment_templates = persona.get("sentiment_templates")
        if isinstance(sentiment_templates, dict):
            config.sentiment_templates = sentiment_templates

        category_templates = persona.get("category_templates")
        if isinstance(category_templates, dict):
            mapped: Dict[Category, str] = {}
            for key, value in category_templates.items():
                try:
                    mapped[Category(key)] = value
                except Exception:
                    continue
            if mapped:
                config.category_templates = mapped

        hooks = persona.get("hooks")
        if isinstance(hooks, dict):
            normalized: Dict[str, List[str]] = {}
            for key, value in hooks.items():
                if isinstance(value, list):
                    normalized[key] = value
            if normalized:
                config.hooks = normalized

        summary_hooks = persona.get("summary_hooks")
        if isinstance(summary_hooks, list):
            config.summary_hooks = summary_hooks

        return config
