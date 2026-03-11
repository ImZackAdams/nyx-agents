from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any

from lilbot.paths import default_session_dir


DEFAULT_HISTORY_LIMIT = 12
SESSION_ID_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
VALID_ROLES = {"user", "assistant", "system", "tool"}


def session_file(session_id: str) -> Path:
    clean_id = SESSION_ID_PATTERN.sub("-", (session_id or "default").strip()) or "default"
    return default_session_dir() / f"{clean_id}.jsonl"


def load_session_history(session_id: str, limit: int = DEFAULT_HISTORY_LIMIT) -> list[dict[str, str]]:
    path = session_file(session_id)
    if not path.exists():
        return []

    messages: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            role = str(payload.get("role", "")).strip().lower()
            content = str(payload.get("content", ""))
            if role not in VALID_ROLES or not content:
                continue
            messages.append({"role": role, "content": content})

    max_items = _coerce_limit(limit)
    return messages[-max_items:]


def save_session_message(session_id: str, role: str, content: str) -> dict[str, str]:
    clean_role = str(role).strip().lower()
    clean_content = str(content)
    if clean_role not in VALID_ROLES:
        raise ValueError(f"Unsupported session role: {role}")
    if not clean_content:
        raise ValueError("Session content cannot be empty.")

    path = session_file(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": _utc_now(),
        "role": clean_role,
        "content": clean_content,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True))
        handle.write("\n")
    return {"role": clean_role, "content": clean_content}


def save_session_exchange(session_id: str, user_text: str, assistant_text: str) -> list[dict[str, str]]:
    return [
        save_session_message(session_id, "user", user_text),
        save_session_message(session_id, "assistant", assistant_text),
    ]


def _coerce_limit(limit: Any) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_HISTORY_LIMIT
    return value if value > 0 else DEFAULT_HISTORY_LIMIT


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
