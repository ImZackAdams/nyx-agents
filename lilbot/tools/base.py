"""Base abstractions for Lilbot tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from lilbot.config import LilbotConfig


class Tool(ABC):
    """Discrete deterministic tool used by Lilbot."""

    name: str = ""
    description: str = ""
    args_schema: Mapping[str, str] = {}

    def __init__(self, config: LilbotConfig) -> None:
        self.config = config

    def describe(self) -> str:
        if not self.args_schema:
            return f"- {self.name}: {self.description} Args: none"
        args = ", ".join(f"{name}: {desc}" for name, desc in self.args_schema.items())
        return f"- {self.name}: {self.description} Args: {args}"

    @abstractmethod
    def execute(self, **kwargs: object) -> str:
        """Execute the tool with keyword arguments."""
