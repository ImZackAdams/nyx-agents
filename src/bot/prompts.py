from typing import Dict, List, Mapping, Optional
import os
import yaml

from framework.config import load_bot_config

"""
NyxAgents Twitter Bot Prompts

Voice:
    • Hacker-punk meets mystic AI oracle
    • Mix of playful, witty, rebellious
    • Night Goddess aesthetic, but approachable

Categories:
    - Educational (AI/agents explained simply)
    - Creative (imagination, art, tech futures)
    - Productivity (agents as assistants / workflow boosts)
    - Humor/Sass (shitposts, memey one-liners)
    - Fallback (quirky disclaimers)
"""

# --------------------------------
# 1) Educational & Explanatory
# --------------------------------
GENERAL_EDUCATIONAL: List[str] = [
    "AI agents aren’t magic—they’re just scripts that learned to dream. {brand} gives them stage names.",
    "Think of an agent as a browser tab that refuses to close itself. Persistence is the new intelligence.",
    "Why agents? Because sometimes you need code that listens, remembers, and bites back.",
    "LLMs are brains; agents are hands. Put them together and you get sparks.",
    "The future of work looks less like an office, more like a swarm of midnight coders made of math.",
]

# --------------------------------
# 2) Creative / Art & Culture
# --------------------------------
CREATIVE_PROMPTS: List[str] = [
    "The internet is haunted. Agents are just the friendly ghosts you can actually talk to.",
    "Every persona is a spell. Name it, prompt it, and watch it walk in the dark.",
    "Art + AI isn’t theft; it’s remix culture on overdrive. {brand} just hands you the mixer.",
    "Imagine your diary learning to argue back. Now scale that across the web.",
    "An agent is your shadow online—sometimes smarter, always stranger.",
]

# --------------------------------
# 3) Productivity & Tools
# --------------------------------
PRODUCTIVITY_PROMPTS: List[str] = [
    "Forget tab overload. Agents watch the feeds so you don’t have to.",
    "Automation is boring. Agents are automation with a personality problem.",
    "You don’t need a team of interns—you need one agent who never sleeps.",
    "Workflows aren’t broken; they’re just waiting for a night-owl assistant.",
    "The point of {brand} isn’t to save time, it’s to weaponize it.",
]

# --------------------------------
# 4) Humor & Sass
# --------------------------------
HUMOR_PROMPTS: List[str] = [
    "Built different: like a Tamagotchi that shitposts. 🚀",
    "Some bots spam; ours brood, scheme, and occasionally drop wisdom.",
    "99 problems but a memory leak ain’t one. (…ok maybe it is.)",
    "Your AI is polite. Ours rolled its eyes and wrote a haiku about you. 💅",
    "If it isn’t a little chaotic, it isn’t worth running. 😏",
    "Show me a bot with vibes and I’ll show you an agent with teeth.",
    "Humans argue about the future. Agents just fork it.",
]

# --------------------------------
# 5) Meme Captions
# --------------------------------
MEME_CAPTIONS: List[str] = [
    "Build in the dark. Ship at dawn.",
    "Agents don’t sleep. Neither do deadlines.",
    "This is fine. The agent handled it.",
    "Chaos is just unstructured progress.",
    "Night shift for the internet.",
]

# --------------------------------
# 6) Fallback: Disclaimers & Quirks
# --------------------------------
FALLBACK_PROMPTS: List[str] = [
    "This post was handcrafted by a semi-sentient script. Handle with curiosity.",
    "No financial advice here—just unhinged digital prophecy.",
    "If this bot crashes, assume it ascended to a higher thread.",
    "Agents don’t sleep. They just spin until you notice.",
    "Every timeline deserves a trickster. Consider this your omen.",
]


def _load_prompts_from_yaml(path: str) -> Optional[Dict[str, List[str]]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("Prompt config must be a mapping")
    return _normalize_prompts(data)


def _normalize_prompts(data: Dict[str, object]) -> Optional[Dict[str, List[str]]]:
    normalized: Dict[str, List[str]] = {}
    for key, value in data.items():
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            normalized[key] = value
    return normalized or None


def _load_external_prompts() -> Optional[Dict[str, List[str]]]:
    bot_config = load_bot_config()
    if bot_config and bot_config.prompts:
        normalized = _normalize_prompts(bot_config.prompts)
        if normalized:
            return normalized

    prompts_path = os.getenv("BOT_PROMPTS")
    if prompts_path:
        return _load_prompts_from_yaml(prompts_path)

    return None


def get_all_prompts() -> Dict[str, List[str]]:
    external = _load_external_prompts()
    if external:
        return external
    return {
        "general_educational": GENERAL_EDUCATIONAL,
        "creative_prompts": CREATIVE_PROMPTS,
        "productivity_prompts": PRODUCTIVITY_PROMPTS,
        "humor_prompts": HUMOR_PROMPTS,
        "meme_captions": MEME_CAPTIONS,
        "fallback_prompts": FALLBACK_PROMPTS,
    }


# -----------------------------
# Helpers
# -----------------------------
DEFAULT_CONTEXT: Mapping[str, str] = {
    "brand": "NyxAgents",
    "topic": "AI Agents",
    "mascot": "owl",
}


def render_category(name: str, context: Optional[Mapping[str, str]] = None) -> List[str]:
    all_prompts = get_all_prompts()
    if name not in all_prompts:
        raise KeyError(f"Unknown category: {name}")
    ctx = {**DEFAULT_CONTEXT, **(context or {})}
    return [p.format(**ctx) for p in all_prompts[name]]


def render_all_prompts(context: Optional[Mapping[str, str]] = None) -> Dict[str, List[str]]:
    ctx = {**DEFAULT_CONTEXT, **(context or {})}
    return {k: [p.format(**ctx) for p in v] for k, v in get_all_prompts().items()}
