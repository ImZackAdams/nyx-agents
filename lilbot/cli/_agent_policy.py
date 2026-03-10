from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import re
from typing import Any

from lilbot.cli._agent_protocol import _sanitize_answer_text
from lilbot.cli._agent_types import ConversationMessage, TokenCallback
from lilbot.memory.memory import search_notes, search_profile_memories, search_session_history


DEFAULT_RELEVANT_PROFILE_LIMIT = 4
DEFAULT_RELEVANT_NOTE_LIMIT = 3
DEFAULT_RELEVANT_HISTORY_LIMIT = 4
PERSONAL_FACT_PATTERN = re.compile(
    r"\b(my name|who am i|what'?s my name|what is my name|my email|my phone|my address|my pronouns|my timezone)\b",
    re.IGNORECASE,
)
ASSISTANT_IDENTITY_PATTERN = re.compile(
    r"\b(?:what'?s your name|what is your name|who are you)\b",
    re.IGNORECASE,
)
GREETING_PATTERN = re.compile(r"^\s*(?:hi|hello|hey)\b[!.? ]*$", re.IGNORECASE)
PROFILE_REQUEST_PATTERN = re.compile(
    r"\b(what do you know about me|tell me about me|summarize my profile|my profile|about me|what should you remember about me|what are my preferences|what do i prefer|what are my goals)\b",
    re.IGNORECASE,
)
CLI_ROUTING_PATTERN = re.compile(
    r"\b(?:how|explain)\b.*\b(?:cli|command line)\b.*\b(?:! ?commands?|llm|decides?|route|routing)\b|\bhow .*run a ! ?command or the llm\b",
    re.IGNORECASE,
)
LAST_QUESTION_PATTERN = re.compile(
    r"\b(what did i just ask(?: you)?|what was my last question|what did i ask(?: you)? just now)\b",
    re.IGNORECASE,
)
SUMMARY_HINT_PATTERN = re.compile(
    r"\b(summarize|summary|overview|describe|explain|what does .* do)\b",
    re.IGNORECASE,
)
NOTE_REQUEST_PATTERN = re.compile(r"\bnotes?\b", re.IGNORECASE)
HISTORY_REQUEST_PATTERN = re.compile(
    r"\b(history|last time|earlier conversation|previous conversation|what did we|what did i ask)\b",
    re.IGNORECASE,
)
README_REQUEST_PATTERN = re.compile(r"\breadme(?:\.md)?\b", re.IGNORECASE)
FILE_LIST_REQUEST_PATTERN = re.compile(
    r"\b(?:what|which|list|show|display)\b.*\b(?:files?|director(?:y|ies)|folders?)\b|\b(?:files?|director(?:y|ies)|folders?)\b.*\b(?:are in|in this|under)\b|\bwhat(?:'s| is)?\s+in\s+this\s+(?:director(?:y|ies)|folder)\b",
    re.IGNORECASE,
)
NOTE_LIST_REQUEST_PATTERN = re.compile(
    r"\b(?:what|which|list|show|display)\b.*\bnotes?\b|\bnotes?\b.*\b(?:do i have|are there|have i saved)\b",
    re.IGNORECASE,
)
HISTORY_LIST_REQUEST_PATTERN = re.compile(
    r"\b(?:what|which|list|show|display)\b.*\bhistory\b|\bhistory\b.*\b(?:do i have|is there)\b",
    re.IGNORECASE,
)
SESSION_ID_PATTERN = re.compile(r"\bsession id\b", re.IGNORECASE)
TIMESTAMP_SUFFIX_PATTERN = re.compile(r"\s+\(\d{4}-\d{2}-\d{2}T[^)]*\)\s*$")
QUERY_TOKEN_PATTERN = re.compile(r"[a-z0-9_]{2,}")
NAME_VALUE_PATTERN = re.compile(
    r"\b(?:my name is|name\s*[:=-])\s*([A-Za-z][A-Za-z' -]{0,40})",
    re.IGNORECASE,
)
EMAIL_VALUE_PATTERN = re.compile(
    r"\b(?:my )?email(?: address)?(?: is|:)?\s+([^\s,;]+@[^\s,;]+)",
    re.IGNORECASE,
)
PHONE_VALUE_PATTERN = re.compile(
    r"\b(?:my )?phone(?: number)?(?: is|:)?\s+([0-9][0-9() .+-]{6,}[0-9])",
    re.IGNORECASE,
)
ADDRESS_VALUE_PATTERN = re.compile(
    r"\b(?:my )?address(?: is|:)\s+(.+)",
    re.IGNORECASE,
)
PRONOUNS_VALUE_PATTERN = re.compile(
    r"\b(?:my )?pronouns(?: are|:)\s+(.+)",
    re.IGNORECASE,
)
TIMEZONE_VALUE_PATTERN = re.compile(
    r"\b(?:my )?timezone(?: is|:)\s+([A-Za-z0-9_./+-]+)",
    re.IGNORECASE,
)
PREFERENCE_VALUE_PATTERN = re.compile(
    r"\b(?:i prefer|i usually use|i like to use)\s+(.+)",
    re.IGNORECASE,
)
FAVORITE_VALUE_PATTERN = re.compile(
    r"\bmy favorite\s+([A-Za-z0-9 _-]{2,30})\s+is\s+(.+)",
    re.IGNORECASE,
)
GOAL_VALUE_PATTERN = re.compile(
    r"\b(?:my goal is|i(?:'m| am) trying to|i want to)\s+(.+)",
    re.IGNORECASE,
)
NOTE_QUERY_STOPWORDS = frozenset(
    {
        "about",
        "all",
        "any",
        "are",
        "based",
        "can",
        "do",
        "from",
        "have",
        "in",
        "list",
        "me",
        "my",
        "note",
        "notes",
        "on",
        "saved",
        "search",
        "show",
        "should",
        "tell",
        "the",
        "there",
        "what",
        "which",
        "you",
        "who",
    }
)
PROFILE_QUERY_STOPWORDS = frozenset(
    {
        "about",
        "are",
        "do",
        "goals",
        "i",
        "know",
        "me",
        "my",
        "preferences",
        "profile",
        "remember",
        "should",
        "tell",
        "what",
        "you",
    }
)
HISTORY_QUERY_STOPWORDS = frozenset(
    {
        "about",
        "are",
        "ask",
        "asked",
        "conversation",
        "did",
        "earlier",
        "history",
        "i",
        "just",
        "last",
        "me",
        "my",
        "previous",
        "question",
        "say",
        "said",
        "session",
        "time",
        "we",
        "what",
        "you",
        "who",
    }
)
OBSERVATION_SUFFIX = (
    "Use this observation to answer the user. "
    "Only call another tool if the observation is clearly insufficient."
)


