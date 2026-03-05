from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class EchoProvider:
    """Placeholder provider for local testing."""

    def generate(self, prompt: str) -> str:
        return "FINAL: (echo provider) No model configured."
