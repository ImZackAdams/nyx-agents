"""Observability helpers for Lilbot controller runs."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import sys
from typing import Any, Mapping, TextIO

from lilbot.utils.formatting import summarize_observation, truncate_text


@dataclass
class StepLogger:
    """Emit readable step-by-step controller telemetry."""

    enabled: bool = False
    stream: TextIO = field(default_factory=lambda: sys.stderr)

    def step(self, number: int) -> None:
        self._emit(f"STEP {number}", "")

    def raw(self, message: str) -> None:
        self._emit("RAW", truncate_text(message, 2000))

    def thought(self, message: str) -> None:
        self._emit("THOUGHT", message)

    def action(self, message: str) -> None:
        self._emit("ACTION", message)

    def args(self, args: Mapping[str, Any]) -> None:
        self._emit("ARGS", json.dumps(dict(args), ensure_ascii=True, sort_keys=True))

    def observation(self, message: str) -> None:
        self._emit("OBSERVATION", summarize_observation(message))

    def error(self, message: str) -> None:
        self._emit("ERROR", message)

    def final(self, message: str) -> None:
        self._emit("FINAL", summarize_observation(message))

    def _emit(self, label: str, message: str) -> None:
        if not self.enabled:
            return

        if not message:
            print(f"[{label}]", file=self.stream, flush=True)
            return

        indent = " " * (len(label) + 3)
        for index, line in enumerate(str(message).splitlines()):
            prefix = f"[{label}] " if index == 0 else indent
            print(prefix + line, file=self.stream, flush=True)