def _trim_history(
    history: Sequence[ConversationMessage],
    history_limit: int,
) -> list[ConversationMessage]:
    if history_limit <= 0:
        return []
    return list(history[-history_limit:])


def _append_exchange(
    history: list[ConversationMessage],
    user_request: str,
    assistant_response: str,
    history_limit: int,
) -> None:
    history.append(ConversationMessage("user", user_request))
    history.append(ConversationMessage("assistant", assistant_response))
    if history_limit > 0 and len(history) > history_limit:
        del history[:-history_limit]


def _save_note_allowed(user_request: str) -> bool:
    request = user_request.lower()
    return any(
        token in request
        for token in ("remember", "save", "store", "memorize", "note this", "write this down")
    )


def _tool_signature(tool_name: str, params: Mapping[str, Any]) -> tuple[str, str]:
    return tool_name, json.dumps(dict(params), ensure_ascii=True, sort_keys=True)


def _observation_message(tool_name: str, observation: str) -> ConversationMessage:
    return ConversationMessage(
        "tool",
        f"{tool_name}: {observation}\n{OBSERVATION_SUFFIX}",
    )


def _relevant_profile_context(
    user_request: str,
    limit: int = DEFAULT_RELEVANT_PROFILE_LIMIT,
) -> str:
    if not _should_prefetch_profile(user_request) and not _looks_like_personal_fact_request(user_request):
        return ""

    query = _profile_query_from_request(user_request)
    memories = search_profile_memories(query, limit=limit)
    if not memories:
        return ""
    return "\n".join(
        f"- {memory['text']} ({memory['created_at']})"
        for memory in memories
    )


def _relevant_note_context(
    user_request: str,
    limit: int = DEFAULT_RELEVANT_NOTE_LIMIT,
) -> str:
    if _should_prefetch_notes(user_request):
        query = _note_query_from_request(user_request)
    elif _looks_like_personal_fact_request(user_request):
        query = _personal_fact_query(user_request)
    else:
        query = user_request
    notes = search_notes(query, limit=limit)
    if not notes:
        return ""
    return "\n".join(
        f"- [{note['id']}] {note['text']} ({note['created_at']})"
        for note in notes
    )


