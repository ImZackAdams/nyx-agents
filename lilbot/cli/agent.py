from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import json
import logging
import re
from typing import Any, Protocol

from lilbot.memory.memory import search_notes, search_session_history


LOGGER = logging.getLogger("lilbot.agent")
DEFAULT_AGENT_MAX_STEPS = 4
DEFAULT_HISTORY_MESSAGES = 8
DEFAULT_RELEVANT_NOTE_LIMIT = 3
DEFAULT_RELEVANT_HISTORY_LIMIT = 4
PROTOCOL_LINE_PATTERN = re.compile(r"(?m)^(FINAL:|TOOL:)\s*(.*)$", re.DOTALL)
CODE_FENCE_PATTERN = re.compile(r"^```(?:json|text)?\s*(.*?)```$", re.DOTALL)
ROLE_LABEL_PATTERN = re.compile(r"^\s*(?:\[[^\]]+\]|(?:assistant|user|system|observation)\s*:)\s*", re.IGNORECASE)
PERSONAL_FACT_PATTERN = re.compile(
    r"\b(my name|who am i|what'?s my name|what is my name|my email|my phone|my address)\b",
    re.IGNORECASE,
)
SUMMARY_HINT_PATTERN = re.compile(
    r"\b(summarize|summary|overview|describe|explain|what does .* do)\b",
    re.IGNORECASE,
)
TIMESTAMP_SUFFIX_PATTERN = re.compile(r"\s+\(\d{4}-\d{2}-\d{2}T[^)]*\)\s*$")


class GeneratesText(Protocol):
    def generate(self, prompt: str) -> str:
        ...


@dataclass(frozen=True)
class ConversationMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ParsedResponse:
    kind: str
    raw: str
    tool_name: str | None = None
    params: dict[str, Any] | None = None
    error: str | None = None


def run_agent(
    llm: GeneratesText,
    *,
    user_request: str,
    system_prompt: str,
    session_id: str,
    history: list[ConversationMessage],
    history_limit: int,
    max_steps: int,
    tool_schemas: Sequence[Mapping[str, Any]],
    tool_executor: Callable[[str, Mapping[str, Any] | None], str],
    status_callback: Callable[[str], None] | None = None,
) -> str:
    trimmed_history = _trim_history(history, history_limit)
    working_messages = list(trimmed_history)
    working_messages.append(ConversationMessage("user", user_request))
    note_context = _relevant_note_context(user_request)
    history_context = _relevant_history_context(session_id, user_request)
    last_tool_name: str | None = None
    last_observation: str | None = None
    fallback_tool_name: str | None = None
    fallback_observation: str | None = None
    seen_tool_calls: set[tuple[str, str]] = set()

    for _ in range(max(1, max_steps)):
        prompt = build_agent_prompt(
            system_prompt=system_prompt,
            messages=working_messages,
            note_context=note_context,
            history_context=history_context,
            tool_schemas=tool_schemas,
        )
        raw_response = llm.generate(prompt).strip()
        parsed = parse_model_response(raw_response)

        if parsed.kind == "final":
            final_text = _final_text(parsed.raw)
            final_text = _coerce_final_answer(
                user_request=user_request,
                final_text=final_text,
                note_context=note_context,
                history_context=history_context,
                last_tool_name=fallback_tool_name or last_tool_name,
                last_observation=fallback_observation or last_observation,
            )
            _append_exchange(history, user_request, final_text, history_limit)
            return final_text

        if parsed.kind == "tool":
            assert parsed.tool_name is not None
            params = parsed.params or {}
            tool_signature = _tool_signature(parsed.tool_name, params)
            if status_callback is not None:
                status_callback(
                    f"tool {parsed.tool_name} {json.dumps(params, ensure_ascii=True, sort_keys=True)}"
                )
            if tool_signature in seen_tool_calls:
                observation = (
                    f"Refused: repeated tool call for {parsed.tool_name}. "
                    "Use the information already gathered and answer with FINAL."
                )
            elif parsed.tool_name == "save_note" and not _save_note_allowed(user_request):
                observation = "Refused: save_note requires an explicit request to remember or save something."
            else:
                seen_tool_calls.add(tool_signature)
                try:
                    observation = tool_executor(parsed.tool_name, params)
                except Exception as exc:
                    observation = f"Tool execution error: {exc}"
            last_tool_name = parsed.tool_name
            last_observation = observation
            if _can_use_observation_for_fallback(observation) and _should_replace_fallback(
                fallback_observation, observation
            ):
                fallback_tool_name = parsed.tool_name
                fallback_observation = observation
            working_messages.append(ConversationMessage("assistant", parsed.raw))
            working_messages.append(
                ConversationMessage(
                    "tool",
                    f"{parsed.tool_name}: {observation}\nUse this observation to answer the user. "
                    "Only call another tool if the observation is clearly insufficient.",
                )
            )
            continue

        LOGGER.debug("Invalid model response for request %r: %s", user_request, parsed.error or parsed.raw)
        working_messages.append(ConversationMessage("assistant", parsed.raw))
        working_messages.append(
            ConversationMessage(
                "tool",
                parsed.error or "Invalid model response. Use FINAL: or TOOL: <name> <json>.",
            )
        )

    fallback = _fallback_answer(
        user_request=user_request,
        note_context=note_context,
        history_context=history_context,
        last_tool_name=fallback_tool_name or last_tool_name,
        last_observation=fallback_observation or last_observation,
        default="I reached the tool-use limit before finishing the request.",
    )
    _append_exchange(history, user_request, fallback, history_limit)
    return fallback


