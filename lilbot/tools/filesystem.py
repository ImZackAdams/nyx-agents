"""Filesystem tools for lilbot."""

from __future__ import annotations

import os
from typing import Any, Dict, List


def list_files(params: Dict[str, Any]) -> str:
    path = params.get("path", ".")
    if not os.path.exists(path):
        return f"Path not found: {path}"
    if not os.path.isdir(path):
        return f"Not a directory: {path}"

    entries: List[str] = sorted(os.listdir(path))
    if not entries:
        return "(empty directory)"
    return "\n".join(entries)


def read_file(params: Dict[str, Any]) -> str:
    path = params.get("path")
    if not path:
        return "Missing required parameter: path"
    if not os.path.exists(path):
        return f"Path not found: {path}"
    if not os.path.isfile(path):
        return f"Not a file: {path}"

    max_chars = params.get("max_chars", 4000)
    try:
        max_chars = int(max_chars)
    except (TypeError, ValueError):
        max_chars = 4000

    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        data = handle.read(max_chars + 1)

    if len(data) > max_chars:
        data = data[:max_chars] + "\n... (truncated)"
    return data


TOOL_DEFS = [
    {
        "name": "list_files",
        "description": "List files in a directory.",
        "execute": list_files,
    },
    {
        "name": "read_file",
        "description": "Read a file from disk.",
        "execute": read_file,
    },
]