def _relevant_history_context(
    session_id: str,
    user_request: str,
    limit: int = DEFAULT_RELEVANT_HISTORY_LIMIT,
) -> str:
    if not session_id.strip():
        return ""
    if _should_prefetch_history(user_request):
        query = _history_query_from_request(user_request)
    elif _looks_like_personal_fact_request(user_request):
        query = _personal_fact_query(user_request)
    else:
        query = user_request
    messages = search_session_history(session_id, query, limit=limit)
    if not messages:
        return ""
    return "\n".join(
        f"- [{message['role']}] {message['content']} ({message['created_at']})"
        for message in messages
    )


def _coerce_final_answer(
    *,
    user_request: str,
    final_text: str,
    profile_context: str,
    note_context: str,
    history_context: str,
    last_tool_name: str | None,
    last_observation: str | None,
) -> str:
    final_text = _collapse_repeated_paragraphs(_sanitize_answer_text(final_text))

    if _is_greeting_request(user_request) and not _looks_like_greeting_answer(final_text):
        return "Hello. I'm lilbot."

    if _looks_like_personal_fact_request(user_request):
        return _resolve_personal_fact_answer(
            user_request=user_request,
            profile_context=profile_context,
            note_context=note_context,
            history_context=history_context,
            last_observation=last_observation,
        )

    if last_tool_name == "list_files" and _is_file_listing_request(user_request) and last_observation:
        fallback = _fallback_from_observation(user_request, last_tool_name, last_observation)
        if fallback:
            return fallback

    if last_tool_name and last_observation:
        if last_tool_name in {"search_notes", "search_history", "search_profile"} and not _observation_has_results(
            last_observation
        ):
            fallback = _fallback_from_observation(user_request, last_tool_name, last_observation)
            if fallback:
                return fallback
        if _looks_like_unhelpful_answer(final_text):
            fallback = _fallback_from_observation(user_request, last_tool_name, last_observation)
            if fallback:
                return fallback
        if _looks_like_malformed_answer(final_text):
            fallback = _fallback_from_observation(user_request, last_tool_name, last_observation)
            if fallback:
                return fallback
        if last_tool_name == "read_file" and _looks_like_file_dump(final_text, last_observation):
            fallback = _fallback_from_observation(user_request, last_tool_name, last_observation)
            if fallback:
                return fallback
        if last_tool_name == "list_files" and _looks_like_listing_echo(final_text, last_observation):
            fallback = _fallback_from_observation(user_request, last_tool_name, last_observation)
            if fallback:
                return fallback

    return final_text or "(empty response)"


def _resolve_personal_fact_answer(
    *,
    user_request: str,
    profile_context: str,
    note_context: str,
    history_context: str,
    last_observation: str | None,
) -> str:
    fact_value = _extract_personal_fact_value(
        user_request,
        profile_context,
        note_context,
        history_context,
        last_observation,
    )
    if fact_value:
        return fact_value
    return "I don't know based on your saved profile, notes, or session history."


def _personal_fact_declaration_answer(user_request: str) -> str | None:
    patterns, label = _personal_fact_patterns(user_request)
    if not patterns or user_request.strip().endswith("?"):
        return None

    for pattern in patterns:
        match = pattern.search(user_request)
        if match is None:
            continue
        value = _clean_fact_value(match.group(1))
        if value:
            return f"Okay. I'll use {_display_personal_fact_value(label, value)} as your {label} in this session."
    return None


def _recent_personal_fact_answer(
    user_request: str,
    history: Sequence[ConversationMessage],
) -> str | None:
    if not _looks_like_personal_fact_request(user_request):
        return None

    for message in reversed(history):
        if message.role != "user":
            continue
        fact_value = _extract_personal_fact_value(
            user_request,
            "",
            "",
            message.content,
            None,
        )
        if fact_value:
            return fact_value
    return None


def _fallback_answer(
    *,
    user_request: str,
    profile_context: str,
    note_context: str,
    history_context: str,
    last_tool_name: str | None,
    last_observation: str | None,
    default: str,
) -> str:
    if _looks_like_personal_fact_request(user_request):
        return _resolve_personal_fact_answer(
            user_request=user_request,
            profile_context=profile_context,
            note_context=note_context,
            history_context=history_context,
            last_observation=last_observation,
        )

    if last_tool_name and last_observation:
        fallback = _fallback_from_observation(user_request, last_tool_name, last_observation)
        if fallback:
            return fallback

    return default


