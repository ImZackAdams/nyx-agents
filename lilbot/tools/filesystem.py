"""Workspace filesystem tools for lilbot."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict


DEFAULT_MAX_CHARS = 4000
DEFAULT_MAX_ENTRIES = 200
WORKSPACE_ROOT_ENV = "LILBOT_WORKSPACE_ROOT"


def get_workspace_root() -> Path:
    root = os.getenv(WORKSPACE_ROOT_ENV) or os.getcwd()
    return Path(root).expanduser().resolve()


def _coerce_positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _display_path(path: Path) -> str:
    root = get_workspace_root()
    try:
        relative = path.relative_to(root)
    except ValueError:
        return str(path)
    return "." if not relative.parts else f"./{relative.as_posix()}"


def _resolve_workspace_path(raw_path: Any, *, default: str | None = None) -> tuple[Path | None, str | None]:
    path_text = str(raw_path or default or "").strip()
    if not path_text:
        return None, "Missing required parameter: path"

    root = get_workspace_root()
    candidate = Path(path_text).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate

    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        return None, f"Invalid path: {path_text} ({exc})"

    if resolved != root and root not in resolved.parents:
        return None, f"Path is outside the workspace root ({root}): {path_text}"

    return resolved, None


def list_files(params: Dict[str, Any]) -> str:
    path, error = _resolve_workspace_path(params.get("path"), default=".")
    if error:
        return error
    assert path is not None

    if not path.exists():
        return f"Path not found: {_display_path(path)}"
    if not path.is_dir():
        return f"Not a directory: {_display_path(path)}"

    max_entries = _coerce_positive_int(params.get("max_entries"), DEFAULT_MAX_ENTRIES)
    try:
        entries = sorted(
            (
                f"{entry.name}/" if entry.is_dir() else entry.name
                for entry in path.iterdir()
            ),
            key=str.lower,
        )
    except OSError as exc:
        return f"Unable to list {_display_path(path)}: {exc}"

    if not entries:
        return "(empty directory)"

    if len(entries) > max_entries:
        shown = entries[:max_entries]
        shown.append(f"... ({len(entries) - max_entries} more entries)")
        return "\n".join(shown)

    return "\n".join(entries)


def read_file(params: Dict[str, Any]) -> str:
    path, error = _resolve_workspace_path(params.get("path"))
    if error:
        return error
    assert path is not None

    if not path.exists():
        return f"Path not found: {_display_path(path)}"
    if not path.is_file():
        return f"Not a file: {_display_path(path)}"

    max_chars = _coerce_positive_int(params.get("max_chars"), DEFAULT_MAX_CHARS)

    try:
        with path.open("rb") as handle:
            data = handle.read(max_chars + 1)
    except OSError as exc:
        return f"Unable to read {_display_path(path)}: {exc}"

    if not data:
        return "(empty file)"
    if b"\x00" in data:
        return f"Binary file not shown: {_display_path(path)}"

    text = data.decode("utf-8", errors="replace")
    if len(data) > max_chars:
        return text[:max_chars] + "\n... (truncated)"
    return text


def write_file(params: Dict[str, Any]) -> str:
    path, error = _resolve_workspace_path(params.get("path"))
    if error:
        return error
    assert path is not None

    if path.exists() and not path.is_file():
        return f"Not a file: {_display_path(path)}"

    content = str(params.get("content", ""))
    mode = str(params.get("mode", "overwrite")).strip().lower()
    if mode not in {"overwrite", "append"}:
        return "Invalid mode. Expected 'overwrite' or 'append'."

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a" if mode == "append" else "w", encoding="utf-8") as handle:
            handle.write(content)
    except OSError as exc:
        return f"Unable to write {_display_path(path)}: {exc}"

    action = "Appended" if mode == "append" else "Wrote"
    return f"{action} {len(content)} characters to {_display_path(path)}"


TOOL_DEFS = [
    {
        "name": "list_files",
        "description": "List files in a workspace-relative directory.",
        "parameters": {
            "path": "Workspace-relative directory path. Defaults to '.'.",
            "max_entries": "Optional positive integer entry limit.",
        },
        "example": {"path": ".", "max_entries": 50},
        "execute": list_files,
    },
    {
        "name": "read_file",
        "description": "Read a UTF-8 text file under the workspace root.",
        "parameters": {
            "path": "Workspace-relative file path.",
            "max_chars": "Optional positive integer character limit.",
        },
        "example": {"path": "README.md", "max_chars": 2000},
        "execute": read_file,
    },
    {
        "name": "write_file",
        "description": "Write a UTF-8 text file under the workspace root.",
        "parameters": {
            "path": "Workspace-relative file path.",
            "content": "Text content to write.",
            "mode": "Use 'overwrite' or 'append'.",
        },
        "example": {
            "path": "scratch/todo.txt",
            "content": "Ship the CLI skeleton.\n",
            "mode": "overwrite",
        },
        "execute": write_file,
    },
]
