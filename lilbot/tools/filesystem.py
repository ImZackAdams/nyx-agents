"""Workspace filesystem tools."""

from __future__ import annotations

from collections import deque
import os
from pathlib import Path
from typing import Iterator

from lilbot.config import LilbotConfig
from lilbot.tools.base import Tool


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


def read_text_preview(path: Path, max_chars: int) -> str:
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


def iter_workspace_files(
    config: LilbotConfig,
    root: Path,
    *,
    limit: int | None = None,
) -> Iterator[Path]:
    visited = 0
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in config.ignored_directories and not name.endswith(".egg-info")
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


def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() in TEXT_FILE_EXTENSIONS:
        return True
    try:
        with path.open("rb") as handle:
            sample = handle.read(1024)
    except OSError:
        return False
    return b"\x00" not in sample


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read a UTF-8 text file under the workspace root."
    args_schema = {"path": "Workspace-relative file path."}

    def execute(self, **kwargs: object) -> str:
        path = str(kwargs.get("path", "")).strip()
        try:
            target = self.config.resolve_workspace_path(path, must_exist=True)
        except ValueError as exc:
            return f"Path error: {exc}"

        if not target.is_file():
            return f"Not a file: {self.config.display_path(target)}"

        try:
            preview = read_text_preview(target, self.config.file_preview_chars)
        except OSError as exc:
            return f"Unable to read {self.config.display_path(target)}: {exc}"

        return f"File preview for {self.config.display_path(target)}:\n{preview}"


class ListDirectoryTool(Tool):
    name = "list_directory"
    description = "List files and directories under the workspace root."
    args_schema = {"path": "Workspace-relative directory path. Defaults to '.'."}

    def execute(self, **kwargs: object) -> str:
        path = str(kwargs.get("path", ".")).strip() or "."
        try:
            target = self.config.resolve_workspace_path(path, must_exist=True)
        except ValueError as exc:
            return f"Path error: {exc}"

        if not target.is_dir():
            return f"Not a directory: {self.config.display_path(target)}"

        try:
            entries = sorted(target.iterdir(), key=lambda item: item.name.lower())
        except OSError as exc:
            return f"Unable to list {self.config.display_path(target)}: {exc}"

        if not entries:
            return f"Directory listing for {self.config.display_path(target)}:\n(empty directory)"

        rendered = [
            f"{entry.name}/" if entry.is_dir() else entry.name
            for entry in entries[: self.config.directory_entry_limit]
        ]
        if len(entries) > self.config.directory_entry_limit:
            rendered.append(
                f"... ({len(entries) - self.config.directory_entry_limit} more entries)"
            )

        return f"Directory listing for {self.config.display_path(target)}:\n" + "\n".join(rendered)
