"""Parser for operational runbook markdown files."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re

from lilbot.ops.models import RunbookRecord


HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
STEP_PATTERN = re.compile(r"^\s*(?:\d+\.\s+|[-*]\s+)(.+)$")


def parse_runbook_file(path: str | Path) -> RunbookRecord:
    runbook_path = Path(path).expanduser().resolve()
    text = runbook_path.read_text(encoding="utf-8")
    return parse_runbook_text(text, source_path=runbook_path)


def parse_runbook_text(text: str, *, source_path: str | Path | None = None) -> RunbookRecord:
    source = str(source_path or "")
    title = ""
    current_section = "general"
    sections: dict[str, list[str]] = defaultdict(list)

    for line in text.splitlines():
        heading_match = HEADING_PATTERN.match(line)
        if heading_match is not None:
            heading = heading_match.group(1).strip()
            if not title:
                title = heading
            current_section = _normalize_section_name(heading)
            continue
        sections[current_section].append(line.rstrip())

    procedure_steps = _extract_steps(sections, ("procedure", "implementation", "steps", "actions"))
    prerequisites = _extract_steps(sections, ("prerequisite", "requirements", "pre-check", "precheck"))
    rollback_steps = _extract_steps(sections, ("rollback", "backout", "recovery"))
    scope = _extract_scope(sections)

    if not title:
        title = Path(source).stem.replace("_", " ").strip() if source else "Untitled Runbook"

    return RunbookRecord(
        title=title,
        scope=scope,
        prerequisites=tuple(prerequisites),
        procedure_steps=tuple(procedure_steps),
        rollback_steps=tuple(rollback_steps),
        source_path=source,
    )


def _normalize_section_name(name: str) -> str:
    lowered = name.lower()
    return "_".join(part for part in re.split(r"[^a-z0-9]+", lowered) if part)


def _extract_steps(sections: dict[str, list[str]], keywords: tuple[str, ...]) -> list[str]:
    steps: list[str] = []
    for section_name, lines in sections.items():
        if not any(keyword in section_name for keyword in keywords):
            continue
        for line in lines:
            match = STEP_PATTERN.match(line.strip())
            if match is not None:
                steps.append(match.group(1).strip())
    return _dedupe_preserving_order(steps)


def _extract_scope(sections: dict[str, list[str]]) -> str:
    for section_name, lines in sections.items():
        if "scope" not in section_name:
            continue
        for line in lines:
            text = line.strip()
            if text:
                return text

    for line in sections.get("general", []):
        text = line.strip()
        if text and not text.startswith(("#", "-", "*")):
            return text
    return ""


def _dedupe_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        clean_item = " ".join(item.split())
        if not clean_item:
            continue
        lowered = clean_item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(clean_item)
    return ordered
