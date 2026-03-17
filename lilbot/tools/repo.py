"""Repository inspection tools."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
import re

from lilbot.tools.base import Tool
from lilbot.tools.filesystem import (
    is_probably_text,
    iter_workspace_files,
    read_text_preview,
)
from lilbot.utils.formatting import first_nonempty_line, truncate_text


IMPORTANT_REPO_FILES = (
    "README",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "package.json",
)
LIKELY_ENTRYPOINTS = {
    "cli.py",
    "__main__.py",
    "main.py",
    "app.py",
    "manage.py",
    "server.py",
}
IGNORED_REPO_SUFFIXES = {".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".onnx"}


class SummarizeRepoTool(Tool):
    name = "summarize_repo"
    description = "Summarize the structure, file types, and likely entry points of a repository."
    args_schema = {"path": "Workspace-relative repository path. Defaults to '.'."}

    def execute(self, **kwargs: object) -> str:
        path = str(kwargs.get("path", ".")).strip() or "."
        try:
            root = self.config.resolve_workspace_path(path, must_exist=True)
        except ValueError as exc:
            return f"Path error: {exc}"

        if not root.is_dir():
            return f"Not a directory: {self.config.display_path(root)}"

        files = [
            file
            for file in iter_workspace_files(self.config, root, limit=self.config.repo_file_limit)
            if file.suffix.lower() not in IGNORED_REPO_SUFFIXES
        ]
        if not files:
            return f"Repository summary for {self.config.display_path(root)}:\n- no files found"

        extension_counter = Counter(file.suffix.lower() or "<no extension>" for file in files)
        directory_counter = Counter(
            str(file.parent.relative_to(root)) or "."
            for file in files
            if file.parent != root
        )

        key_files = [file for file in files if file.name in IMPORTANT_REPO_FILES]
        entrypoints = [file.relative_to(root).as_posix() for file in files if _is_likely_entrypoint(file)]

        summary_lines = [
            f"Repository summary for {self.config.display_path(root)}:",
            f"- scanned_files: {len(files)}",
            f"- top_extensions: {_format_counter(extension_counter, 6)}",
            f"- busiest_directories: {_format_counter(directory_counter, 5)}",
        ]

        if entrypoints:
            summary_lines.append("- likely_entrypoints:")
            for entrypoint in entrypoints[:5]:
                summary_lines.append(f"  {entrypoint}")

        if key_files:
            summary_lines.append("- key_file_previews:")
            for file in key_files[:4]:
                try:
                    preview = read_text_preview(file, 300)
                except OSError:
                    continue
                headline = first_nonempty_line(preview) or "(empty)"
                summary_lines.append(
                    f"  {file.relative_to(root).as_posix()}: {truncate_text(headline, 180)}"
                )

        return "\n".join(summary_lines)


class FindFunctionTool(Tool):
    name = "find_function"
    description = "Find likely function definitions and references in a source tree."
    args_schema = {
        "name": "Function name to search for.",
        "path": "Workspace-relative repository path. Defaults to '.'.",
    }

    def execute(self, **kwargs: object) -> str:
        name = str(kwargs.get("name", "")).strip()
        path = str(kwargs.get("path", ".")).strip() or "."
        if not name:
            return "Function name is required."

        try:
            root = self.config.resolve_workspace_path(path, must_exist=True)
        except ValueError as exc:
            return f"Path error: {exc}"

        if not root.is_dir():
            return f"Not a directory: {self.config.display_path(root)}"

        definitions: list[str] = []
        references: list[str] = []

        for file_path in iter_workspace_files(self.config, root, limit=self.config.repo_file_limit):
            if file_path.suffix.lower() in IGNORED_REPO_SUFFIXES:
                continue
            if not is_probably_text(file_path):
                continue

            relative = file_path.relative_to(root).as_posix()
            if file_path.suffix == ".py":
                definitions.extend(_find_python_definitions(file_path, relative, name))
            elif len(definitions) < self.config.repo_reference_limit:
                match = _find_heuristic_definition(file_path, relative, name)
                if match:
                    definitions.append(match)

            if len(references) < self.config.repo_reference_limit:
                references.extend(_find_text_references(file_path, relative, name))

        output = [f"Function trace for `{name}` under {self.config.display_path(root)}:"]
        if definitions:
            output.append("- definitions:")
            output.extend(f"  {item}" for item in definitions[: self.config.repo_reference_limit])
        else:
            output.append("- definitions: none found")

        if references:
            output.append("- references:")
            output.extend(f"  {item}" for item in references[: self.config.repo_reference_limit])
        else:
            output.append("- references: none found")

        return "\n".join(output)


def _is_likely_entrypoint(path: Path) -> bool:
    if path.name in LIKELY_ENTRYPOINTS:
        return True
    if path.suffix != ".py":
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(
        re.search(r"if\s+__name__\s*==\s*[\"']__main__[\"']\s*:", text)
    )


def _find_python_definitions(path: Path, relative: str, name: str) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
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
                matches.append(_format_definition_match(relative, node.lineno, lines, self.class_stack, node.name, async_def=False))
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            if node.name == name:
                matches.append(_format_definition_match(relative, node.lineno, lines, self.class_stack, node.name, async_def=True))
            self.generic_visit(node)

    Visitor().visit(tree)
    return matches


def _format_definition_match(
    relative: str,
    line_number: int,
    lines: list[str],
    class_stack: list[str],
    name: str,
    *,
    async_def: bool,
) -> str:
    prefix = ".".join(class_stack)
    label = f"{prefix}.{name}" if prefix else name
    kind = "async definition" if async_def else "definition"
    snippet = _snippet(lines, line_number)
    return f"{relative}:{line_number} {kind} {label}\n    {snippet}"


def _find_heuristic_definition(path: Path, relative: str, name: str) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    patterns = [
        re.compile(rf"^\s*function\s+{re.escape(name)}\s*\("),
        re.compile(rf"^\s*(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:async\s*)?\("),
        re.compile(rf"^\s*func\s+{re.escape(name)}\s*\("),
        re.compile(rf"^\s*fn\s+{re.escape(name)}\b"),
    ]
    for index, line in enumerate(lines, start=1):
        if any(pattern.search(line) for pattern in patterns):
            return f"{relative}:{index} heuristic definition\n    {_snippet(lines, index)}"
    return None


def _find_text_references(path: Path, relative: str, name: str) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    pattern = re.compile(rf"\b{re.escape(name)}\b")
    matches: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        if not pattern.search(line):
            continue
        snippet = truncate_text(line.strip(), 220)
        matches.append(f"{relative}:{line_number} {snippet}")
        if len(matches) >= 5:
            break
    return matches


def _snippet(lines: list[str], line_number: int, *, window: int = 1) -> str:
    start = max(1, line_number - window)
    end = min(len(lines), line_number + window)
    selected = [lines[index - 1].rstrip() for index in range(start, end + 1)]
    return " | ".join(truncate_text(line.strip(), 100) for line in selected if line.strip())


def _format_counter(counter: Counter[str], limit: int) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{name} ({count})" for name, count in counter.most_common(limit))
