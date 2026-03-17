"""Base interface for Lilbot model backends."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseModel(ABC):
    """Small backend abstraction used by the controller."""

    runtime_summary: str = ""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a plain text response for the given prompt."""
