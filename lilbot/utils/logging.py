"""Small observability helpers for Lilbot."""

from __future__ import annotations

from dataclasses import dataclass, field
import sys
from typing import TextIO


@dataclass
class AgentTraceLogger:
    """Emits user-visible agent telemetry."""

    enabled: bool = True
    stream: TextIO = field(default_factory=lambda: sys.stderr)

    def thought(self, message: str) -> None:
        self._emit("THOUGHT", message)

    def action(self, message: str) -> None:
        self._emit("ACTION", message)

    def observation(self, message: str) -> None:
        self._emit("OBSERVATION", message)

    def _emit(self, label: str, message: str) -> None:
        if not self.enabled:
            return
        text = str(message).strip()
        if not text:
            return

        indent = " " * (len(label) + 3)
        for index, line in enumerate(text.splitlines()):
            prefix = f"[{label}] " if index == 0 else indent
            print(prefix + line, file=self.stream, flush=True)
