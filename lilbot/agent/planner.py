from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Planner:
    max_steps: int = 8