def _direct_tool_answer(
    *,
    user_request: str,
    last_tool_name: str | None,
    last_observation: str | None,
) -> str | None:
    if not last_tool_name or not last_observation:
        return None

    if last_tool_name == "search_notes" and _is_direct_note_request(user_request):
        return _fallback_from_observation(user_request, last_tool_name, last_observation)

    if last_tool_name == "search_history" and _is_direct_history_request(user_request):
        return _fallback_from_observation(user_request, last_tool_name, last_observation)

    if last_tool_name == "search_profile" and _is_direct_profile_request(user_request):
        return _fallback_from_observation(user_request, last_tool_name, last_observation)

    if last_tool_name == "list_files" and (
        _is_file_listing_request(user_request)
        or _is_summary_request(user_request)
        or _is_repository_request(user_request)
    ):
        return _fallback_from_observation(user_request, last_tool_name, last_observation)

    return None


def _fallback_from_observation(
    user_request: str,
    tool_name: str,
    observation: str,
) -> str | None:
    if observation.startswith(("Refused:", "Tool execution error:", "Unable to ", "Missing required")):
        return observation

    if tool_name in {"search_notes", "search_history"}:
        return _format_memory_observation(user_request, tool_name, observation)

    if tool_name == "search_profile":
        return _format_profile_observation(user_request, observation)

    if tool_name == "read_file":
        if _is_summary_request(user_request):
            return _summarize_text_observation(observation)
        return observation

    if tool_name == "list_files":
        if _is_file_listing_request(user_request):
            return observation
        if _is_summary_request(user_request) or _is_repository_request(user_request):
            return _summarize_listing_observation(observation)
        return observation

    if tool_name == "system_info":
        return observation

    return None


def _format_memory_observation(
    user_request: str,
    tool_name: str,
    observation: str,
) -> str:
    lowered_observation = observation.lower()
    if lowered_observation.startswith("no matching"):
        if tool_name == "search_notes":
            return "I couldn't find matching notes."
        return "I couldn't find matching session history."
    if lowered_observation.startswith("no saved notes"):
        return "You do not have any saved notes yet."
    if lowered_observation.startswith("no session history"):
        return "There is no saved session history yet."

    items = _extract_observation_items(observation)
    if not items:
        return observation

    if tool_name == "search_notes":
        collapsed_items = _collapse_duplicate_items(items)
        unique_items = [item for item, _ in collapsed_items]
        if "based on my notes" in user_request.lower():
            if len(unique_items) == 1:
                return unique_items[0]
            return "Based on your notes:\n" + "\n".join(f"- {item}" for item in unique_items)
        return "Matching notes:\n" + "\n".join(
            f"- {item}" if count == 1 else f"- {item} (saved {count} times)"
            for item, count in collapsed_items
        )

    return "Relevant session history:\n" + "\n".join(f"- {item}" for item in items)


def _format_profile_observation(
    user_request: str,
    observation: str,
) -> str:
    lowered_observation = observation.lower()
    if lowered_observation.startswith("no matching"):
        return "I couldn't find matching profile memories."
    if lowered_observation.startswith("no saved profile"):
        return "I do not have any saved profile memories yet."

    items = _extract_observation_items(observation)
    if not items:
        return observation

    if _looks_like_personal_fact_request(user_request) and items:
        return items[0]

    if _is_direct_profile_request(user_request):
        return "What I know about you:\n" + "\n".join(f"- {item}" for item in items)

    return "Relevant profile memories:\n" + "\n".join(f"- {item}" for item in items)


def _extract_observation_items(observation: str) -> list[str]:
    items: list[str] = []
    for line in observation.splitlines():
        clean_line = line.strip()
        if not clean_line:
            continue
        if clean_line.startswith("[") and "]" in clean_line:
            clean_line = clean_line.split("]", 1)[1].strip()
        clean_line = TIMESTAMP_SUFFIX_PATTERN.sub("", clean_line).strip()
        if clean_line:
            items.append(clean_line)
    return items


