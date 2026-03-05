from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]
    risky: bool = False


class Tool:
    """
    Base class for tools.

    Subclasses must set: name, description, input_schema
    and implement run(input_data).
    """

    name: str = ""
    description: str = ""
    input_schema: Dict[str, Any] = {}
    risky: bool = False

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            risky=self.risky,
        )

    def run(self, input_data: Dict[str, Any]) -> Any:  # pragma: no cover - interface
        raise NotImplementedError
