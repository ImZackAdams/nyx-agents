"""Persistent personal-profile tools for lilbot."""

from __future__ import annotations

from typing import Any, Dict

from lilbot.memory.memory import save_profile_memory as _save_profile_memory
from lilbot.memory.memory import search_profile_memories as _search_profile_memories


def save_profile_memory(params: Dict[str, Any]) -> str:
    text = params.get("text") or params.get("memory")
    category = params.get("category")
    if not text:
        return "Missing required parameter: text"

    try:
        memory = _save_profile_memory(str(text), str(category) if category else None)
    except Exception as exc:
        return f"Unable to save profile memory: {exc}"

    return f"Saved profile memory {memory['id']}: {memory['text']}"


def search_profile(params: Dict[str, Any]) -> str:
    query = params.get("query") or params.get("text")
    limit = params.get("limit", 8)

    try:
        results = _search_profile_memories(str(query) if query else None, limit=int(limit))
    except Exception as exc:
        return f"Unable to search profile memory: {exc}"

    if not results:
        if query:
            return "No matching profile memories."
        return "No saved profile memories."

    lines = [
        f"[{memory['id']}] {memory['text']} ({memory['created_at']})"
        for memory in results
    ]
    return "\n".join(lines)


TOOL_DEFS = [
    {
        "name": "save_profile_memory",
        "description": "Save a durable personal profile memory such as a preference, goal, or personal fact.",
        "parameters": {
            "text": "The profile memory to save.",
            "category": "Optional category such as name, preference, goal, or timezone.",
        },
        "example": {"text": "name: Zack", "category": "name"},
        "execute": save_profile_memory,
    },
    {
        "name": "search_profile",
        "description": "Search saved personal profile memories or list recent profile memories.",
        "parameters": {
            "query": "Optional text query for profile retrieval.",
            "limit": "Optional positive integer result limit.",
        },
        "example": {"query": "preferences", "limit": 6},
        "execute": search_profile,
    },
]