def _collapse_duplicate_items(items: Sequence[str]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    order: list[str] = []
    for item in items:
        if item not in counts:
            order.append(item)
            counts[item] = 0
        counts[item] += 1
    return [(item, counts[item]) for item in order]


def _summarize_text_observation(observation: str) -> str:
    stripped = observation.strip()
    if not stripped:
        return "(empty response)"

    markdown_summary = _summarize_markdown_text(stripped)
    if markdown_summary:
        return markdown_summary

    paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n", stripped) if chunk.strip()]
    if not paragraphs:
        return stripped[:300]
    first_paragraph = paragraphs[0]
    sentences = re.split(r"(?<=[.!?])\s+", first_paragraph)
    summary = " ".join(sentence.strip() for sentence in sentences[:2] if sentence.strip()).strip()
    if summary:
        return summary
    return first_paragraph[:300]


def _summarize_markdown_text(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    title = ""
    headings: list[str] = []
    intro_lines: list[str] = []
    in_code_block = False
    seen_intro = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block or not stripped:
            if intro_lines:
                seen_intro = True
            continue
        if stripped.startswith("# "):
            if not title:
                title = stripped[2:].strip()
            continue
        if stripped.startswith("## "):
            headings.append(stripped[3:].strip())
            continue
        if stripped.startswith("- "):
            continue
        if not seen_intro:
            intro_lines.append(stripped)

    intro = " ".join(intro_lines).strip()
    parts: list[str] = []
    if intro:
        parts.append(intro)
    elif title:
        parts.append(f"{title} is the main subject of this document.")

    if headings:
        parts.append(f"It covers {_natural_join(headings[:5])}.")

    return " ".join(part for part in parts if part).strip()


def _summarize_listing_observation(observation: str) -> str:
    entries = [
        line.strip()
        for line in observation.splitlines()
        if line.strip() and not line.startswith("...")
    ]
    if not entries:
        return "(empty directory)"

    directories = [entry.rstrip("/") for entry in entries if entry.endswith("/")]
    files = [entry for entry in entries if not entry.endswith("/")]
    key_files = [
        name
        for name in (
            "README.md",
            "pyproject.toml",
            "requirements.txt",
            "GETTING_STARTED.md",
            "setup.sh",
        )
        if name in files
    ]

    parts = ["This repository appears to be a Python CLI project."]
    if "lilbot" in directories:
        parts.append("The main application code lives in `lilbot/`.")
    if key_files:
        parts.append(f"Top-level files include {_natural_join(key_files[:5])}.")
    if directories:
        parts.append(f"Main directories include {_natural_join(directories[:5])}.")
    return " ".join(parts)


def _collapse_repeated_paragraphs(text: str) -> str:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]
    if len(paragraphs) < 2:
        return text.strip()

    kept: list[str] = []
    for paragraph in paragraphs:
        if any(_paragraphs_are_similar(paragraph, existing) for existing in kept):
            continue
        kept.append(paragraph)

    if not kept:
        return text.strip()
    return "\n\n".join(kept)


def _paragraphs_are_similar(first: str, second: str) -> bool:
    left = _normalize_similarity_text(first)
    right = _normalize_similarity_text(second)
    if not left or not right:
        return False
    shorter, longer = sorted((left, right), key=len)
    if len(shorter) >= 24 and longer.startswith(shorter):
        return True

    left_tokens = left.split()
    right_tokens = right.split()
    if not left_tokens or not right_tokens:
        return False
    overlap = len(set(left_tokens) & set(right_tokens))
    baseline = min(len(set(left_tokens)), len(set(right_tokens)))
    return baseline > 0 and overlap / baseline >= 0.8


def _normalize_similarity_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.lower()))


def _natural_join(items: Sequence[str]) -> str:
    clean_items = [item for item in items if item]
    if not clean_items:
        return ""
    if len(clean_items) == 1:
        return clean_items[0]
    if len(clean_items) == 2:
        return f"{clean_items[0]} and {clean_items[1]}"
    return f"{', '.join(clean_items[:-1])}, and {clean_items[-1]}"


def _extract_personal_fact_value(
    user_request: str,
    profile_context: str,
    note_context: str,
    history_context: str,
    last_observation: str | None,
) -> str | None:
    patterns, label = _personal_fact_patterns(user_request)
    if not patterns:
        return None

    evidence_chunks = [profile_context, note_context, history_context, last_observation or ""]
    for chunk in evidence_chunks:
        if not chunk.strip():
            continue
        for pattern in patterns:
            match = pattern.search(chunk)
            if match is None:
                continue
            value = _clean_fact_value(match.group(1))
            if value:
                return f"Your {label} appears to be {_display_personal_fact_value(label, value)}."
    return None


def _personal_fact_patterns(user_request: str) -> tuple[tuple[re.Pattern[str], ...], str]:
    lowered = user_request.lower()
    if "name" in lowered or "who am i" in lowered:
        return (NAME_VALUE_PATTERN,), "name"
    if "email" in lowered:
        return (EMAIL_VALUE_PATTERN,), "email"
    if "phone" in lowered:
        return (PHONE_VALUE_PATTERN,), "phone number"
    if "address" in lowered:
        return (ADDRESS_VALUE_PATTERN,), "address"
    if "pronoun" in lowered:
        return (PRONOUNS_VALUE_PATTERN,), "pronouns"
    if "timezone" in lowered:
        return (TIMEZONE_VALUE_PATTERN,), "timezone"
    return (), "details"


