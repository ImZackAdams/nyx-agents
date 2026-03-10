"""Persistent note storage for lilbot."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator


DEFAULT_NOTE_LIMIT = 10
DEFAULT_SESSION_LIMIT = 12
MEMORY_DB_ENV = "LILBOT_MEMORY_DB_PATH"
LEGACY_JSON_ENV = "LILBOT_MEMORY_JSON_PATH"
TOKEN_PATTERN = re.compile(r"[a-z0-9_]{2,}")


def get_store_path() -> Path:
    configured_path = os.getenv(MEMORY_DB_ENV)
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return Path(__file__).with_name("memory_store.db")


def get_legacy_store_path() -> Path:
    configured_path = os.getenv(LEGACY_JSON_ENV)
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return Path(__file__).with_name("memory_store.json")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    store_path = get_store_path()
    store_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(store_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    _initialize_schema(connection)
    try:
        yield connection
    finally:
        connection.close()


def _initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_notes_created_at
        ON notes (created_at DESC);

        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS session_messages (
            id INTEGER PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_session_messages_session_created
        ON session_messages (session_id, created_at DESC, id DESC);
        """
    )
    _migrate_legacy_store(connection)


def _metadata_value(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute(
        "SELECT value FROM metadata WHERE key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    return str(row["value"])


def _set_metadata(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO metadata (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def _migrate_legacy_store(connection: sqlite3.Connection) -> None:
    if _metadata_value(connection, "legacy_json_imported_at") is not None:
        return

    legacy_path = get_legacy_store_path()
    if not legacy_path.exists():
        _set_metadata(
            connection,
            "legacy_json_imported_at",
            datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        )
        connection.commit()
        return

    imported = 0
    try:
        with legacy_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        payload = {"notes": []}

    notes = payload.get("notes", []) if isinstance(payload, dict) else []
    for raw_note in notes:
        if not isinstance(raw_note, dict):
            continue
        text = str(raw_note.get("text", "")).strip()
        if not text:
            continue
        created_at = str(raw_note.get("created_at") or _utc_now())
        note_id = _coerce_note_id(raw_note.get("id"))

        if note_id is None:
            connection.execute(
                "INSERT INTO notes (text, created_at) VALUES (?, ?)",
                (text, created_at),
            )
        else:
            connection.execute(
                "INSERT OR IGNORE INTO notes (id, text, created_at) VALUES (?, ?, ?)",
                (note_id, text, created_at),
            )
        imported += 1

    _set_metadata(
        connection,
        "legacy_json_imported_at",
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
    _set_metadata(connection, "legacy_json_import_count", str(imported))
    connection.commit()


def _coerce_note_id(value: Any) -> int | None:
    try:
        note_id = int(value)
    except (TypeError, ValueError):
        return None
    return note_id if note_id > 0 else None


def _coerce_limit(limit: Any, default: int = DEFAULT_NOTE_LIMIT) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _rank_text_records(
    records: list[dict[str, Any]],
    *,
    query: str,
    limit: int,
    text_key: str = "text",
) -> list[dict[str, Any]]:
    clean_query = query.strip().lower()
    if not clean_query:
        return records[:limit]

    query_tokens = sorted(set(TOKEN_PATTERN.findall(clean_query)))
    scored_records: list[tuple[int, str, int, dict[str, Any]]] = []
    fallback_records: list[dict[str, Any]] = []

    for record in records:
        text_lower = str(record.get(text_key, "")).lower()
        if clean_query in text_lower:
            fallback_records.append(record)

        score = 0
        if clean_query in text_lower:
            score += max(3, len(query_tokens) + 1)
        score += sum(1 for token in query_tokens if token in text_lower)
        if score > 0:
            scored_records.append(
                (
                    score,
                    str(record.get("created_at", "")),
                    int(record.get("id", 0)),
                    record,
                )
            )

    if scored_records:
        scored_records.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return [record for _, _, _, record in scored_records[:limit]]

    return fallback_records[:limit]


def save_note(text: str) -> dict[str, Any]:
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Note text cannot be empty.")

    created_at = _utc_now()
    with _connect() as connection:
        cursor = connection.execute(
            "INSERT INTO notes (text, created_at) VALUES (?, ?)",
            (clean_text, created_at),
        )
        note_id = int(cursor.lastrowid)
        connection.commit()

    return {
        "id": note_id,
        "text": clean_text,
        "created_at": created_at,
    }


def search_notes(query: str | None = None, limit: int = DEFAULT_NOTE_LIMIT) -> list[dict[str, Any]]:
    max_results = _coerce_limit(limit)

    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, text, created_at
            FROM notes
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """
        ).fetchall()

    notes = [dict(row) for row in rows]
    return _rank_text_records(notes, query=query or "", limit=max_results)


def save_session_exchange(session_id: str, user_content: str, assistant_content: str) -> None:
    clean_session = session_id.strip()
    if not clean_session:
        raise ValueError("session_id cannot be empty.")

    records = (
        ("user", user_content.strip()),
        ("assistant", assistant_content.strip()),
    )
    created_at = _utc_now()
    with _connect() as connection:
        for role, content in records:
            if not content:
                continue
            connection.execute(
                """
                INSERT INTO session_messages (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (clean_session, role, content, created_at),
            )
        connection.commit()


def load_session_history(session_id: str, limit: int = DEFAULT_SESSION_LIMIT) -> list[dict[str, Any]]:
    clean_session = session_id.strip()
    if not clean_session:
        return []

    max_results = _coerce_limit(limit, default=DEFAULT_SESSION_LIMIT)
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM session_messages
            WHERE session_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (clean_session, max_results),
        ).fetchall()

    messages = [dict(row) for row in rows]
    messages.reverse()
    return messages


def search_session_history(
    session_id: str,
    query: str | None = None,
    limit: int = DEFAULT_SESSION_LIMIT,
) -> list[dict[str, Any]]:
    clean_session = session_id.strip()
    if not clean_session:
        return []

    max_results = _coerce_limit(limit, default=DEFAULT_SESSION_LIMIT)
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM session_messages
            WHERE session_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            (clean_session,),
        ).fetchall()

    messages = [dict(row) for row in rows]
    return _rank_text_records(messages, query=query or "", limit=max_results, text_key="content")