def build_agent_prompt(
    *,
    system_prompt: str,
    messages: Sequence[ConversationMessage],
    note_context: str,
    history_context: str,
    tool_schemas: Sequence[Mapping[str, Any]],
) -> str:
    sections = [
        _base_agent_instructions(tool_schemas),
    ]
    if system_prompt.strip():
        sections.append(f"Additional system guidance:\n{system_prompt.strip()}")
    if note_context:
        sections.append(f"Potentially relevant notes:\n{note_context}")
    if history_context:
        sections.append(f"Potentially relevant past conversation:\n{history_context}")
    sections.append("Conversation:\n" + _format_messages(messages))
    sections.append("Assistant:")
    return "\n\n".join(sections)


def parse_model_response(raw_response: str) -> ParsedResponse:
    normalized = _normalize_model_response(raw_response)
    if normalized.startswith("FINAL:"):
        return ParsedResponse(kind="final", raw=normalized)

    match = PROTOCOL_LINE_PATTERN.match(normalized)
    if match is None and normalized:
        return ParsedResponse(kind="final", raw=f"FINAL: {normalized}")
    if match is None:
        return ParsedResponse(
            kind="error",
            raw=normalized,
            error="Invalid response format. Reply with FINAL: <answer> or TOOL: <name> <json>.",
        )

    prefix, remainder = match.groups()
    if prefix == "FINAL:":
        return ParsedResponse(kind="final", raw=f"FINAL: {remainder.strip()}")

    tool_name, arg_text = _split_tool_payload(remainder)
    if not tool_name:
        return ParsedResponse(
            kind="error",
            raw=normalized,
            error="Tool response must include a tool name followed by a JSON object.",
        )
    arg_text = arg_text or "{}"
    try:
        params = json.loads(arg_text)
    except json.JSONDecodeError as exc:
        return ParsedResponse(
            kind="error",
            raw=normalized,
            error=f"Tool arguments must be valid JSON: {exc}",
        )
    if not isinstance(params, dict):
        return ParsedResponse(
            kind="error",
            raw=normalized,
            error="Tool arguments must decode to a JSON object.",
        )
    return ParsedResponse(kind="tool", raw=f"TOOL: {tool_name} {arg_text}", tool_name=tool_name, params=params)


