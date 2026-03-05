from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ConversationMemory:
    max_items: int = 10
    items: List[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.items.append(message)
        if len(self.items) > self.max_items:
            self.items = self.items[-self.max_items:]

    def render(self) -> str:
        return "\n".join(self.items)
