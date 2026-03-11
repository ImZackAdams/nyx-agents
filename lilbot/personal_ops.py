"""Structured personal-ops helpers built from lilbot's local vault."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import re
from typing import Any

from lilbot.memory.memory import (
    save_note,
    save_profile_memory,
    search_notes,
    search_profile_memories,
    search_session_history,
    vault_snapshot,
)


DEFAULT_OPS_LIMIT = 8
_NOTE_SCAN_LIMIT = 400
_PROFILE_SCAN_LIMIT = 160
_RAW_CAPTURE_LIMIT = 4
_FILLER_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "for",
        "from",
        "in",
        "is",
        "my",
        "of",
        "on",
        "the",
        "to",
        "with",
    }
)
_SHARE_THEME_STOPWORDS = _FILLER_WORDS.union(
    {
        "active",
        "admin",
        "address",
        "america",
        "build",
        "call",
        "carry",
        "commitment",
        "commitments",
        "context",
        "deadline",
        "deadlines",
        "detail",
        "details",
        "due",
        "email",
        "finish",
        "goal",
        "have",
        "keep",
        "life",
        "lilbot",
        "local",
        "need",
        "notes",
        "number",
        "office",
        "open",
        "opens",
        "ops",
        "personal",
        "phone",
        "plan",
        "planning",
        "preference",
        "preferences",
        "private",
        "project",
        "projects",
        "reference",
        "references",
        "remembered",
        "renew",
        "save",
        "saved",
        "schedule",
        "send",
        "soon",
        "submit",
        "terminal",
        "thread",
        "threads",
        "timezone",
        "todo",
        "vault",
        "window",
        "york",
        "jan",
        "january",
        "feb",
        "february",
        "mar",
        "march",
        "apr",
        "april",
        "may",
        "jun",
        "june",
        "jul",
        "july",
        "aug",
        "august",
        "sep",
        "sept",
        "september",
        "oct",
        "october",
        "nov",
        "november",
        "dec",
        "december",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    }
)
_TAG_PATTERN = re.compile(r"^\s*(commitment|thread|project|reference|ref|note)\s*:\s*(.+)$", re.IGNORECASE)
_COMMITMENT_HINT_PATTERN = re.compile(
    r"\b("
    r"appointment|book|by|call|cancel|deadline|due|email|follow up|follow-up|"
    r"have to|must|need to|pay|register|renew|renewal|reply|schedule|send|submit|"
    r"todo|to-do|update|visit"
    r")\b",
    re.IGNORECASE,
)
_THREAD_HINT_PATTERN = re.compile(
    r"\b("
    r"moving|job search|taxes|trip|travel|wedding|renovation|onboarding|planning|"
    r"project|thread|working on|researching|preparing for|training for"
    r")\b",
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"\b[^\s,;]+@[^\s,;]+\b")
_URL_PATTERN = re.compile(r"\b(?:https?://|www\.)\S+\b", re.IGNORECASE)
_PHONE_PATTERN = re.compile(r"\b(?:\+?\d[\d(). -]{6,}\d)\b")
_LONG_NUMBER_PATTERN = re.compile(r"\b\d{4,}\b")
_SHARE_TOKEN_PATTERN = re.compile(r"[a-z][a-z0-9_+-]{2,}")
_DATE_PHRASE_PATTERN = re.compile(
    r"\b(?:by|before|on|due(?: on)?|deadline(?: is|:)?|renewal deadline is)\b.+$",
    re.IGNORECASE,
)
_ISO_DATE_PATTERN = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_SLASH_DATE_PATTERN = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
_MONTH_DATE_PATTERN = re.compile(
    r"\b("
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:tember)?|sept(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r")\s+(\d{1,2})(?:,\s*|\s+)?(\d{4})?\b",
    re.IGNORECASE,
)
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def save_commitment(text: str) -> dict[str, Any]:
    return save_note(_normalize_tagged_capture(text, "commitment"))


def save_thread(text: str) -> dict[str, Any]:
    return save_note(_normalize_tagged_capture(text, "thread"))


def save_reference(text: str) -> dict[str, Any]:
    return save_note(_normalize_tagged_capture(text, "reference"))


def save_preference(text: str) -> dict[str, Any]:
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Preference text cannot be empty.")
    if ":" not in clean_text:
        clean_text = f"preference: {clean_text}"
    return save_profile_memory(clean_text, "preference")


def list_commitments(
    query: str | None = None,
    *,
    limit: int = DEFAULT_OPS_LIMIT,
) -> list[dict[str, Any]]:
    source_query = query if query and query.strip() else None
    notes = search_notes(source_query, limit=max(limit * 8, _NOTE_SCAN_LIMIT))
    records = [_commitment_record(note) for note in notes]
    return _finalize_records(records, query=query, limit=limit, prioritize_due_dates=True)


def list_threads(
    query: str | None = None,
    *,
    limit: int = DEFAULT_OPS_LIMIT,
) -> list[dict[str, Any]]:
    source_query = query if query and query.strip() else None
    notes = search_notes(source_query, limit=max(limit * 8, _NOTE_SCAN_LIMIT))
    records = [_thread_record(note) for note in notes]

    profile_memories = search_profile_memories(source_query, limit=max(limit * 6, _PROFILE_SCAN_LIMIT))
    records.extend(_thread_record_from_profile(memory) for memory in profile_memories)
    return _finalize_records(records, query=query, limit=limit)


def list_references(
    query: str | None = None,
    *,
    limit: int = DEFAULT_OPS_LIMIT,
) -> list[dict[str, Any]]:
    source_query = query if query and query.strip() else None
    notes = search_notes(source_query, limit=max(limit * 8, _NOTE_SCAN_LIMIT))
    records = [_reference_record(note) for note in notes]
    return _finalize_records(records, query=query, limit=limit)


def list_preferences(
    query: str | None = None,
    *,
    limit: int = DEFAULT_OPS_LIMIT,
) -> list[dict[str, Any]]:
    memories = search_profile_memories(query if query and query.strip() else None, limit=max(limit * 5, 80))
    records: list[dict[str, Any]] = []
    for memory in memories:
        text = str(memory.get("text", "")).strip()
        if not text:
            continue
        category = str(memory.get("category", "profile")).strip() or "profile"
        records.append(
            {
                "id": int(memory.get("id", 0)),
                "kind": "preference",
                "category": category,
                "title": _preference_title(text, category),
                "detail": text,
                "created_at": str(memory.get("created_at", "")),
                "search_text": f"{category} {text}",
            }
        )
    return _finalize_records(records, query=query, limit=limit)


def build_personal_ops_brief(
    query: str | None = None,
    *,
    session_id: str | None = None,
) -> str:
    clean_query = (query or "").strip()
    commitments = list_commitments(clean_query or None, limit=5)
    threads = list_threads(clean_query or None, limit=4)
    references = list_references(clean_query or None, limit=3)
    preferences = list_preferences(clean_query or None, limit=4)
    if clean_query and not preferences:
        preferences = list_preferences(limit=2)
    raw_captures = _raw_capture_records(clean_query or None, limit=_RAW_CAPTURE_LIMIT)
    session_hits = (
        search_session_history(str(session_id).strip(), clean_query, limit=3)
        if clean_query and session_id and str(session_id).strip()
        else []
    )

    lines = ["Personal ops brief"]
    if clean_query:
        lines.append(f"Topic: {clean_query}")

    if commitments:
        lines.append("Open commitments:")
        lines.extend(f"- {_format_commitment_line(record)}" for record in commitments)

    if threads:
        lines.append("Active threads:")
        lines.extend(f"- {record['title']}" for record in threads)

    if preferences:
        lines.append("Preferences and context:")
        lines.extend(f"- {record['detail']}" for record in preferences)

    if references:
        lines.append("Saved references:")
        lines.extend(f"- {record['detail']}" for record in references)

    if raw_captures:
        lines.append("Recent captures:")
        lines.extend(f"- {record['detail']}" for record in raw_captures)

    if session_hits:
        lines.append("Recent session context:")
        lines.extend(f"- [{item['role']}] {item['content']}" for item in session_hits)

    if len(lines) == 1:
        if clean_query:
            return f'No saved personal-ops context matched "{clean_query}".'
        return "No saved personal-ops context yet."
    return "\n".join(lines)


def build_viral_launch_pack(
    query: str | None = None,
    *,
    session_id: str | None = None,
) -> str:
    clean_query = (query or "").strip()
    snapshot = personal_ops_snapshot(session_id)
    commitments = list_commitments(clean_query or None, limit=5)
    threads = list_threads(clean_query or None, limit=4)
    references = list_references(clean_query or None, limit=4)
    preferences = list_preferences(clean_query or None, limit=4)
    captures = _raw_capture_records(clean_query or None, limit=3)

    total_saved_items = (
        snapshot["note_count"]
        + snapshot["commitment_count"]
        + snapshot["thread_count"]
        + snapshot["reference_count"]
        + snapshot["preference_count"]
    )
    if total_saved_items == 0:
        return (
            "Lilbot needs some receipts before it can generate a viral pack. "
            "Save a commitment, thread, reference, or preference first."
        )

    due_soon_count = _count_due_within_days(commitments, days=7)
    themes = _top_share_themes(
        clean_query,
        commitments=commitments,
        threads=threads,
        references=references,
        preferences=preferences,
        captures=captures,
    )

    counts = [
        f"{snapshot['commitment_count']} {_pluralize(snapshot['commitment_count'], 'commitment')}",
        f"{snapshot['thread_count']} active {_pluralize(snapshot['thread_count'], 'thread')}",
        f"{snapshot['reference_count']} saved {_pluralize(snapshot['reference_count'], 'reference')}",
        f"{snapshot['preference_count']} remembered {_pluralize(snapshot['preference_count'], 'preference')}",
    ]
    if snapshot["note_count"] > 0:
        counts.append(f"{snapshot['note_count']} raw {_pluralize(snapshot['note_count'], 'capture')}")

    lines = [
        "Lilbot viral pack",
        "",
        "Hook:",
        _viral_hook(themes),
        "",
        "Post:",
        (
            f"Lilbot currently keeps {_human_join(counts)} in one private local vault."
            f"{_due_soon_sentence(due_soon_count)}"
        ),
    ]
    if themes:
        lines.append(f"Current themes: {_human_join(themes)}.")
    lines.extend(
        [
            "No SaaS, no browser sprawl, and no cloud dependency. Just a terminal-native personal ops system that remembers context and surfaces what matters next.",
            "Built with Lilbot, a private local personal ops vault for people who prefer terminals over tabs.",
            "",
            "Receipt card:",
            "Lilbot receipts",
            f"- {snapshot['commitment_count']} {_pluralize(snapshot['commitment_count'], 'commitment')} tracked",
            f"- {snapshot['thread_count']} active {_pluralize(snapshot['thread_count'], 'thread')} kept moving",
            f"- {snapshot['reference_count']} saved {_pluralize(snapshot['reference_count'], 'reference')} within reach",
            f"- {snapshot['preference_count']} {_pluralize(snapshot['preference_count'], 'preference')} remembered",
        ]
    )
    if snapshot["note_count"] > 0:
        lines.append(f"- {snapshot['note_count']} raw {_pluralize(snapshot['note_count'], 'capture')} processed")
    if due_soon_count > 0:
        lines.append(f"- {due_soon_count} {_pluralize(due_soon_count, 'deadline')} due within 7 days")
    if themes:
        lines.append(f"- Themes: {_human_join(themes)}")
    lines.extend(
        [
            "",
            "CTA:",
            "If your to-do list keeps losing context, replace it with a personal ops vault.",
        ]
    )
    return "\n".join(lines)


def personal_ops_snapshot(session_id: str | None = None) -> dict[str, Any]:
    snapshot = vault_snapshot(session_id, note_limit=4, profile_limit=4, history_limit=4)
    commitments = list_commitments(limit=64)
    threads = list_threads(limit=64)
    references = list_references(limit=64)
    preferences = list_preferences(limit=24)
    upcoming_commitments = [record for record in commitments if record.get("due_at")][:3]

    return {
        **snapshot,
        "commitment_count": len(commitments),
        "thread_count": len(threads),
        "reference_count": len(references),
        "preference_count": len(preferences),
        "upcoming_commitments": upcoming_commitments,
        "active_threads": threads[:3],
        "recent_preferences": preferences[:4],
        "recent_references": references[:3],
    }


def _count_due_within_days(records: list[dict[str, Any]], *, days: int) -> int:
    today = datetime.now(timezone.utc).date()
    count = 0
    for record in records:
        due_at = str(record.get("due_at", "")).strip()
        if not due_at:
            continue
        try:
            due_date = date.fromisoformat(due_at)
        except ValueError:
            continue
        delta = (due_date - today).days
        if 0 <= delta <= days:
            count += 1
    return count


def _top_share_themes(
    query: str,
    *,
    commitments: list[dict[str, Any]],
    threads: list[dict[str, Any]],
    references: list[dict[str, Any]],
    preferences: list[dict[str, Any]],
    captures: list[dict[str, Any]],
    limit: int = 3,
) -> list[str]:
    weighted_texts: list[tuple[str, int]] = []
    if query:
        weighted_texts.append((query, 3))
    weighted_texts.extend((str(record.get("title", "")), 4) for record in commitments)
    weighted_texts.extend((str(record.get("title", "")), 5) for record in threads)
    weighted_texts.extend((str(record.get("detail", "")), 3) for record in references)
    weighted_texts.extend((str(record.get("detail", "")), 1) for record in preferences)
    weighted_texts.extend((str(record.get("detail", "")), 1) for record in captures)

    scores: dict[str, int] = {}
    for text, weight in weighted_texts:
        seen_in_text: set[str] = set()
        for token in _share_theme_tokens(text):
            if token in seen_in_text:
                continue
            seen_in_text.add(token)
            scores[token] = scores.get(token, 0) + weight

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _ in ranked[:limit]]


def _share_theme_tokens(text: str) -> list[str]:
    sanitized = _sanitize_share_source(text)
    return [
        token
        for token in _SHARE_TOKEN_PATTERN.findall(sanitized.lower())
        if token not in _SHARE_THEME_STOPWORDS and not any(character.isdigit() for character in token)
    ]


def _sanitize_share_source(text: str) -> str:
    sanitized = _URL_PATTERN.sub(" ", text)
    sanitized = _EMAIL_PATTERN.sub(" ", sanitized)
    sanitized = _PHONE_PATTERN.sub(" ", sanitized)
    sanitized = _LONG_NUMBER_PATTERN.sub(" ", sanitized)
    return sanitized


def _viral_hook(themes: list[str]) -> str:
    if themes:
        return (
            f"I built Lilbot because {themes[0]} context kept leaking across tabs, notes, and half-finished threads."
        )
    return "I built Lilbot because life admin kept leaking across tabs, notes, and half-finished threads."


def _due_soon_sentence(due_soon_count: int) -> str:
    if due_soon_count <= 0:
        return ""
    return f" {due_soon_count} {_pluralize(due_soon_count, 'deadline')} land in the next 7 days."


def _pluralize(count: int, singular: str, plural: str | None = None) -> str:
    if count == 1:
        return singular
    return plural or f"{singular}s"


def _human_join(items: list[str]) -> str:
    clean_items = [item.strip() for item in items if item.strip()]
    if not clean_items:
        return ""
    if len(clean_items) == 1:
        return clean_items[0]
    if len(clean_items) == 2:
        return f"{clean_items[0]} and {clean_items[1]}"
    return f"{', '.join(clean_items[:-1])}, and {clean_items[-1]}"


def _normalize_tagged_capture(text: str, tag: str) -> str:
    clean_text = text.strip()
    if not clean_text:
        raise ValueError(f"{tag.capitalize()} text cannot be empty.")

    match = _TAG_PATTERN.match(clean_text)
    if match is not None:
        existing_tag = match.group(1).strip().lower()
        if existing_tag in {tag, "project" if tag == "thread" else tag, "ref" if tag == "reference" else tag}:
            return f"{tag}: {match.group(2).strip()}"
    return f"{tag}: {clean_text}"


def _commitment_record(note: dict[str, Any]) -> dict[str, Any] | None:
    detail = _tagged_payload(str(note.get("text", "")), "commitment")
    text = detail or str(note.get("text", "")).strip()
    if not text or (detail is None and not _looks_like_commitment_text(text)):
        return None
    due_at = _extract_due_at(text)
    return {
        "id": int(note.get("id", 0)),
        "kind": "commitment",
        "title": _title_without_due(text),
        "detail": text,
        "due_at": due_at,
        "created_at": str(note.get("created_at", "")),
        "search_text": f"{text} {due_at}",
    }


def _thread_record(note: dict[str, Any]) -> dict[str, Any] | None:
    explicit_thread = _tagged_payload(str(note.get("text", "")), "thread")
    explicit_project = _tagged_payload(str(note.get("text", "")), "project")
    text = explicit_thread or explicit_project or str(note.get("text", "")).strip()
    if not text or (explicit_thread is None and explicit_project is None and not _looks_like_thread_text(text)):
        return None
    return {
        "id": int(note.get("id", 0)),
        "kind": "thread",
        "title": _compact_title(text),
        "detail": text,
        "created_at": str(note.get("created_at", "")),
        "search_text": text,
    }


def _reference_record(note: dict[str, Any]) -> dict[str, Any] | None:
    detail = _tagged_payload(str(note.get("text", "")), "reference") or _tagged_payload(
        str(note.get("text", "")),
        "ref",
    )
    if detail is None:
        return None
    return {
        "id": int(note.get("id", 0)),
        "kind": "reference",
        "title": _compact_title(detail),
        "detail": detail,
        "created_at": str(note.get("created_at", "")),
        "search_text": detail,
    }


def _thread_record_from_profile(memory: dict[str, Any]) -> dict[str, Any] | None:
    category = str(memory.get("category", "")).strip().lower()
    text = str(memory.get("text", "")).strip()
    if category != "goal" or not text:
        return None
    return {
        "id": int(memory.get("id", 0)),
        "kind": "thread",
        "title": _compact_title(text),
        "detail": text,
        "created_at": str(memory.get("created_at", "")),
        "search_text": f"{category} {text}",
    }


def _raw_capture_records(query: str | None, *, limit: int) -> list[dict[str, Any]]:
    notes = search_notes(query if query and query.strip() else None, limit=max(limit * 3, 24))
    captures: list[dict[str, Any]] = []
    for note in notes:
        text = str(note.get("text", "")).strip()
        if not text or _TAG_PATTERN.match(text) is not None:
            continue
        captures.append(
            {
                "id": int(note.get("id", 0)),
                "detail": text,
                "created_at": str(note.get("created_at", "")),
            }
        )
    return captures[:limit]


def _tagged_payload(text: str, tag: str) -> str | None:
    match = _TAG_PATTERN.match(text.strip())
    if match is None:
        return None
    if match.group(1).strip().lower() != tag:
        return None
    payload = match.group(2).strip()
    return payload or None


def _looks_like_commitment_text(text: str) -> bool:
    if _tagged_payload(text, "commitment") is not None:
        return True
    lowered = text.lower()
    if lowered.startswith(("todo:", "to-do:", "task:")):
        return True
    return _COMMITMENT_HINT_PATTERN.search(text) is not None


def _looks_like_thread_text(text: str) -> bool:
    if _tagged_payload(text, "thread") is not None or _tagged_payload(text, "project") is not None:
        return True
    return _THREAD_HINT_PATTERN.search(text) is not None


def _extract_due_at(text: str) -> str:
    lowered = text.lower()
    today = datetime.now(timezone.utc).date()
    if "tomorrow" in lowered:
        return (today + timedelta(days=1)).isoformat()
    if "today" in lowered:
        return today.isoformat()

    iso_match = _ISO_DATE_PATTERN.search(text)
    if iso_match is not None:
        return _safe_iso_date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))

    slash_match = _SLASH_DATE_PATTERN.search(text)
    if slash_match is not None:
        month = int(slash_match.group(1))
        day = int(slash_match.group(2))
        year_text = slash_match.group(3)
        year = _coerce_year(year_text, today.year)
        if year is not None:
            return _roll_forward_if_needed(year, month, day, year_text is None, today)

    month_match = _MONTH_DATE_PATTERN.search(text)
    if month_match is not None:
        month_name = month_match.group(1).lower()
        month = _MONTHS.get(month_name)
        if month is not None:
            day = int(month_match.group(2))
            year_text = month_match.group(3)
            year = _coerce_year(year_text, today.year)
            if year is not None:
                return _roll_forward_if_needed(year, month, day, year_text is None, today)

    return ""


def _coerce_year(year_text: str | None, default_year: int) -> int | None:
    if year_text is None or not year_text.strip():
        return default_year
    year = int(year_text)
    if year < 100:
        year += 2000
    return year


def _roll_forward_if_needed(
    year: int,
    month: int,
    day: int,
    infer_next_year: bool,
    today: date,
) -> str:
    try:
        candidate = datetime(year, month, day, tzinfo=timezone.utc).date()
    except ValueError:
        return ""
    if infer_next_year and candidate < today:
        try:
            candidate = datetime(year + 1, month, day, tzinfo=timezone.utc).date()
        except ValueError:
            return ""
    return candidate.isoformat()


def _safe_iso_date(year: int, month: int, day: int) -> str:
    try:
        return datetime(year, month, day, tzinfo=timezone.utc).date().isoformat()
    except ValueError:
        return ""


def _title_without_due(text: str) -> str:
    base = _DATE_PHRASE_PATTERN.sub("", text).strip(" -.,;:")
    if not base:
        base = text.strip()
    return _compact_title(base)


def _compact_title(text: str, *, max_words: int = 10) -> str:
    words = text.strip().split()
    if not words:
        return ""
    clipped = words[:max_words]
    title = " ".join(clipped).strip(" -.,;:")
    if len(words) > max_words:
        title += " ..."
    return title


def _preference_title(text: str, category: str) -> str:
    if ":" in text:
        label, value = text.split(":", 1)
        value = value.strip()
        if value:
            return value
        return label.strip()
    return f"{category}: {text}"


def _finalize_records(
    records: list[dict[str, Any] | None],
    *,
    query: str | None,
    limit: int,
    prioritize_due_dates: bool = False,
) -> list[dict[str, Any]]:
    clean_records = [record for record in records if record is not None]
    deduped = _dedupe_records(clean_records)
    if query and query.strip():
        ranked = _rank_records(deduped, query.strip())
    else:
        ranked = list(deduped)

    ranked.sort(key=lambda record: record.get("created_at", ""), reverse=True)
    if prioritize_due_dates:
        ranked.sort(key=lambda record: (not bool(record.get("due_at")), str(record.get("due_at") or "9999-12-31")))
    return ranked[: max(1, int(limit))]


def _dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        fingerprint = re.sub(r"\s+", " ", str(record.get("detail", "")).strip().lower())
        if not fingerprint:
            fingerprint = re.sub(r"\s+", " ", str(record.get("title", "")).strip().lower())
        if not fingerprint or fingerprint in seen:
            continue
        seen.add(fingerprint)
        deduped.append(record)
    return deduped


def _rank_records(records: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    query_tokens = [token for token in re.findall(r"[a-z0-9_]{2,}", query.lower()) if token not in _FILLER_WORDS]
    if not query_tokens:
        return records

    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, record in enumerate(records):
        haystack = str(record.get("search_text", "")).lower()
        if not haystack:
            continue
        score = sum(3 if f" {token} " in f" {haystack} " else 1 for token in query_tokens if token in haystack)
        if score == 0:
            continue
        scored.append((score, -index, record))

    if not scored:
        return []
    scored.sort(reverse=True)
    return [record for _, _, record in scored]


def _format_commitment_line(record: dict[str, Any]) -> str:
    due_at = str(record.get("due_at", "")).strip()
    if due_at:
        return f"{record['title']} (due {due_at})"
    return str(record.get("title", record.get("detail", "")))
