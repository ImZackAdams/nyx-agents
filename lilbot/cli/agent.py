from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import json
import logging
import re
from typing import Any, Protocol


LOGGER = logging.getLogger("lilbot.agent")
DEFAULT_AGENT_MAX_STEPS = 4
DEFAULT_HISTORY_MESSAGES = 12
PROTOCOL_LINE_PATTERN = re.compile(r"(?m)^(FINAL:|TOOL:)\s*(.*)$", re.DOTALL)
CODE_FENCE_PATTERN = re.compile(r"^```(?:json|text)?\s*(.*?)```$", re.DOTALL)
ROLE_LABEL_PATTERN = re.compile(
    r"^\s*(?:\[[^\]]+\]|(?:assistant|user|system|observation)\s*:)\s*",
    re.IGNORECASE,
)
SPECIAL_TOKEN_PATTERN = re.compile(r"<\|(?:assistant|user|system)\|>")


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
    del session_id

    working_messages = _trim_history(history, history_limit)
    working_messages.append(ConversationMessage("user", user_request))
    last_observation: str | None = None
    seen_tool_calls: set[tuple[str, str]] = set()

    for _ in range(max(1, max_steps)):
        prompt = _build_agent_prompt(
            system_prompt=system_prompt,
            messages=working_messages,
            tool_schemas=tool_schemas,
        )
        stream_state = StreamState(token_callback) if token_callback is not None else None
        raw_response = llm.generate(
            prompt,
            on_token=stream_state.on_token if stream_state is not None else None,
        ).strip()
        if stream_state is not None:
            stream_state.finalize(raw_response)

        parsed = _parse_model_response(raw_response)
        if parsed.kind == "final":
            final_text = _final_text(parsed.raw)
            _append_exchange(history, user_request, final_text, history_limit)
            return final_text

        if parsed.kind == "tool":
            assert parsed.tool_name is not None
            params = parsed.params or {}
            signature = _tool_signature(parsed.tool_name, params)
            if status_callback is not None:
                status_callback(_tool_status_message(parsed.tool_name, params))

            if signature in seen_tool_calls:
                observation = (
                    f"Refused: repeated tool call for {parsed.tool_name}. "
                    "Use the information already gathered and answer with FINAL."
                )
            else:
                seen_tool_calls.add(signature)
                observation = _execute_tool(tool_executor, parsed.tool_name, params)
                last_observation = observation

            working_messages.append(ConversationMessage("assistant", parsed.raw))
            working_messages.append(
                ConversationMessage("tool", f"{parsed.tool_name}: {observation}")
            )
            continue

        LOGGER.debug(
            "Invalid model response for request %r: %s",
            user_request,
            parsed.error or parsed.raw,
        )
        working_messages.append(ConversationMessage("assistant", parsed.raw))
        working_messages.append(
            ConversationMessage(
                "tool",
                parsed.error or "Invalid model response. Use FINAL: or TOOL: <name> <json>.",
            )
        )

    fallback = _fallback_answer(last_observation)
    _append_exchange(history, user_request, fallback, history_limit)
    return fallback


def maybe_answer_without_llm(
    *,
    user_request: str,
    session_id: str,
    history: list[ConversationMessage],
    history_limit: int,
    tool_executor: Callable[[str, Mapping[str, Any] | None], str],
    status_callback: Callable[[str], None] | None = None,
) -> str | None:
    del user_request, session_id, history, history_limit, tool_executor, status_callback
    return None


def _build_agent_prompt(
    *,
    system_prompt: str,
    messages: Sequence[ConversationMessage],
    tool_schemas: Sequence[Mapping[str, object]],
) -> str:
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
        tool_lines.append(
            f"- {name}: {description} Params: {parameter_text}. Example: {example}"
        )

    sections = [
        "\n".join(
            [
                "You are lilbot, a minimal local-first LLM agent.",
                "You must respond with exactly one of these formats:",
                "FINAL: <answer>",
                "TOOL: <tool_name> <json object>",
                "Use at most one tool per message.",
                "After you receive an Observation, either call another tool or answer with FINAL.",
                "Prefer tools over guessing when the answer depends on workspace files or local system state.",
                "If you are asked to summarize a file, summarize it instead of pasting raw file contents.",
                "Never prefix your answer with [assistant] or Assistant:.",
                "Never invent tool results.",
                "Keep answers concise unless the user asks for more detail.",
                "Available tools:",
                *tool_lines,
            ]
        )
    ]
    if system_prompt.strip():
        sections.append(f"Additional system guidance:\n{system_prompt.strip()}")
    sections.append("Conversation:\n" + _format_messages(messages))
    sections.append("Assistant:")
    return "\n\n".join(sections)


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


def _parse_model_response(raw_response: str) -> ParsedResponse:
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
    return ParsedResponse(
        kind="tool",
        raw=f"TOOL: {tool_name} {arg_text}",
        tool_name=tool_name,
        params=params,
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


def _append_exchange(
    history: list[ConversationMessage],
    user_request: str,
    assistant_response: str,
    history_limit: int,
) -> None:
    history.append(ConversationMessage("user", user_request))
    history.append(ConversationMessage("assistant", assistant_response))
    history[:] = _trim_history(history, history_limit)


def _trim_history(
    history: list[ConversationMessage],
    history_limit: int,
) -> list[ConversationMessage]:
    if history_limit <= 0:
        return []
    return list(history[-history_limit:])


def _fallback_answer(last_observation: str | None) -> str:
    if last_observation:
        return (
            "I did not get a clean FINAL response from the model. "
            f"The last tool result was:\n{last_observation}"
        )
    return "I reached the tool-use limit before producing a final answer."


def _execute_tool(
    tool_executor: Callable[[str, Mapping[str, Any] | None], str],
    tool_name: str,
    params: Mapping[str, Any],
) -> str:
    try:
        return tool_executor(tool_name, params)
    except Exception as exc:
        return f"Tool {tool_name} failed: {exc}"


def _tool_status_message(tool_name: str, params: Mapping[str, Any]) -> str:
    if not params:
        return tool_name
    return f"{tool_name} {json.dumps(dict(params), ensure_ascii=True, sort_keys=True)}"


def _tool_signature(tool_name: str, params: Mapping[str, Any]) -> tuple[str, str]:
    return (
        tool_name,
        json.dumps(dict(params), ensure_ascii=True, sort_keys=True),
    )


__all__ = [
    "ConversationMessage",
    "DEFAULT_AGENT_MAX_STEPS",
    "DEFAULT_HISTORY_MESSAGES",
    "maybe_answer_without_llm",
    "run_agent",
]
