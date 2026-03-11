"""Parser for environment standards and policy artifacts."""

from __future__ import annotations

from pathlib import Path
import re

from lilbot.ops.models import StandardsRecord


KEY_VALUE_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 _/-]*)\s*:\s*(.*?)\s*$")
RULE_PATTERN = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(.+)$")


def parse_standards_file(path: str | Path) -> StandardsRecord:
    standards_path = Path(path).expanduser().resolve()
    text = standards_path.read_text(encoding="utf-8")
    return parse_standards_text(text, source_path=standards_path)


def parse_standards_text(text: str, *, source_path: str | Path | None = None) -> StandardsRecord:
    source = str(source_path or "")
    attributes: dict[str, str] = {}
    rules: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        key_value_match = KEY_VALUE_PATTERN.match(line)
        if key_value_match is not None:
            key = _normalize_key(key_value_match.group(1))
            value = key_value_match.group(2).strip()
            if value:
                attributes[key] = value
            continue

        rule_match = RULE_PATTERN.match(line)
        if rule_match is not None:
            rules.append(rule_match.group(1).strip())

    if source:
        default_domain = Path(source).stem.replace("_", " ")
    else:
        default_domain = "standards"
    domain = attributes.get("domain") or attributes.get("environment") or default_domain

    return StandardsRecord(
        domain=domain,
        rules=tuple(_dedupe_preserving_order(rules)),
        attributes=attributes,
        source_path=source,
    )


def _normalize_key(key: str) -> str:
    return "_".join(part for part in re.split(r"[^A-Za-z0-9]+", key.lower()) if part)


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
