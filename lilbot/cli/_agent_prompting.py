from __future__ import annotations

from collections.abc import Mapping, Sequence
import json

from lilbot.cli._agent_types import ConversationMessage


def build_agent_prompt(
    *,
    system_prompt: str,
    messages: Sequence[ConversationMessage],
    note_context: str,
    history_context: str,
    tool_schemas: Sequence[Mapping[str, object]],
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


def _base_agent_instructions(tool_schemas: Sequence[Mapping[str, object]]) -> str:
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
