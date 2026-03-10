from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import json
import re
from typing import Any, Protocol

from lilbot.memory.memory import search_notes, search_session_history


DEFAULT_AGENT_MAX_STEPS = 4
DEFAULT_HISTORY_MESSAGES = 8
DEFAULT_RELEVANT_NOTE_LIMIT = 3
DEFAULT_RELEVANT_HISTORY_LIMIT = 4
PROTOCOL_LINE_PATTERN = re.compile(r"(?m)^(FINAL:|TOOL:)\s*(.*)$", re.DOTALL)
CODE_FENCE_PATTERN = re.compile(r"^```(?:json|text)?\s*(.*?)```$", re.DOTALL)


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
            _append_exchange(history, user_request, final_text, history_limit)
            return final_text

        if parsed.kind == "tool":
            assert parsed.tool_name is not None
            params = parsed.params or {}
            if status_callback is not None:
                status_callback(
                    f"tool {parsed.tool_name} {json.dumps(params, ensure_ascii=True, sort_keys=True)}"
                )
            if parsed.tool_name == "save_note" and not _save_note_allowed(user_request):
                observation = "Refused: save_note requires an explicit request to remember or save something."
            else:
                try:
                    observation = tool_executor(parsed.tool_name, params)
                except Exception as exc:
                    observation = f"Tool execution error: {exc}"
            working_messages.append(ConversationMessage("assistant", parsed.raw))
            working_messages.append(
                ConversationMessage("tool", f"{parsed.tool_name}: {observation}")
            )
            continue

        working_messages.append(ConversationMessage("assistant", parsed.raw))
        working_messages.append(
            ConversationMessage(
                "tool",
                parsed.error or "Invalid model response. Use FINAL: or TOOL: <name> <json>.",
            )
        )

    fallback = "I reached the tool-use limit before finishing the request."
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
            "If the request may relate to saved notes, prefer search_notes before answering.",
            "If the request asks about earlier conversation, prefer search_history before answering.",
            "Only use save_note when the user explicitly asks you to remember, store, or save information.",
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

    protocol_match = PROTOCOL_LINE_PATTERN.search(text)
    if protocol_match is not None:
        prefix, remainder = protocol_match.groups()
        return f"{prefix} {remainder.strip()}".strip()
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
    if response.startswith("FINAL:"):
        return response.partition(":")[2].strip()
    return response.strip()
