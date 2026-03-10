"""Notes tools backed by persistent memory."""

from __future__ import annotations

from typing import Any, Dict

from lilbot.memory.memory import save_note as _save_note
from lilbot.memory.memory import search_notes as _search_notes


def save_note(params: Dict[str, Any]) -> str:
    text = params.get("text") or params.get("note")
    if not text:
        return "Missing required parameter: text"

    note = _save_note(str(text))
    return f"Saved note {note['id']}: {note['text']}"


def search_notes(params: Dict[str, Any]) -> str:
    query = params.get("query") or params.get("text")
    if not query:
        return "Missing required parameter: query"

    results = _search_notes(str(query))
    if not results:
        return "No matching notes."

    lines = [
        f"[{note['id']}] {note['text']} ({note['created_at']})"
        for note in results
    ]
    return "\n".join(lines)


TOOL_DEFS = [
    {
        "name": "save_note",
        "description": "Save a note to persistent memory.",
        "execute": save_note,
    },
    {
        "name": "search_notes",
        "description": "Search saved notes by text query.",
        "execute": search_notes,
    },
]
