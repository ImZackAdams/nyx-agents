"""Tool registry and execution helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from lilbot.tools.base import Tool


class ToolRegistry:
    """Register, describe, and execute Lilbot tools."""

    def __init__(self, tools: Iterable[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or ():
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError("Tool name is required.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._tools))
            raise KeyError(f"Unknown tool: {name}. Available tools: {available}") from exc

    def names(self) -> list[str]:
        return sorted(self._tools)

    def describe(self, allowed_tools: Sequence[str] | None = None) -> str:
        allowed = set(allowed_tools) if allowed_tools is not None else None
        lines = [
            tool.describe()
            for name, tool in sorted(self._tools.items())
            if allowed is None or name in allowed
        ]
        return "\n".join(lines) if lines else "No tools available."

    def execute(self, name: str, arguments: Mapping[str, object] | None = None) -> str:
        tool = self.get(name)
        return str(tool.execute(**dict(arguments or {})))
