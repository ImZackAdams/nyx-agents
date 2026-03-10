"""Persistent note storage for lilbot."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List


STORE_PATH = Path(__file__).with_name("memory_store.json")


def _load_store() -> Dict[str, Any]:
    if not STORE_PATH.exists():
        return {"notes": []}

    try:
        with STORE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("notes"), list):
            return data
    except json.JSONDecodeError:
        pass

    return {"notes": []}


def _save_store(data: Dict[str, Any]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STORE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def save_note(text: str) -> Dict[str, Any]:
    store = _load_store()
    notes = store.get("notes", [])
    next_id = max((note.get("id", 0) for note in notes), default=0) + 1 if notes else 1

    note = {
        "id": next_id,
        "text": text.strip(),
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    notes.append(note)
    store["notes"] = notes
    _save_store(store)
    return note


def search_notes(query: str) -> List[Dict[str, Any]]:
    store = _load_store()
    notes = store.get("notes", [])
    query_lower = query.strip().lower()
    if not query_lower:
        return []
    return [
        note
        for note in notes
        if query_lower in str(note.get("text", "")).lower()
    ]
