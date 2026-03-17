"""Model backend selection for Lilbot."""

from __future__ import annotations

from lilbot.config import LilbotConfig
from lilbot.model.base import BaseModel
from lilbot.model.hf_model import HuggingFaceLocalModel


def build_model(config: LilbotConfig) -> BaseModel:
    """Build the configured local model backend."""

    if config.backend == "hf":
        return HuggingFaceLocalModel(
            config.model,
            device=config.device,
            max_new_tokens=config.max_new_tokens,
            temperature=config.temperature,
        )
    raise RuntimeError(f"Unsupported backend: {config.backend}")


__all__ = ["BaseModel", "HuggingFaceLocalModel", "build_model"]
