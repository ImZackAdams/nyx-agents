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
    r"\b(?:what|which|list|show|display)\b.*\b(?:files?|directories|folders?)\b|\b(?:files?|directories|folders?)\b.*\b(?:are in|in this|under)\b",
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
SPECIAL_TOKEN_PATTERN = re.compile(r"<\|(?:assistant|user|system)\|>")
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
NOTE_QUERY_STOPWORDS = frozenset(
    {
        "about",
        "all",
        "any",
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
HISTORY_QUERY_STOPWORDS = frozenset(
    {
        "about",
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
TokenCallback = Callable[[str], None]


class GeneratesText(Protocol):
    def generate(self, prompt: str, *, on_token: TokenCallback | None = None) -> str:
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


@dataclass
class StreamState:
    callback: TokenCallback
    mode: str | None = None
    raw_buffer: str = ""
    emitted_text: str = ""

    def on_token(self, token: str) -> None:
        if not token:
            return
        self.raw_buffer += token
        self._flush(allow_plain_text=False)

    def finalize(self, raw_response: str) -> None:
        if raw_response and not self.raw_buffer:
            self.raw_buffer = raw_response
        self._flush(allow_plain_text=True)

    @property
    def streamed(self) -> bool:
        return bool(self.emitted_text)

    def _flush(self, *, allow_plain_text: bool) -> None:
        normalized = _normalize_stream_candidate(self.raw_buffer)
        if self.mode is None:
            if normalized.startswith("TOOL:"):
                self.mode = "tool"
            elif normalized.startswith("FINAL:"):
                self.mode = "final"
            elif allow_plain_text and normalized:
                self.mode = "final"
            else:
                return

        if self.mode != "final":
            return

        display_text = _final_text(normalized)
        if not display_text.startswith(self.emitted_text):
            return
        delta = display_text[len(self.emitted_text):]
        if delta:
            self.callback(delta)
            self.emitted_text = display_text


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
    token_callback: TokenCallback | None = None,
) -> str:
    trimmed_history = _trim_history(history, history_limit)
    direct_answer, prefetch_state = _prepare_agent_request(
        user_request=user_request,
        session_id=session_id,
        history=history,
        history_limit=history_limit,
        tool_executor=tool_executor,
        status_callback=status_callback,
        persist_direct_answer=True,
    )
    if direct_answer is not None:
        return direct_answer

    working_messages = prefetch_state.working_messages
    note_context = prefetch_state.note_context
    history_context = prefetch_state.history_context
    last_tool_name = prefetch_state.last_tool_name
    last_observation = prefetch_state.last_observation
    fallback_tool_name = prefetch_state.fallback_tool_name
    fallback_observation = prefetch_state.fallback_observation
    seen_tool_calls = prefetch_state.seen_tool_calls

    direct_tool_answer = _direct_tool_answer(
        user_request=user_request,
        last_tool_name=fallback_tool_name or last_tool_name,
        last_observation=fallback_observation or last_observation,
    )
    if direct_tool_answer is not None:
        _append_exchange(history, user_request, direct_tool_answer, history_limit)
        return direct_tool_answer

    for _ in range(max(1, max_steps)):
        prompt = build_agent_prompt(
            system_prompt=system_prompt,
            messages=working_messages,
            note_context=note_context,
            history_context=history_context,
            tool_schemas=tool_schemas,
        )
        stream_state: StreamState | None = None
        if _allow_live_streaming(user_request, token_callback, last_tool_name):
            stream_state = StreamState(token_callback)

        raw_response = llm.generate(
            prompt,
            on_token=stream_state.on_token if stream_state is not None else None,
        ).strip()
        if stream_state is not None:
            stream_state.finalize(raw_response)
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
        if fallback_observation and not parsed.raw.strip():
            break
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


@dataclass
class PrefetchState:
    working_messages: list[ConversationMessage]
    note_context: str
    history_context: str
    last_tool_name: str | None
    last_observation: str | None
    fallback_tool_name: str | None
    fallback_observation: str | None
    seen_tool_calls: set[tuple[str, str]]


def maybe_answer_without_llm(
    *,
    user_request: str,
    session_id: str,
    history: list[ConversationMessage],
    history_limit: int,
    tool_executor: Callable[[str, Mapping[str, Any] | None], str],
    status_callback: Callable[[str], None] | None = None,
) -> str | None:
    direct_answer, _ = _prepare_agent_request(
        user_request=user_request,
        session_id=session_id,
        history=history,
        history_limit=history_limit,
        tool_executor=tool_executor,
        status_callback=status_callback,
        persist_direct_answer=True,
    )
    return direct_answer


def _prepare_agent_request(
    *,
    user_request: str,
    session_id: str,
    history: list[ConversationMessage],
    history_limit: int,
    tool_executor: Callable[[str, Mapping[str, Any] | None], str],
    status_callback: Callable[[str], None] | None,
    persist_direct_answer: bool,
) -> tuple[str | None, PrefetchState]:
    trimmed_history = _trim_history(history, history_limit)
    direct_answer = _direct_answer(
        user_request=user_request,
        session_id=session_id,
        history=trimmed_history,
    )
    if direct_answer is not None:
        if persist_direct_answer:
            _append_exchange(history, user_request, direct_answer, history_limit)
        return direct_answer, PrefetchState(
            working_messages=list(trimmed_history),
            note_context="",
            history_context="",
            last_tool_name=None,
            last_observation=None,
            fallback_tool_name=None,
            fallback_observation=None,
            seen_tool_calls=set(),
        )

    working_messages = list(trimmed_history)
    working_messages.append(ConversationMessage("user", user_request))
    note_context = _relevant_note_context(user_request)
    history_context = _relevant_history_context(session_id, user_request)
    last_tool_name: str | None = None
    last_observation: str | None = None
    fallback_tool_name: str | None = None
    fallback_observation: str | None = None
    seen_tool_calls: set[tuple[str, str]] = set()

    for tool_name, params in _prefetch_tool_requests(user_request, session_id):
        tool_signature = _tool_signature(tool_name, params)
        if tool_signature in seen_tool_calls:
            continue
        if status_callback is not None:
            status_callback(
                f"tool {tool_name} {json.dumps(params, ensure_ascii=True, sort_keys=True)}"
            )
        try:
            observation = tool_executor(tool_name, params)
        except Exception as exc:
            observation = f"Tool execution error: {exc}"
        seen_tool_calls.add(tool_signature)
        last_tool_name = tool_name
        last_observation = observation
        if _can_use_observation_for_fallback(observation) and _should_replace_fallback(
            fallback_observation, observation
        ):
            fallback_tool_name = tool_name
            fallback_observation = observation
        working_messages.append(
            ConversationMessage(
                "tool",
                f"{tool_name}: {observation}\nUse this observation to answer the user. "
                "Only call another tool if the observation is clearly insufficient.",
            )
        )

    if _looks_like_personal_fact_request(user_request):
        direct_answer = _resolve_personal_fact_answer(
            user_request=user_request,
            note_context=note_context,
            history_context=history_context,
            last_observation=fallback_observation or last_observation,
        )
    else:
        direct_answer = _direct_tool_answer(
            user_request=user_request,
            last_tool_name=fallback_tool_name or last_tool_name,
            last_observation=fallback_observation or last_observation,
        )

    if direct_answer is not None and persist_direct_answer:
        _append_exchange(history, user_request, direct_answer, history_limit)

    return direct_answer, PrefetchState(
        working_messages=working_messages,
        note_context=note_context,
        history_context=history_context,
        last_tool_name=last_tool_name,
        last_observation=last_observation,
        fallback_tool_name=fallback_tool_name,
        fallback_observation=fallback_observation,
        seen_tool_calls=seen_tool_calls,
    )


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

    text = _strip_special_tokens(text)
    text = _strip_role_labels(text)
    text = _unwrap_nested_protocol(text)

    protocol_match = PROTOCOL_LINE_PATTERN.search(text)
    if protocol_match is not None:
        prefix, remainder = protocol_match.groups()
        return f"{prefix} {remainder.strip()}".strip()
    return _strip_role_labels(text)


def _normalize_stream_candidate(raw_response: str) -> str:
    text = raw_response.lstrip()
    if not text:
        return ""
    text = _strip_special_tokens(text)
    text = _strip_role_labels(text)
    text = _unwrap_nested_protocol(text)
    return text


def _split_tool_payload(payload: str) -> tuple[str, str]:
    stripped = payload.strip()
    if not stripped:
        return "", "{}"
    parts = stripped.split(None, 1)
    if len(parts) == 1:
        return parts[0], "{}"
    return parts[0], parts[1].strip()


def _final_text(response: str) -> str:
    text = response.partition(":")[2] if response.startswith("FINAL:") else response
    text = _strip_special_tokens(text)
    text = _strip_role_labels(text)
    return text.strip()


def _tool_signature(tool_name: str, params: Mapping[str, Any]) -> tuple[str, str]:
    return tool_name, json.dumps(dict(params), ensure_ascii=True, sort_keys=True)


def _sanitize_answer_text(text: str) -> str:
    normalized = _strip_special_tokens(text).strip()
    if "\nFINAL:" in normalized or "\nTOOL:" in normalized:
        protocol_positions = [
            match.start()
            for match in re.finditer(r"(?m)^(?:FINAL:|TOOL:)\s*", normalized)
        ]
        if protocol_positions:
            normalized = normalized[protocol_positions[-1]:].strip()
            if normalized.startswith("FINAL:"):
                normalized = normalized.partition(":")[2].strip()
    normalized = _strip_role_labels(normalized).strip()
    return _collapse_repeated_paragraphs(normalized)


def _coerce_final_answer(
    *,
    user_request: str,
    final_text: str,
    note_context: str,
    history_context: str,
    last_tool_name: str | None,
    last_observation: str | None,
) -> str:
    final_text = _sanitize_answer_text(final_text)

    if _looks_like_personal_fact_request(user_request):
        return _resolve_personal_fact_answer(
            user_request=user_request,
            note_context=note_context,
            history_context=history_context,
            last_observation=last_observation,
        )

    if last_tool_name == "list_files" and _is_file_listing_request(user_request) and last_observation:
        fallback = _fallback_from_observation(user_request, last_tool_name, last_observation)
        if fallback:
            return fallback

    if last_tool_name and last_observation:
        if last_tool_name in {"search_notes", "search_history"} and not _observation_has_results(last_observation):
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
    note_context: str,
    history_context: str,
    last_observation: str | None,
) -> str:
    fact_value = _extract_personal_fact_value(user_request, note_context, history_context, last_observation)
    if fact_value:
        return fact_value
    return "I don't know based on your saved notes or session history."


def _fallback_answer(
    *,
    user_request: str,
    note_context: str,
    history_context: str,
    last_tool_name: str | None,
    last_observation: str | None,
    default: str,
) -> str:
    if _looks_like_personal_fact_request(user_request):
        return _resolve_personal_fact_answer(
            user_request=user_request,
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

    if last_tool_name == "list_files" and _is_file_listing_request(user_request):
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


def _collapse_repeated_paragraphs(text: str) -> str:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
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


def _strip_role_labels(text: str) -> str:
    normalized = text.strip()
    while normalized:
        stripped = ROLE_LABEL_PATTERN.sub("", normalized, count=1).strip()
        if stripped == normalized:
            return normalized
        normalized = stripped
    return normalized


def _strip_special_tokens(text: str) -> str:
    return SPECIAL_TOKEN_PATTERN.sub("", text).strip()


def _unwrap_nested_protocol(text: str) -> str:
    normalized = _strip_special_tokens(text)
    for _ in range(3):
        if normalized.startswith(("FINAL:", "TOOL:")):
            _, _, remainder = normalized.partition(":")
            inner = _strip_special_tokens(_strip_role_labels(remainder))
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


def _extract_personal_fact_value(
    user_request: str,
    note_context: str,
    history_context: str,
    last_observation: str | None,
) -> str | None:
    patterns, label = _personal_fact_patterns(user_request)
    if not patterns:
        return None

    evidence_chunks = [note_context, history_context, last_observation or ""]
    for chunk in evidence_chunks:
        if not chunk.strip():
            continue
        for pattern in patterns:
            match = pattern.search(chunk)
            if match is None:
                continue
            value = _clean_fact_value(match.group(1))
            if value:
                return f"Your {label} appears to be {value}."
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
    return (), "details"


def _clean_fact_value(value: str) -> str:
    cleaned = value.strip().strip("`\"' .,;:")
    cleaned = re.split(r"[\n\r]", cleaned, maxsplit=1)[0].strip()
    if not cleaned:
        return ""
    if cleaned.lower() in {"unknown", "n/a", "none"}:
        return ""
    return cleaned


def _looks_like_personal_fact_request(user_request: str) -> bool:
    return PERSONAL_FACT_PATTERN.search(user_request) is not None


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
    if CLI_ROUTING_PATTERN.search(user_request):
        return (
            "If the input starts with `!`, lilbot runs a local prefix command immediately. "
            "Plain `help`, `commands`, or `?` in the interactive REPL also stay local. "
            "Everything else is treated as a normal prompt and sent through the LLM agent."
        )

    session_answer = _session_id_answer(user_request, session_id)
    if session_answer is not None:
        return session_answer

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
            requests.append(("search_history", {"limit": 6, "session_id": session_id, "query": personal_query}))

    return requests


def _should_prefetch_notes(user_request: str) -> bool:
    return NOTE_REQUEST_PATTERN.search(user_request) is not None


def _should_prefetch_history(user_request: str) -> bool:
    return HISTORY_REQUEST_PATTERN.search(user_request) is not None


def _note_query_from_request(user_request: str) -> str | None:
    return _query_from_request(user_request, NOTE_QUERY_STOPWORDS)


def _history_query_from_request(user_request: str) -> str | None:
    return _query_from_request(user_request, HISTORY_QUERY_STOPWORDS)


def _personal_fact_query(user_request: str) -> str | None:
    lowered = user_request.lower()
    if "name" in lowered or "who am i" in lowered:
        return "name"
    if "email" in lowered:
        return "email"
    if "phone" in lowered:
        return "phone"
    if "address" in lowered:
        return "address"
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
