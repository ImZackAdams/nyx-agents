from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import json
import logging
from typing import Any

from lilbot.cli._agent_prompting import build_agent_prompt
from lilbot.cli._agent_protocol import StreamState, _final_text, parse_model_response
from lilbot.cli._agent_types import ConversationMessage, GeneratesText, TokenCallback


LOGGER = logging.getLogger("lilbot.agent")
DEFAULT_AGENT_MAX_STEPS = 4
DEFAULT_HISTORY_MESSAGES = 12


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
        prompt = build_agent_prompt(
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

        parsed = parse_model_response(raw_response)
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
