"""Operational memory helpers backed by lilbot's SQLite store."""

from __future__ import annotations

from lilbot.memory.memory import save_note, save_profile_memory, search_notes, search_profile_memories


def save_environment_constraint(text: str) -> dict[str, object]:
    return save_profile_memory(f"environment_constraint: {text}", "environment constraint")


def save_maintenance_window(text: str) -> dict[str, object]:
    return save_profile_memory(f"maintenance_window: {text}", "maintenance window")


def save_reference_template(text: str) -> dict[str, object]:
    return save_note(f"reference_template: {text}")


def save_operational_note(text: str) -> dict[str, object]:
    return save_note(f"ops_note: {text}")


def search_operational_notes(query: str | None = None, *, limit: int = 8) -> list[dict[str, object]]:
    return search_notes(query, limit=limit)


def search_environment_constraints(query: str | None = None, *, limit: int = 8) -> list[dict[str, object]]:
    return search_profile_memories(query, limit=limit)