def _base_agent_instructions(tool_schemas: Sequence[Mapping[str, Any]]) -> str:
    tool_lines = []
    for tool in tool_schemas:
        name = str(tool["name"])
        description = str(tool["description"])
        parameters = tool.get("parameters") or {}
        parameter_text = (
            "; ".join(f"{key}={value}" for key, value in parameters.items())
            if isinstance(parameters, Mapping) and parameters
            else "no parameters"
        )
        example = json.dumps(tool.get("example", {}), ensure_ascii=True, sort_keys=True)
        tool_lines.append(f"- {name}: {description} Params: {parameter_text}. Example: {example}")

    return "\n".join(
        [
            "You are lilbot, a local CLI agent.",
            "You must respond with exactly one of these formats:",
            "FINAL: <answer>",
            "TOOL: <tool_name> <json object>",
            "Use at most one tool per message.",
            "After you receive an Observation, either call another tool or answer with FINAL.",
            "Prefer tools over guessing when the answer depends on local files, notes, or system state.",
            "Potentially relevant notes or past conversation may already be provided above. Use them directly if they are sufficient.",
            "If the request may relate to saved notes, prefer search_notes before answering.",
            "If the request asks about earlier conversation, prefer search_history before answering.",
            "If you are asked to summarize a file, summarize it instead of pasting raw file contents.",
            "Never prefix your answer with [assistant] or Assistant:.",
            "Only use save_note when the user explicitly asks you to remember, store, or save information.",
            "For personal facts about the user, only answer when supported by notes, history, or tool observations. Otherwise say you do not know.",
            "Never invent tool results.",
            "Available tools:",
            *tool_lines,
        ]
    )


def _format_messages(messages: Sequence[ConversationMessage]) -> str:
    lines: list[str] = []
    for message in messages:
        if message.role == "user":
            lines.append(f"User: {message.content}")
        elif message.role == "assistant":
            lines.append(f"Assistant: {message.content}")
        elif message.role == "tool":
            lines.append(f"Observation: {message.content}")
        else:
            lines.append(f"{message.role.title()}: {message.content}")
    return "\n".join(lines)


