from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Iterable, Optional

from .base_tool import Tool


class ToolRegistry:
    def __init__(self, allowlist: Optional[Iterable[str]] = None, logger: Optional[logging.Logger] = None):
        self._tools: Dict[str, Tool] = {}
        self._allowlist = set(allowlist or [])
        self._logger = logger or logging.getLogger(__name__)

    def register(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError("Tool must define a name")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def list_specs(self) -> Dict[str, dict]:
        return {name: tool.spec().__dict__ for name, tool in self._tools.items()}

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def is_allowed(self, name: str) -> bool:
        if not self._allowlist:
            return True
        return name in self._allowlist

    def execute(
        self,
        name: str,
        input_data: Dict[str, Any],
        confirm: Optional[Callable[[Tool], bool]] = None,
    ) -> Any:
        if not self.is_allowed(name):
            raise PermissionError(f"Tool not allowlisted: {name}")

        tool = self.get(name)
        if tool.risky and confirm:
            if not confirm(tool):
                return {"error": f"Tool execution cancelled: {name}"}

        self._logger.info("tool.execute", extra={"tool": name, "input": input_data})
        return tool.run(input_data)


_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(tool: Tool) -> Tool:
    get_registry().register(tool)
    return tool
