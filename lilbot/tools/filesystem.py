"""Deterministic workspace filesystem tools."""

from __future__ import annotations

from collections import deque
import os
from pathlib import Path
from typing import Iterator

from lilbot.utils.config import LilbotConfig


TEXT_FILE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cfg",
    ".conf",
    ".cpp",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".log",
    ".md",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


def _read_text_preview(path: Path, max_chars: int) -> str:
    with path.open("rb") as handle:
        data = handle.read(max_chars + 1)

    if not data:
        return "(empty file)"
    if b"\x00" in data:
        return "Binary file preview blocked."

    text = data.decode("utf-8", errors="replace")
    if len(data) > max_chars:
        return text[:max_chars] + "\n... (truncated)"
    return text


def iter_workspace_files(config: LilbotConfig, root: Path, *, limit: int | None = None) -> Iterator[Path]:
    visited = 0
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            [name for name in dirnames if name not in config.ignored_directories]
        )
        for filename in sorted(filenames):
            visited += 1
            if limit is not None and visited > limit:
                return
            yield Path(current_root) / filename


def tail_file(path: Path, *, max_lines: int) -> list[str]:
    lines: deque[str] = deque(maxlen=max_lines)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            lines.append(line.rstrip("\n"))
    return list(lines)


def read_file(config: LilbotConfig, path: str) -> str:
    """Read a text file under the configured workspace root."""

    try:
        target = config.resolve_workspace_path(path, must_exist=True)
    except ValueError as exc:
        return f"Path error: {exc}"

    if not target.is_file():
        return f"Not a file: {config.display_path(target)}"

    try:
        preview = _read_text_preview(target, config.file_max_chars)
    except OSError as exc:
        return f"Unable to read {config.display_path(target)}: {exc}"

    return f"File preview for {config.display_path(target)}:\n{preview}"


def list_directory(config: LilbotConfig, path: str = ".") -> str:
    """List directory contents inside the configured workspace root."""

    try:
        target = config.resolve_workspace_path(path, must_exist=True)
    except ValueError as exc:
        return f"Path error: {exc}"

    if not target.is_dir():
        return f"Not a directory: {config.display_path(target)}"

    try:
        entries = sorted(target.iterdir(), key=lambda item: item.name.lower())
    except OSError as exc:
        return f"Unable to list {config.display_path(target)}: {exc}"

    if not entries:
        return f"Directory listing for {config.display_path(target)}:\n(empty directory)"

    rendered = [
        f"{entry.name}/" if entry.is_dir() else entry.name
        for entry in entries[: config.directory_entry_limit]
    ]
    if len(entries) > config.directory_entry_limit:
        rendered.append(f"... ({len(entries) - config.directory_entry_limit} more entries)")

    return f"Directory listing for {config.display_path(target)}:\n" + "\n".join(rendered)


def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() in TEXT_FILE_EXTENSIONS:
        return True
    try:
        with path.open("rb") as handle:
            sample = handle.read(1024)
    except OSError:
        return False
    return b"\x00" not in sample


TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read a UTF-8 text file under the workspace root.",
        "parameters": {
            "path": "Workspace-relative file path.",
        },
        "function": read_file,
    },
    {
        "name": "list_directory",
        "description": "List files and folders under the workspace root.",
        "parameters": {
            "path": "Workspace-relative directory path. Defaults to '.'.",
        },
        "function": list_directory,
    },
]
