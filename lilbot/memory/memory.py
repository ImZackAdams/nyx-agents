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

from lilbot.paths import default_legacy_memory_json_path, default_memory_db_path


DEFAULT_NOTE_LIMIT = 10
DEFAULT_SESSION_LIMIT = 12
DEFAULT_PROFILE_LIMIT = 8
MEMORY_DB_ENV = "LILBOT_MEMORY_DB_PATH"
LEGACY_JSON_ENV = "LILBOT_MEMORY_JSON_PATH"
FTS_SCHEMA_VERSION = "2"
TOKEN_PATTERN = re.compile(r"[a-z0-9_]{2,}")
SESSION_NOISE_PATTERN = re.compile(r"^\s*(?:\[\]|\{\}|null|\(empty response\))\s*$", re.IGNORECASE)
SESSION_PROTOCOL_PATTERN = re.compile(
    r"^\s*(?:<\|(?:assistant|user|system)\|>\s*)*(?:FINAL:|TOOL:)",
    re.IGNORECASE,
)
SESSION_SPECIAL_TOKEN_PATTERN = re.compile(r"<\|(?:assistant|user|system)\|>")
SESSION_NOISE_RESPONSES = {
    "(echo provider) No model configured.",
}
PROFILE_SINGLETON_CATEGORIES = frozenset(
    {
        "name",
        "email",
        "phone number",
        "address",
        "pronouns",
        "timezone",
    }
)
_FTS5_AVAILABLE: bool | None = None


def get_store_path() -> Path:
    configured_path = os.getenv(MEMORY_DB_ENV)
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return default_memory_db_path()


