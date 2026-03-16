"""Repository analysis tools."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
import re

from lilbot.tools.filesystem import _read_text_preview, is_probably_text, iter_workspace_files
from lilbot.utils.config import LilbotConfig


IMPORTANT_REPO_FILES = (
    "README",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "package.json",
)


def summarize_repo(config: LilbotConfig, path: str = ".") -> str:
    """Produce a deterministic repository summary."""

    try:
        root = config.resolve_workspace_path(path, must_exist=True)
    except ValueError as exc:
        return f"Path error: {exc}"

    if not root.is_dir():
        return f"Not a directory: {config.display_path(root)}"

    files = list(iter_workspace_files(config, root, limit=config.repo_file_limit))
    if not files:
        return f"Repository summary for {config.display_path(root)}:\n- no files found"

    extension_counter = Counter(file.suffix.lower() or "<no extension>" for file in files)
    directory_counter = Counter(
        str(file.parent.relative_to(root)) or "."
        for file in files
        if file.parent != root
    )

    key_files = [file for file in files if file.name in IMPORTANT_REPO_FILES]
    preview_lines: list[str] = []
    for file in key_files[:3]:
        try:
            preview = _read_text_preview(file, 300)
        except OSError:
            continue
        first_line = next((line.strip() for line in preview.splitlines() if line.strip()), "(empty)")
        preview_lines.append(f"- {file.relative_to(root)}: {first_line[:180]}")

    summary_lines = [
        f"Repository summary for {config.display_path(root)}:",
        f"- scanned_files: {len(files)}",
        f"- top_extensions: {_format_counter(extension_counter, 5)}",
        f"- busiest_directories: {_format_counter(directory_counter, 5)}",
    ]

    if preview_lines:
        summary_lines.append("- key_file_previews:")
        summary_lines.extend(f"  {line}" for line in preview_lines)

    return "\n".join(summary_lines)


def find_function(config: LilbotConfig, name: str, path: str = ".") -> str:
    """Find likely function definitions and references in a repository."""

    try:
        root = config.resolve_workspace_path(path, must_exist=True)
    except ValueError as exc:
        return f"Path error: {exc}"

    if not root.is_dir():
        return f"Not a directory: {config.display_path(root)}"

    definitions: list[str] = []
    references: list[str] = []

    for file_path in iter_workspace_files(config, root, limit=config.repo_file_limit):
        if not is_probably_text(file_path):
            continue

        relative = file_path.relative_to(root).as_posix()
        if file_path.suffix == ".py":
            definitions.extend(_find_python_definitions(file_path, relative, name))

        if len(references) < config.repo_reference_limit:
            references.extend(_find_text_references(file_path, relative, name))

    output = [f"Function trace for `{name}` under {config.display_path(root)}:"]
    if definitions:
        output.append("- definitions:")
        output.extend(f"  {item}" for item in definitions[:10])
    else:
        output.append("- definitions: none found")

    if references:
        output.append("- references:")
        output.extend(f"  {item}" for item in references[: config.repo_reference_limit])
    else:
        output.append("- references: none found")

    return "\n".join(output)


def _find_python_definitions(path: Path, relative: str, name: str) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    matches: list[str] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if node.name == name:
                prefix = ".".join(self.class_stack)
                label = f"{prefix}.{node.name}" if prefix else node.name
                matches.append(f"{relative}:{node.lineno} definition {label}")
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            if node.name == name:
                prefix = ".".join(self.class_stack)
                label = f"{prefix}.{node.name}" if prefix else node.name
                matches.append(f"{relative}:{node.lineno} async definition {label}")
            self.generic_visit(node)

    Visitor().visit(tree)
    return matches


def _find_text_references(path: Path, relative: str, name: str) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    pattern = re.compile(rf"\b{name}\b")
    matches: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        if not pattern.search(line):
            continue
        snippet = line.strip()
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        matches.append(f"{relative}:{line_number} {snippet}")
        if len(matches) >= 5:
            break
    return matches


def _format_counter(counter: Counter[str], limit: int) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{name} ({count})" for name, count in counter.most_common(limit))


TOOL_DEFINITIONS = [
    {
        "name": "summarize_repo",
        "description": "Summarize the structure of a repository under the workspace root.",
        "parameters": {
            "path": "Workspace-relative repository path. Defaults to '.'.",
        },
        "function": summarize_repo,
    },
    {
        "name": "find_function",
        "description": "Find likely function definitions and references in a repository.",
        "parameters": {
            "name": "Function name to search for.",
            "path": "Workspace-relative repository path. Defaults to '.'.",
        },
        "function": find_function,
    },
]
