"""Tool registry for Lilbot."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from lilbot.tools.filesystem import TOOL_DEFINITIONS as FILESYSTEM_TOOL_DEFINITIONS
from lilbot.tools.logs import TOOL_DEFINITIONS as LOG_TOOL_DEFINITIONS
from lilbot.tools.repo import TOOL_DEFINITIONS as REPO_TOOL_DEFINITIONS
from lilbot.tools.shell import TOOL_DEFINITIONS as SHELL_TOOL_DEFINITIONS
from lilbot.utils.config import LilbotConfig


ALL_TOOL_DEFINITIONS = tuple(
    FILESYSTEM_TOOL_DEFINITIONS
    + SHELL_TOOL_DEFINITIONS
    + REPO_TOOL_DEFINITIONS
    + LOG_TOOL_DEFINITIONS
)


@dataclass
class ToolRegistry:
    """Binds tool metadata to a concrete runtime configuration."""

    config: LilbotConfig

    def __post_init__(self) -> None:
        self._tools = {tool["name"]: tool for tool in ALL_TOOL_DEFINITIONS}

    def definitions(self, allowed_tools: Sequence[str] | None = None) -> list[dict[str, Any]]:
        allowed = set(allowed_tools) if allowed_tools is not None else None
        definitions: list[dict[str, Any]] = []
        for tool in ALL_TOOL_DEFINITIONS:
            if allowed is not None and tool["name"] not in allowed:
                continue
            definitions.append(
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": dict(tool["parameters"]),
                }
            )
        return definitions

    def describe(self, allowed_tools: Sequence[str] | None = None) -> str:
        definitions = self.definitions(allowed_tools)
        if not definitions:
            return "No tools available."

        lines: list[str] = []
        for tool in definitions:
            parameters = tool["parameters"]
            parameter_text = ", ".join(f"{key}: {value}" for key, value in parameters.items())
            if not parameter_text:
                parameter_text = "no parameters"
            lines.append(
                f"- {tool['name']}: {tool['description']} Parameters: {parameter_text}"
            )
        return "\n".join(lines)

    def execute(self, name: str, arguments: Mapping[str, Any] | None = None) -> str:
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(sorted(self._tools))
            raise KeyError(f"Unknown tool: {name}. Available tools: {available}")
        return str(tool["function"](self.config, **dict(arguments or {})))


def build_tool_registry(config: LilbotConfig) -> ToolRegistry:
    return ToolRegistry(config)
