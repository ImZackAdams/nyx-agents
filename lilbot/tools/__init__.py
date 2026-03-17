"""Lilbot tool exports and default registry construction."""

from __future__ import annotations

from lilbot.config import LilbotConfig
from lilbot.tools.filesystem import ListDirectoryTool, ReadFileTool
from lilbot.tools.logs import SummarizeLogTool
from lilbot.tools.registry import ToolRegistry
from lilbot.tools.repo import FindFunctionTool, SummarizeRepoTool
from lilbot.tools.shell import RunShellTool
from lilbot.tools.system import CpuSnapshotTool, DiskUsageTool, MemoryUsageTool


def build_default_tool_registry(config: LilbotConfig) -> ToolRegistry:
    return ToolRegistry(
        [
            ReadFileTool(config),
            ListDirectoryTool(config),
            RunShellTool(config),
            SummarizeRepoTool(config),
            FindFunctionTool(config),
            SummarizeLogTool(config),
            DiskUsageTool(config),
            MemoryUsageTool(config),
            CpuSnapshotTool(config),
        ]
    )


__all__ = [
    "ToolRegistry",
    "build_default_tool_registry",
]
