"""Conversation history tools backed by persistent memory."""

from __future__ import annotations

import os
from typing import Any, Dict

from lilbot.memory.memory import load_session_history as _load_session_history
from lilbot.memory.memory import search_session_history as _search_session_history


SESSION_ID_ENV = "LILBOT_SESSION_ID"
DEFAULT_SESSION_ID = "default"


def _session_id(params: Dict[str, Any]) -> str:
    raw_session_id = params.get("session_id") or os.getenv(SESSION_ID_ENV) or DEFAULT_SESSION_ID
    return str(raw_session_id).strip() or DEFAULT_SESSION_ID


def search_history(params: Dict[str, Any]) -> str:
    session_id = _session_id(params)
    query = params.get("query") or params.get("text")
    limit = params.get("limit", 8)

    try:
        if query:
            results = _search_session_history(session_id, str(query), limit=int(limit))
        else:
            results = _load_session_history(session_id, limit=int(limit))
    except Exception as exc:
        return f"Unable to load session history: {exc}"

    if not results:
        if query:
            return "No matching session history."
        return "No session history yet."

    lines = [
        f"[{message['role']}] {message['content']} ({message['created_at']})"
        for message in results
    ]
    return "\n".join(lines)


TOOL_DEFS = [
    {
        "name": "search_history",
        "description": "Search the current session's prior conversation or list recent session messages.",
        "parameters": {
            "query": "Optional text to search for in earlier conversation messages.",
            "limit": "Optional positive integer result limit.",
            "session_id": "Optional session identifier; defaults to the current CLI session.",
        },
        "example": {"query": "groceries", "limit": 6},
        "execute": search_history,
    }
]
