"""System tools for lilbot."""

from __future__ import annotations

import os
import platform
import sys
from typing import Any, Dict

try:
    import psutil
except Exception:  # pragma: no cover - optional dependency
    psutil = None


def system_info(_: Dict[str, Any]) -> str:
    lines = [
        f"OS: {platform.platform()}",
        f"Python: {sys.version.split()[0]}",
        f"Current directory: {os.getcwd()}",
    ]
    if psutil is not None:
        memory = psutil.virtual_memory()
        lines.append(f"CPU usage: {psutil.cpu_percent(interval=0.1):.1f}%")
        lines.append(f"RAM usage: {memory.percent:.1f}%")
    return "\n".join(lines)


TOOL_DEFS = [
    {
        "name": "system_info",
        "description": "Get basic system information.",
        "parameters": {},
        "example": {},
        "execute": system_info,
    }
]
