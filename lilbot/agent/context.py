from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from lilbot.memory.conversation_memory import ConversationMemory


@dataclass
class AgentContext:
    memory: ConversationMemory = field(default_factory=ConversationMemory)
    scratchpad: List[str] = field(default_factory=list)

    def add_observation(self, text: str) -> None:
        self.scratchpad.append(text)

    def render_scratchpad(self) -> str:
        return "\n".join(self.scratchpad)