def _profile_memory_candidate(user_request: str) -> tuple[str, str, str] | None:
    stripped_request = user_request.strip()
    if not stripped_request or stripped_request.endswith("?"):
        return None

    patterns_with_labels = (
        (NAME_VALUE_PATTERN, "name"),
        (EMAIL_VALUE_PATTERN, "email"),
        (PHONE_VALUE_PATTERN, "phone number"),
        (ADDRESS_VALUE_PATTERN, "address"),
        (PRONOUNS_VALUE_PATTERN, "pronouns"),
        (TIMEZONE_VALUE_PATTERN, "timezone"),
    )
    for pattern, label in patterns_with_labels:
        match = pattern.search(stripped_request)
        if match is None:
            continue
        value = _clean_fact_value(match.group(1))
        if not value:
            continue
        display_value = _display_personal_fact_value(label, value)
        return (
            f"{label}: {display_value}",
            label,
            f"Okay. I'll remember that your {label} is {display_value}.",
        )

    favorite_match = FAVORITE_VALUE_PATTERN.search(stripped_request)
    if favorite_match is not None:
        topic = _clean_fact_value(favorite_match.group(1))
        value = _clean_fact_value(favorite_match.group(2))
        if topic and value:
            return (
                f"favorite {topic}: {value}",
                "preference",
                f"Okay. I'll remember that your favorite {topic} is {value}.",
            )

    preference_match = PREFERENCE_VALUE_PATTERN.search(stripped_request)
    if preference_match is not None:
        value = _clean_fact_value(preference_match.group(1))
        if value:
            return (
                f"preference: {value}",
                "preference",
                f"Okay. I'll remember that you prefer {value}.",
            )

    goal_match = GOAL_VALUE_PATTERN.search(stripped_request)
    if goal_match is not None:
        value = _clean_fact_value(goal_match.group(1))
        if value:
            return (
                f"goal: {value}",
                "goal",
                f"Okay. I'll remember that your goal is {value}.",
            )

    return None


def _clean_fact_value(value: str) -> str:
    cleaned = value.strip().strip("`\"' .,;:")
    cleaned = re.split(r"[\n\r]", cleaned, maxsplit=1)[0].strip()
    if not cleaned:
        return ""
    if cleaned.lower() in {"unknown", "n/a", "none"}:
        return ""
    return cleaned


def _display_personal_fact_value(label: str, value: str) -> str:
    if label != "name":
        return value
    if value != value.lower():
        return value
    return " ".join(part.capitalize() for part in value.split())


def _looks_like_personal_fact_request(user_request: str) -> bool:
    return PERSONAL_FACT_PATTERN.search(user_request) is not None


def _looks_like_profile_request(user_request: str) -> bool:
    return PROFILE_REQUEST_PATTERN.search(user_request) is not None or _looks_like_personal_fact_request(
        user_request
    )


def _is_summary_request(user_request: str) -> bool:
    return SUMMARY_HINT_PATTERN.search(user_request) is not None


def _allow_live_streaming(
    user_request: str,
    token_callback: TokenCallback | None,
    last_tool_name: str | None,
) -> bool:
    if token_callback is None:
        return False
    if last_tool_name is not None:
        return False
    if _looks_like_personal_fact_request(user_request):
        return False
    if _is_summary_request(user_request):
        return False
    if _should_prefetch_profile(user_request):
        return False
    if _should_prefetch_notes(user_request) or _should_prefetch_history(user_request):
        return False
    if _is_file_listing_request(user_request) or README_REQUEST_PATTERN.search(user_request):
        return False
    return True


def _is_repository_request(user_request: str) -> bool:
    lowered = user_request.lower()
    return any(token in lowered for token in ("repository", "repo", "project", "codebase"))


def _is_file_listing_request(user_request: str) -> bool:
    return FILE_LIST_REQUEST_PATTERN.search(user_request) is not None


def _is_direct_note_request(user_request: str) -> bool:
    lowered = user_request.lower()
    if "based on my notes" in lowered:
        return False
    return NOTE_LIST_REQUEST_PATTERN.search(user_request) is not None


def _is_direct_history_request(user_request: str) -> bool:
    return HISTORY_LIST_REQUEST_PATTERN.search(user_request) is not None


def _is_direct_profile_request(user_request: str) -> bool:
    return _looks_like_profile_request(user_request)


