import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import yaml


@dataclass
class BotConfig:
    persona: Dict[str, Any]
    behavior: Dict[str, Any]


def _read_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("Bot config must be a mapping")
    return data


def load_bot_config(path: Optional[str] = None) -> Optional[BotConfig]:
    config_path = path or os.getenv("BOT_CONFIG")
    if not config_path:
        return None
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"BOT_CONFIG not found: {config_path}")

    data = _read_yaml(config_path)
    persona = data.get("persona", {})
    behavior = data.get("behavior", {})
    if not isinstance(persona, dict) or not isinstance(behavior, dict):
        raise ValueError("'persona' and 'behavior' must be mappings")

    return BotConfig(persona=persona, behavior=behavior)


def apply_behavior_env(behavior: Dict[str, Any]) -> None:
    mapping = {
        "enable_news": "ENABLE_NEWS",
        "enable_memes": "ENABLE_MEMES",
    }
    for key, env_name in mapping.items():
        if key in behavior and env_name not in os.environ:
            os.environ[env_name] = "1" if bool(behavior[key]) else "0"
