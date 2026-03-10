from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import json
import re
from typing import Any, Protocol

from lilbot.memory.memory import search_notes


DEFAULT_AGENT_MAX_STEPS = 4
DEFAULT_HISTORY_MESSAGES = 8
DEFAULT_RELEVANT_NOTE_LIMIT = 3
TOOL_CALL_PATTERN = re.compile(r"^TOOL:\s*([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$", re.DOTALL)
TOOL_EXAMPLES = {
    "list_files": '{"path": "."}',
    "read_file": '{"path": "README.md"}',
    "system_info": "{}",
    "save_note": '{"text": "remember this"}',
    "search_notes": '{"query": "groceries", "limit": 5}',
}


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

    for _ in range(max(1, max_steps)):
        prompt = build_agent_prompt(
            system_prompt=system_prompt,
            messages=working_messages,
            note_context=note_context,
            tool_schemas=tool_schemas,
        )
        raw_response = llm.generate(prompt).strip()
        parsed = parse_model_response(raw_response)

        if parsed.kind == "final":
            _append_exchange(history, user_request, parsed.raw, history_limit)
            return parsed.raw

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

    fallback = "FINAL: I reached the tool-use limit before finishing the request."
    _append_exchange(history, user_request, fallback, history_limit)
    return fallback


def build_agent_prompt(
    *,
    system_prompt: str,
    messages: Sequence[ConversationMessage],
    note_context: str,
    tool_schemas: Sequence[Mapping[str, Any]],
) -> str:
    sections = [
        _base_agent_instructions(tool_schemas),
    ]
    if system_prompt.strip():
        sections.append(f"Additional system guidance:\n{system_prompt.strip()}")
    if note_context:
        sections.append(f"Potentially relevant notes:\n{note_context}")
    sections.append("Conversation:\n" + _format_messages(messages))
    sections.append("Assistant:")
    return "\n\n".join(sections)


def parse_model_response(raw_response: str) -> ParsedResponse:
    if raw_response.startswith("FINAL:"):
        return ParsedResponse(kind="final", raw=raw_response)

    match = TOOL_CALL_PATTERN.match(raw_response)
    if match is None:
        return ParsedResponse(
            kind="error",
            raw=raw_response,
            error="Invalid response format. Reply with FINAL: <answer> or TOOL: <name> <json>.",
        )

    tool_name = match.group(1)
    arg_text = match.group(2).strip() or "{}"
    try:
        params = json.loads(arg_text)
    except json.JSONDecodeError as exc:
        return ParsedResponse(
            kind="error",
            raw=raw_response,
            error=f"Tool arguments must be valid JSON: {exc}",
        )
    if not isinstance(params, dict):
        return ParsedResponse(
            kind="error",
            raw=raw_response,
            error="Tool arguments must decode to a JSON object.",
        )
    return ParsedResponse(kind="tool", raw=raw_response, tool_name=tool_name, params=params)


def _base_agent_instructions(tool_schemas: Sequence[Mapping[str, Any]]) -> str:
    tool_lines = []
    for tool in tool_schemas:
        name = str(tool["name"])
        description = str(tool["description"])
        example = TOOL_EXAMPLES.get(name, "{}")
        tool_lines.append(f"- {name}: {description} Example: {example}")

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
