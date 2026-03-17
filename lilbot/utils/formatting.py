"""Formatting helpers used across Lilbot."""

from __future__ import annotations


def truncate_text(text: str, limit: int) -> str:
    """Trim long strings while keeping output readable."""

    rendered = str(text)
    if len(rendered) <= limit:
        return rendered
    return rendered[:limit].rstrip() + "\n... (truncated)"


def first_nonempty_line(text: str) -> str:
    """Return the first non-empty line from a block of text."""

    for line in str(text).splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def summarize_observation(text: str, *, limit: int = 320) -> str:
    """Return a short one-line summary for logs and controller traces."""

    headline = first_nonempty_line(text)
    if not headline:
        return ""
    return truncate_text(headline, limit).replace("\n", " ")
