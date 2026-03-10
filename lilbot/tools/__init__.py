"""Tool registry for lilbot."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from lilbot.tools.filesystem import TOOL_DEFS as FILESYSTEM_TOOL_DEFS
from lilbot.tools.history import TOOL_DEFS as HISTORY_TOOL_DEFS
from lilbot.tools.notes import TOOL_DEFS as NOTE_TOOL_DEFS
from lilbot.tools.profile import TOOL_DEFS as PROFILE_TOOL_DEFS
from lilbot.tools.system import TOOL_DEFS as SYSTEM_TOOL_DEFS


ALL_TOOL_DEFS = tuple(
    FILESYSTEM_TOOL_DEFS
    + HISTORY_TOOL_DEFS
    + NOTE_TOOL_DEFS
    + PROFILE_TOOL_DEFS
    + SYSTEM_TOOL_DEFS
)
TOOL_REGISTRY = {tool["name"]: tool["execute"] for tool in ALL_TOOL_DEFS}


def execute_tool(name: str, params: Mapping[str, Any] | None = None) -> str:
    """Execute a registered tool by name."""
    executor = TOOL_REGISTRY.get(name)
    if executor is None:
        available = ", ".join(sorted(TOOL_REGISTRY))
        raise KeyError(f"Unknown tool: {name}. Available tools: {available}")
    return str(executor(dict(params or {})))
