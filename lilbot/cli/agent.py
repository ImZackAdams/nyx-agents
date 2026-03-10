from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import json
import logging
from typing import Any

from lilbot.cli._agent_policy import (
    _allow_live_streaming,
    _append_exchange,
    _can_use_observation_for_fallback,
    _coerce_final_answer,
    _direct_answer,
    _direct_tool_answer,
    _fallback_answer,
    _looks_like_personal_fact_request,
    _observation_message,
    _prefetch_tool_requests,
    _relevant_history_context,
    _relevant_note_context,
    _resolve_personal_fact_answer,
    _save_note_allowed,
    _should_replace_fallback,
    _tool_signature,
    _trim_history,
)
from lilbot.cli._agent_prompting import build_agent_prompt
from lilbot.cli._agent_protocol import StreamState, _final_text, parse_model_response
from lilbot.cli._agent_types import (
    ConversationMessage,
    GeneratesText,
    ParsedResponse,
    PrefetchState,
    TokenCallback,
)


LOGGER = logging.getLogger("lilbot.agent")
DEFAULT_AGENT_MAX_STEPS = 4
DEFAULT_HISTORY_MESSAGES = 8


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
            final_text = _coerce_final_answer(
                user_request=user_request,
                final_text=_final_text(parsed.raw),
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
                status_callback(_tool_status_message(parsed.tool_name, params))

            if tool_signature in seen_tool_calls:
                observation = (
                    f"Refused: repeated tool call for {parsed.tool_name}. "
                    "Use the information already gathered and answer with FINAL."
                )
            elif parsed.tool_name == "save_note" and not _save_note_allowed(user_request):
                observation = (
                    "Refused: save_note requires an explicit request to remember or save something."
                )
            else:
                seen_tool_calls.add(tool_signature)
                observation = _execute_tool(tool_executor, parsed.tool_name, params)

            last_tool_name = parsed.tool_name
            last_observation = observation
            if _can_use_observation_for_fallback(observation) and _should_replace_fallback(
                fallback_observation,
                observation,
            ):
                fallback_tool_name = parsed.tool_name
                fallback_observation = observation

            working_messages.append(ConversationMessage("assistant", parsed.raw))
            working_messages.append(_observation_message(parsed.tool_name, observation))
            continue

        LOGGER.debug(
            "Invalid model response for request %r: %s",
            user_request,
            parsed.error or parsed.raw,
        )
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
            status_callback(_tool_status_message(tool_name, params))

        observation = _execute_tool(tool_executor, tool_name, params)
        seen_tool_calls.add(tool_signature)
        last_tool_name = tool_name
        last_observation = observation
        if _can_use_observation_for_fallback(observation) and _should_replace_fallback(
            fallback_observation,
            observation,
        ):
            fallback_tool_name = tool_name
            fallback_observation = observation
        working_messages.append(_observation_message(tool_name, observation))

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


def _tool_status_message(tool_name: str, params: Mapping[str, Any]) -> str:
    return f"tool {tool_name} {json.dumps(dict(params), ensure_ascii=True, sort_keys=True)}"


def _execute_tool(
    tool_executor: Callable[[str, Mapping[str, Any] | None], str],
    tool_name: str,
    params: Mapping[str, Any] | None,
) -> str:
    try:
        return tool_executor(tool_name, params)
    except Exception as exc:
        return f"Tool execution error: {exc}"