def get_legacy_store_path() -> Path:
    configured_path = os.getenv(LEGACY_JSON_ENV)
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return default_legacy_memory_json_path()


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

        CREATE TABLE IF NOT EXISTS profile_memories (
            id INTEGER PRIMARY KEY,
            category TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_profile_memories_created_at
        ON profile_memories (created_at DESC);

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
    _initialize_full_text_search(connection)


def _initialize_full_text_search(connection: sqlite3.Connection) -> None:
    global _FTS5_AVAILABLE

    if _FTS5_AVAILABLE is False:
        return

    try:
        connection.executescript(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
            USING fts5(text, content='notes', content_rowid='id');

            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                INSERT INTO notes_fts(rowid, text) VALUES (new.id, new.text);
            END;

            CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, text)
                VALUES ('delete', old.id, old.text);
            END;

            CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, text)
                VALUES ('delete', old.id, old.text);
                INSERT INTO notes_fts(rowid, text) VALUES (new.id, new.text);
            END;

            CREATE VIRTUAL TABLE IF NOT EXISTS profile_memories_fts
            USING fts5(text, content='profile_memories', content_rowid='id');

            CREATE TRIGGER IF NOT EXISTS profile_memories_ai AFTER INSERT ON profile_memories BEGIN
                INSERT INTO profile_memories_fts(rowid, text) VALUES (new.id, new.text);
            END;

            CREATE TRIGGER IF NOT EXISTS profile_memories_ad AFTER DELETE ON profile_memories BEGIN
                INSERT INTO profile_memories_fts(profile_memories_fts, rowid, text)
                VALUES ('delete', old.id, old.text);
            END;

            CREATE TRIGGER IF NOT EXISTS profile_memories_au AFTER UPDATE ON profile_memories BEGIN
                INSERT INTO profile_memories_fts(profile_memories_fts, rowid, text)
                VALUES ('delete', old.id, old.text);
                INSERT INTO profile_memories_fts(rowid, text) VALUES (new.id, new.text);
            END;

            CREATE VIRTUAL TABLE IF NOT EXISTS session_messages_fts
            USING fts5(
                session_id UNINDEXED,
                role UNINDEXED,
                content,
                content='session_messages',
                content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS session_messages_ai AFTER INSERT ON session_messages BEGIN
                INSERT INTO session_messages_fts(rowid, session_id, role, content)
                VALUES (new.id, new.session_id, new.role, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS session_messages_ad AFTER DELETE ON session_messages BEGIN
                INSERT INTO session_messages_fts(session_messages_fts, rowid, session_id, role, content)
                VALUES ('delete', old.id, old.session_id, old.role, old.content);
            END;

            CREATE TRIGGER IF NOT EXISTS session_messages_au AFTER UPDATE ON session_messages BEGIN
                INSERT INTO session_messages_fts(session_messages_fts, rowid, session_id, role, content)
                VALUES ('delete', old.id, old.session_id, old.role, old.content);
                INSERT INTO session_messages_fts(rowid, session_id, role, content)
                VALUES (new.id, new.session_id, new.role, new.content);
            END;
            """
        )
    except sqlite3.OperationalError as exc:
        if "fts5" not in str(exc).lower():
            raise
        _FTS5_AVAILABLE = False
        return

    _FTS5_AVAILABLE = True
    if _metadata_value(connection, "fts_schema_version") == FTS_SCHEMA_VERSION:
        return

    connection.execute("INSERT INTO notes_fts(notes_fts) VALUES ('rebuild')")
    connection.execute("INSERT INTO profile_memories_fts(profile_memories_fts) VALUES ('rebuild')")
    connection.execute("INSERT INTO session_messages_fts(session_messages_fts) VALUES ('rebuild')")
    _set_metadata(connection, "fts_schema_version", FTS_SCHEMA_VERSION)
    connection.commit()


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


def _normalize_profile_category(category: Any) -> str:
    normalized = " ".join(str(category or "profile").strip().lower().split())
    return normalized or "profile"


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


def _fts_match_expression(query: str) -> str | None:
    tokens = list(dict.fromkeys(TOKEN_PATTERN.findall(query.strip().lower())))
    if not tokens:
        return None
    return " OR ".join(f"{token}*" for token in tokens[:8])


def _search_notes_fts(
    connection: sqlite3.Connection,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    match_expression = _fts_match_expression(query)
    if not match_expression:
        return []

    rows = connection.execute(
        """
        SELECT notes.id, notes.text, notes.created_at
        FROM notes_fts
        JOIN notes ON notes.id = notes_fts.rowid
        WHERE notes_fts MATCH ?
        ORDER BY bm25(notes_fts), notes.created_at DESC, notes.id DESC
        LIMIT ?
        """,
        (match_expression, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def _search_profile_memories_fts(
    connection: sqlite3.Connection,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    match_expression = _fts_match_expression(query)
    if not match_expression:
        return []

    rows = connection.execute(
        """
        SELECT profile_memories.id,
               profile_memories.category,
               profile_memories.text,
               profile_memories.created_at
        FROM profile_memories_fts
        JOIN profile_memories ON profile_memories.id = profile_memories_fts.rowid
        WHERE profile_memories_fts MATCH ?
        ORDER BY bm25(profile_memories_fts),
                 profile_memories.created_at DESC,
                 profile_memories.id DESC
        LIMIT ?
        """,
        (match_expression, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def _search_session_history_fts(
    connection: sqlite3.Connection,
    session_id: str,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    match_expression = _fts_match_expression(query)
    if not match_expression:
        return []

    # Fetch extras so noise filtering does not collapse the result set too aggressively.
    raw_limit = max(limit * 3, 24)
    rows = connection.execute(
        """
        SELECT session_messages.id,
               session_messages.session_id,
               session_messages.role,
               session_messages.content,
               session_messages.created_at
        FROM session_messages_fts
        JOIN session_messages ON session_messages.id = session_messages_fts.rowid
        WHERE session_messages_fts MATCH ?
          AND session_messages.session_id = ?
        ORDER BY bm25(session_messages_fts),
                 session_messages.created_at DESC,
                 session_messages.id DESC
        LIMIT ?
        """,
        (match_expression, session_id, raw_limit),
    ).fetchall()
    filtered = _filter_session_messages([dict(row) for row in rows])
    return filtered[:limit]


def _is_noise_assistant_text(content: str) -> bool:
    content = content.strip()
    if not content:
        return True
    if content in SESSION_NOISE_RESPONSES:
        return True
    if SESSION_NOISE_PATTERN.fullmatch(content) is not None:
        return True
    if SESSION_PROTOCOL_PATTERN.match(content) is not None:
        return True
    return SESSION_SPECIAL_TOKEN_PATTERN.search(content) is not None


def _is_noise_assistant_message(record: dict[str, Any]) -> bool:
    role = str(record.get("role", "")).strip().lower()
    if role != "assistant":
        return False
    return _is_noise_assistant_text(str(record.get("content", "")))


def _filter_session_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for message in messages:
        if _is_noise_assistant_message(message):
            if filtered and str(filtered[-1].get("role", "")).strip().lower() == "user":
                filtered.pop()
            continue
        filtered.append(message)
    return filtered


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


def save_profile_memory(text: str, category: str | None = None) -> dict[str, Any]:
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Profile memory text cannot be empty.")

    clean_category = _normalize_profile_category(category)
    created_at = _utc_now()
    with _connect() as connection:
        if clean_category in PROFILE_SINGLETON_CATEGORIES:
            existing = connection.execute(
                """
                SELECT id, category, text, created_at
                FROM profile_memories
                WHERE category = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (clean_category,),
            ).fetchone()
            if existing is not None and str(existing["text"]).strip().lower() == clean_text.lower():
                return dict(existing)
            connection.execute(
                "DELETE FROM profile_memories WHERE category = ?",
                (clean_category,),
            )
        else:
            existing = connection.execute(
                """
                SELECT id, category, text, created_at
                FROM profile_memories
                WHERE category = ? AND lower(text) = lower(?)
                ORDER BY id ASC
                LIMIT 1
                """,
                (clean_category, clean_text),
            ).fetchone()
            if existing is not None:
                return dict(existing)

        cursor = connection.execute(
            "INSERT INTO profile_memories (category, text, created_at) VALUES (?, ?, ?)",
            (clean_category, clean_text, created_at),
        )
        profile_id = int(cursor.lastrowid)
        connection.commit()

    return {
        "id": profile_id,
        "category": clean_category,
        "text": clean_text,
        "created_at": created_at,
    }


def search_notes(query: str | None = None, limit: int = DEFAULT_NOTE_LIMIT) -> list[dict[str, Any]]:
    max_results = _coerce_limit(limit)
    clean_query = (query or "").strip()
    fetch_limit = max(200, max_results)

    with _connect() as connection:
        if clean_query and _FTS5_AVAILABLE:
            fts_rows = _search_notes_fts(connection, clean_query, max_results)
            if fts_rows:
                return fts_rows

        rows = connection.execute(
            """
            SELECT id, text, created_at
            FROM notes
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """
            ,
            (fetch_limit,),
        ).fetchall()

    notes = [dict(row) for row in rows]
    return _rank_text_records(notes, query=clean_query, limit=max_results)


def search_profile_memories(
    query: str | None = None,
    limit: int = DEFAULT_PROFILE_LIMIT,
) -> list[dict[str, Any]]:
    max_results = _coerce_limit(limit, default=DEFAULT_PROFILE_LIMIT)
    clean_query = (query or "").strip()
    fetch_limit = max(200, max_results)

    with _connect() as connection:
        if clean_query and _FTS5_AVAILABLE:
            fts_rows = _search_profile_memories_fts(connection, clean_query, max_results)
            if fts_rows:
                return fts_rows

        rows = connection.execute(
            """
            SELECT id, category, text, created_at
            FROM profile_memories
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """
            ,
            (fetch_limit,),
        ).fetchall()

    memories = [dict(row) for row in rows]
    return _rank_text_records(memories, query=clean_query, limit=max_results)


def save_session_exchange(session_id: str, user_content: str, assistant_content: str) -> None:
    clean_session = session_id.strip()
    if not clean_session:
        raise ValueError("session_id cannot be empty.")

    clean_assistant = assistant_content.strip()
    if _is_noise_assistant_text(clean_assistant):
        return

    records = (
        ("user", user_content.strip()),
        ("assistant", clean_assistant),
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
    return _filter_session_messages(messages)


def search_session_history(
    session_id: str,
    query: str | None = None,
    limit: int = DEFAULT_SESSION_LIMIT,
) -> list[dict[str, Any]]:
    clean_session = session_id.strip()
    if not clean_session:
        return []

    max_results = _coerce_limit(limit, default=DEFAULT_SESSION_LIMIT)
    clean_query = (query or "").strip()
    with _connect() as connection:
        if clean_query and _FTS5_AVAILABLE:
            fts_rows = _search_session_history_fts(
                connection,
                clean_session,
                clean_query,
                max_results,
            )
            if fts_rows:
                return fts_rows

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
    messages.reverse()
    filtered_messages = _filter_session_messages(messages)
    return _rank_text_records(
        filtered_messages,
        query=clean_query,
        limit=max_results,
        text_key="content",
    )


def vault_snapshot(
    session_id: str | None = None,
    *,
    note_limit: int = 5,
    profile_limit: int = 5,
    history_limit: int = 6,
) -> dict[str, Any]:
    clean_session = str(session_id or "").strip()
    note_max = _coerce_limit(note_limit)
    profile_max = _coerce_limit(profile_limit, default=DEFAULT_PROFILE_LIMIT)
    history_max = _coerce_limit(history_limit, default=DEFAULT_SESSION_LIMIT)

    with _connect() as connection:
        note_count = int(connection.execute("SELECT COUNT(*) FROM notes").fetchone()[0])
        profile_count = int(connection.execute("SELECT COUNT(*) FROM profile_memories").fetchone()[0])

        recent_notes = [
            dict(row)
            for row in connection.execute(
                """
                SELECT id, text, created_at
                FROM notes
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (note_max,),
            ).fetchall()
        ]
        recent_profile_memories = [
            dict(row)
            for row in connection.execute(
                """
                SELECT id, category, text, created_at
                FROM profile_memories
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (profile_max,),
            ).fetchall()
        ]

        session_message_count = 0
        recent_session_history: list[dict[str, Any]] = []
        if clean_session:
            session_message_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM session_messages WHERE session_id = ?",
                    (clean_session,),
                ).fetchone()[0]
            )
            recent_session_history = _filter_session_messages(
                [
                    dict(row)
                    for row in connection.execute(
                        """
                        SELECT id, session_id, role, content, created_at
                        FROM session_messages
                        WHERE session_id = ?
                        ORDER BY created_at DESC, id DESC
                        LIMIT ?
                        """,
                        (clean_session, history_max),
                    ).fetchall()
                ]
            )
            recent_session_history.reverse()

    return {
        "session_id": clean_session,
        "note_count": note_count,
        "profile_count": profile_count,
        "session_message_count": session_message_count,
        "recent_notes": recent_notes,
        "recent_profile_memories": recent_profile_memories,
        "recent_session_history": recent_session_history,
    }