def _looks_like_unhelpful_answer(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped == "(empty response)":
        return True
    lowered = stripped.lower()
    if lowered.startswith(("[assistant]", "assistant:", "tool:", "final:", "observation:")):
        return True
    return any(
        fragment in lowered
        for fragment in (
            "(echo provider)",
            "i don't have access",
            "i do not have access",
            "i'm unable to directly",
            "i am unable to directly",
            "my capabilities are limited",
            "capabilities are limited",
            "i can't access",
            "i cannot access",
            "i can't provide",
            "i cannot provide",
            "i don't have any saved notes",
            "i do not have any saved notes",
            "i don't have any saved note",
            "i do not have any saved note",
        )
    )


def _looks_like_malformed_answer(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if "FINAL:" in stripped or "TOOL:" in stripped:
        return True
    if stripped[0] in {"`", "~"} and len(stripped) < 120:
        return True
    words = re.findall(r"[A-Za-z0-9]+", stripped)
    if len(words) <= 3 and stripped.endswith((".", "!", "?")):
        return True
    return False


def _looks_like_listing_echo(final_text: str, observation: str) -> bool:
    stripped = final_text.strip()
    if not stripped:
        return True
    observation_lines = {line.strip() for line in observation.splitlines() if line.strip()}
    return len(stripped) <= 80 and stripped in observation_lines


def _looks_like_file_dump(final_text: str, observation: str) -> bool:
    stripped = final_text.strip()
    if not stripped:
        return True
    if stripped.startswith("#"):
        return True
    normalized_final = " ".join(stripped.split())
    normalized_observation = " ".join(observation.strip().split())
    if len(normalized_final) < 20:
        return False
    return (
        normalized_observation.startswith(normalized_final)
        or normalized_final[:80] in normalized_observation[:240]
    )


def _can_use_observation_for_fallback(observation: str) -> bool:
    return not observation.lower().startswith(("refused:", "tool execution error:"))


def _should_replace_fallback(
    current_observation: str | None,
    new_observation: str,
) -> bool:
    if current_observation is None:
        return True
    if _observation_has_results(new_observation) and not _observation_has_results(current_observation):
        return True
    if _observation_has_results(current_observation) and not _observation_has_results(new_observation):
        return False
    return True


def _observation_has_results(observation: str) -> bool:
    lowered = observation.lower()
    return not lowered.startswith(
        (
            "no matching",
            "no saved notes",
            "no saved profile",
            "no session history",
            "i couldn't find",
            "unable to ",
            "missing required",
            "refused:",
            "tool execution error:",
        )
    )


def _direct_answer(
    *,
    user_request: str,
    session_id: str,
    history: Sequence[ConversationMessage],
) -> str | None:
    assistant_identity = _assistant_identity_answer(user_request)
    if assistant_identity is not None:
        return assistant_identity

    if CLI_ROUTING_PATTERN.search(user_request):
        return (
            "If the input starts with `!`, lilbot runs a local prefix command immediately. "
            "Plain `help`, `commands`, or `?` in the interactive REPL also stay local. "
            "Everything else is treated as a normal prompt and sent through the LLM agent."
        )

    session_answer = _session_id_answer(user_request, session_id)
    if session_answer is not None:
        return session_answer

    if _looks_like_profile_request(user_request) and not _looks_like_personal_fact_request(user_request):
        return None

    declaration_answer = _personal_fact_declaration_answer(user_request)
    if declaration_answer is not None:
        return declaration_answer

    remembered_fact = _recent_personal_fact_answer(user_request, history)
    if remembered_fact is not None:
        return remembered_fact

    if LAST_QUESTION_PATTERN.search(user_request):
        previous_question = _last_user_message(history)
        if previous_question:
            return f'You just asked: "{previous_question}"'
        return "You have not asked anything else in this session yet."

    return None


def _session_id_answer(user_request: str, session_id: str) -> str | None:
    lowered = user_request.lower()
    if SESSION_ID_PATTERN.search(user_request) and any(
        token in lowered for token in ("what", "which", "current", "show", "tell")
    ):
        return f"Your current session id is {session_id}."
    return None


def _assistant_identity_answer(user_request: str) -> str | None:
    if ASSISTANT_IDENTITY_PATTERN.search(user_request) is None:
        return None
    return "I'm lilbot, your local CLI assistant."


def _is_greeting_request(user_request: str) -> bool:
    return GREETING_PATTERN.fullmatch(user_request.strip()) is not None


def _looks_like_greeting_answer(text: str) -> bool:
    lowered = text.strip().lower()
    return any(token in lowered for token in ("hello", "hi", "hey", "greetings"))


def _last_user_message(history: Sequence[ConversationMessage]) -> str | None:
    for message in reversed(history):
        if message.role == "user" and message.content.strip():
            return message.content.strip()
    return None


def _prefetch_tool_requests(user_request: str, session_id: str) -> list[tuple[str, dict[str, Any]]]:
    requests: list[tuple[str, dict[str, Any]]] = []

    if README_REQUEST_PATTERN.search(user_request):
        requests.append(("read_file", {"path": "README.md", "max_chars": 4000}))
    elif _is_file_listing_request(user_request) or _is_repository_request(user_request):
        requests.append(("list_files", {"path": ".", "max_entries": 50}))

    if _should_prefetch_profile(user_request):
        profile_params: dict[str, Any] = {"limit": 8}
        profile_query = _profile_query_from_request(user_request)
        if profile_query:
            profile_params["query"] = profile_query
        requests.append(("search_profile", profile_params))
    elif _looks_like_personal_fact_request(user_request):
        personal_query = _personal_fact_query(user_request)
        if personal_query:
            requests.append(("search_profile", {"limit": 5, "query": personal_query}))

    if _should_prefetch_notes(user_request):
        note_params: dict[str, Any] = {"limit": 10}
        note_query = _note_query_from_request(user_request)
        if note_query:
            note_params["query"] = note_query
        requests.append(("search_notes", note_params))
    elif _looks_like_personal_fact_request(user_request):
        personal_query = _personal_fact_query(user_request)
        if personal_query:
            requests.append(("search_notes", {"limit": 5, "query": personal_query}))

    if _should_prefetch_history(user_request) and session_id.strip():
        history_params: dict[str, Any] = {"limit": 8, "session_id": session_id}
        history_query = _history_query_from_request(user_request)
        if history_query:
            history_params["query"] = history_query
        requests.append(("search_history", history_params))
    elif _looks_like_personal_fact_request(user_request) and session_id.strip():
        personal_query = _personal_fact_query(user_request)
        if personal_query:
            requests.append(
                ("search_history", {"limit": 6, "session_id": session_id, "query": personal_query})
            )

    return requests


def _should_prefetch_profile(user_request: str) -> bool:
    return _looks_like_profile_request(user_request)


def _should_prefetch_notes(user_request: str) -> bool:
    return NOTE_REQUEST_PATTERN.search(user_request) is not None


def _should_prefetch_history(user_request: str) -> bool:
    return HISTORY_REQUEST_PATTERN.search(user_request) is not None


def _note_query_from_request(user_request: str) -> str | None:
    return _query_from_request(user_request, NOTE_QUERY_STOPWORDS)


def _history_query_from_request(user_request: str) -> str | None:
    return _query_from_request(user_request, HISTORY_QUERY_STOPWORDS)


def _profile_query_from_request(user_request: str) -> str | None:
    lowered = user_request.lower()
    if PROFILE_REQUEST_PATTERN.search(user_request) is not None and "about me" in lowered:
        return None
    if "name" in lowered or "who am i" in lowered:
        return "name"
    if "email" in lowered:
        return "email"
    if "phone" in lowered:
        return "phone number"
    if "address" in lowered:
        return "address"
    if "pronoun" in lowered:
        return "pronouns"
    if "timezone" in lowered:
        return "timezone"
    if "goal" in lowered:
        return "goal"
    if any(token in lowered for token in ("prefer", "favorite", "favourite", "usually use", "like to use")):
        return "preference"
    return _query_from_request(user_request, PROFILE_QUERY_STOPWORDS)


def _personal_fact_query(user_request: str) -> str | None:
    lowered = user_request.lower()
    if "name" in lowered or "who am i" in lowered:
        return "name"
    if "email" in lowered:
        return "email"
    if "phone" in lowered:
        return "phone number"
    if "address" in lowered:
        return "address"
    if "pronoun" in lowered:
        return "pronouns"
    if "timezone" in lowered:
        return "timezone"
    return None


def _query_from_request(user_request: str, stopwords: frozenset[str]) -> str | None:
    lowered = user_request.lower()
    about_match = re.search(r"\babout\s+(.+)", lowered)
    if about_match is not None:
        about_text = _clean_query_text(about_match.group(1), stopwords)
        if about_text:
            return about_text

    keywords = [token for token in QUERY_TOKEN_PATTERN.findall(lowered) if token not in stopwords]
    if not keywords:
        return None
    return " ".join(keywords[:4])


def _clean_query_text(text: str, stopwords: frozenset[str]) -> str:
    keywords = [token for token in QUERY_TOKEN_PATTERN.findall(text.lower()) if token not in stopwords]
    if not keywords:
        return ""
    return " ".join(keywords[:4])
