"""Log inspection tools."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from lilbot.tools.filesystem import tail_file
from lilbot.utils.config import LilbotConfig


TIMESTAMP_PREFIX_PATTERN = re.compile(
    r"^(?:[A-Z][a-z]{2}\s+\d+\s+\d\d:\d\d:\d\d|\d{4}-\d{2}-\d{2}[T\s]\d\d:\d\d:\d\d(?:\.\d+)?)\s+"
)


def summarize_log(config: LilbotConfig, path: str) -> str:
    """Summarize the tail of a log file from the workspace or a safe system log directory."""

    try:
        target = config.resolve_log_path(path)
    except ValueError as exc:
        return f"Path error: {exc}"

    if not target.is_file():
        return f"Not a file: {target}"

    try:
        lines = tail_file(target, max_lines=config.log_line_limit)
    except OSError as exc:
        return f"Unable to read {target}: {exc}"

    if not lines:
        return f"Log summary for {target}:\n(empty file)"

    lowered_lines = [line.lower() for line in lines]
    error_count = sum("error" in line or "failed" in line for line in lowered_lines)
    warning_count = sum("warn" in line for line in lowered_lines)
    critical_count = sum("critical" in line or "panic" in line for line in lowered_lines)

    normalized_messages = [_normalize_log_line(line) for line in lines if line.strip()]
    repeated_messages = Counter(normalized_messages).most_common(5)
    notable_lines = [
        line for line in lines if any(word in line.lower() for word in ("error", "warn", "fail", "critical"))
    ][-5:]

    summary_lines = [
        f"Log summary for {target}:",
        f"- sampled_lines: {len(lines)}",
        f"- errors: {error_count}",
        f"- warnings: {warning_count}",
        f"- critical_events: {critical_count}",
    ]

    if repeated_messages:
        summary_lines.append("- frequent_messages:")
        for message, count in repeated_messages:
            summary_lines.append(f"  {count}x {message[:160]}")

    if notable_lines:
        summary_lines.append("- recent_notable_lines:")
        for line in notable_lines:
            summary_lines.append(f"  {line[:220]}")

    return "\n".join(summary_lines)


def _normalize_log_line(line: str) -> str:
    stripped = TIMESTAMP_PREFIX_PATTERN.sub("", line.strip())
    stripped = re.sub(r"\[\d+\]", "[]", stripped)
    stripped = re.sub(r"\bpid=\d+\b", "pid=?", stripped)
    return stripped


TOOL_DEFINITIONS = [
    {
        "name": "summarize_log",
        "description": "Summarize a workspace or system log file.",
        "parameters": {
            "path": "Path to a log file under the workspace root or a safe log directory.",
        },
        "function": summarize_log,
    }
]
