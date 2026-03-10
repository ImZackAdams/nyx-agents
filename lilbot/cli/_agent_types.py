from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol


TokenCallback = Callable[[str], None]


class GeneratesText(Protocol):
    def generate(self, prompt: str, *, on_token: TokenCallback | None = None) -> str:
        ...


@dataclass(frozen=True)
class ConversationMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ParsedResponse:
    kind: str
    raw: str
    tool_name: str | None = None
    params: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class PrefetchState:
    working_messages: list[ConversationMessage]
    note_context: str
    history_context: str
    last_tool_name: str | None
    last_observation: str | None
    fallback_tool_name: str | None
    fallback_observation: str | None
    seen_tool_calls: set[tuple[str, str]]
