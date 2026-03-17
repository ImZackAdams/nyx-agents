"""In-memory session state for a single Lilbot run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionStep:
    """A single controller step and its artifacts."""

    number: int
    prompt: str
    raw_model_output: str = ""
    thought: str | None = None
    action_name: str | None = None
    action_args: dict[str, Any] = field(default_factory=dict)
    observation: str | None = None
    error: str | None = None


@dataclass
class LilbotSession:
    """Current-run memory for the Lilbot controller."""

    user_query: str
    steps: list[SessionStep] = field(default_factory=list)
    final_answer: str | None = None

    @property
    def actions_taken(self) -> list[str]:
        return [step.action_name for step in self.steps if step.action_name]