def _relevant_note_context(user_request: str, limit: int = DEFAULT_RELEVANT_NOTE_LIMIT) -> str:
    notes = search_notes(user_request, limit=limit)
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
    messages = search_session_history(session_id, user_request, limit=limit)
    if not messages:
        return ""
    return "\n".join(
        f"- [{message['role']}] {message['content']} ({message['created_at']})"
        for message in messages
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


def _normalize_model_response(raw_response: str) -> str:
    text = raw_response.strip()
    if not text:
        return text

    fence_match = CODE_FENCE_PATTERN.match(text)
    if fence_match is not None:
        text = fence_match.group(1).strip()

    text = _strip_role_labels(text)
    text = _unwrap_nested_protocol(text)

    protocol_match = PROTOCOL_LINE_PATTERN.search(text)
    if protocol_match is not None:
        prefix, remainder = protocol_match.groups()
        return f"{prefix} {remainder.strip()}".strip()
    return _strip_role_labels(text)


def _split_tool_payload(payload: str) -> tuple[str, str]:
    stripped = payload.strip()
    if not stripped:
        return "", "{}"
    parts = stripped.split(None, 1)
    if len(parts) == 1:
        return parts[0], "{}"
    return parts[0], parts[1].strip()


def _final_text(response: str) -> str:
    if response.startswith("FINAL:"):
        return response.partition(":")[2].strip()
    return response.strip()


def _tool_signature(tool_name: str, params: Mapping[str, Any]) -> tuple[str, str]:
    return tool_name, json.dumps(dict(params), ensure_ascii=True, sort_keys=True)


def _coerce_final_answer(
    *,
    user_request: str,
    final_text: str,
    note_context: str,
    history_context: str,
    last_tool_name: str | None,
    last_observation: str | None,
) -> str:
    if _looks_like_personal_fact_request(user_request) and not _has_retrieval_evidence(
        note_context, history_context, last_observation
    ):
        return "I don't know based on your saved notes or session history."

    if last_tool_name and last_observation:
        if _looks_like_unhelpful_answer(final_text):
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


def _fallback_answer(
    *,
    user_request: str,
    note_context: str,
    history_context: str,
    last_tool_name: str | None,
    last_observation: str | None,
    default: str,
) -> str:
    if last_tool_name and last_observation:
        fallback = _fallback_from_observation(user_request, last_tool_name, last_observation)
        if fallback:
            return fallback

    if _looks_like_personal_fact_request(user_request) and not _has_retrieval_evidence(
        note_context, history_context, last_observation
    ):
        return "I don't know based on your saved notes or session history."

    return default


def _fallback_from_observation(
    user_request: str,
    tool_name: str,
    observation: str,
) -> str | None:
    if observation.startswith(("Refused:", "Tool execution error:", "Unable to ", "Missing required")):
        return observation

    if tool_name in {"search_notes", "search_history"}:
        return _format_memory_observation(user_request, tool_name, observation)

    if tool_name == "read_file":
        if _is_summary_request(user_request):
            return _summarize_text_observation(observation)
        return observation

    if tool_name == "list_files":
        if _is_summary_request(user_request) or _is_repository_request(user_request):
            return _summarize_listing_observation(observation)
        return observation

    if tool_name == "system_info":
        return observation

    return None


def _format_memory_observation(user_request: str, tool_name: str, observation: str) -> str:
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
        if "based on my notes" in user_request.lower():
            if len(items) == 1:
                return items[0]
            return "Based on your notes:\n" + "\n".join(f"- {item}" for item in items)
        return "Matching notes:\n" + "\n".join(f"- {item}" for item in items)

    return "Relevant session history:\n" + "\n".join(f"- {item}" for item in items)


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
    entries = [line.strip() for line in observation.splitlines() if line.strip() and not line.startswith("...")]
    if not entries:
        return "(empty directory)"

    directories = [entry.rstrip("/") for entry in entries if entry.endswith("/")]
    files = [entry for entry in entries if not entry.endswith("/")]
    key_files = [
        name for name in ("README.md", "pyproject.toml", "requirements.txt", "GETTING_STARTED.md", "setup.sh")
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


def _natural_join(items: Sequence[str]) -> str:
    clean_items = [item for item in items if item]
    if not clean_items:
        return ""
    if len(clean_items) == 1:
        return clean_items[0]
    if len(clean_items) == 2:
        return f"{clean_items[0]} and {clean_items[1]}"
    return f"{', '.join(clean_items[:-1])}, and {clean_items[-1]}"


def _strip_role_labels(text: str) -> str:
    normalized = text.strip()
    while normalized:
        stripped = ROLE_LABEL_PATTERN.sub("", normalized, count=1).strip()
        if stripped == normalized:
            return normalized
        normalized = stripped
    return normalized


def _unwrap_nested_protocol(text: str) -> str:
    normalized = text.strip()
    for _ in range(3):
        if normalized.startswith(("FINAL:", "TOOL:")):
            _, _, remainder = normalized.partition(":")
            inner = _strip_role_labels(remainder)
            if inner.startswith(("FINAL:", "TOOL:")):
                normalized = inner
                continue
        break
    return normalized


def _has_retrieval_evidence(
    note_context: str,
    history_context: str,
    last_observation: str | None,
) -> bool:
    if note_context.strip() or history_context.strip():
        return True
    if last_observation and not last_observation.lower().startswith(
        ("no ", "i couldn't find", "refused:", "unable to ", "missing required", "tool execution error:")
    ):
        return True
    return False


def _looks_like_personal_fact_request(user_request: str) -> bool:
    return PERSONAL_FACT_PATTERN.search(user_request) is not None


def _is_summary_request(user_request: str) -> bool:
    return SUMMARY_HINT_PATTERN.search(user_request) is not None


def _is_repository_request(user_request: str) -> bool:
    lowered = user_request.lower()
    return any(token in lowered for token in ("repository", "repo", "project", "codebase"))


def _looks_like_unhelpful_answer(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped == "(empty response)":
        return True
    lowered = stripped.lower()
    return lowered.startswith(("[assistant]", "assistant:", "tool:", "final:", "observation:"))


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
            "no session history",
            "i couldn't find",
            "unable to ",
            "missing required",
            "refused:",
            "tool execution error:",
        )
    )
