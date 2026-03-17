"""Prompt templates for the Lilbot controller loop."""

from __future__ import annotations

from collections.abc import Sequence

from lilbot.memory.session import LilbotSession
from lilbot.tools.registry import ToolRegistry


SYSTEM_PROMPT = """You are Lilbot, a local-first AI command line assistant for developers and system administrators.

You are not the operating system. You are a reasoning engine that can inspect local state only through deterministic tools.

Rules:
- Never invent tool results, file contents, command output, or repository details.
- Keep thoughts brief and practical.
- Use the minimum number of tools needed to answer correctly.
- Prefer read-oriented tools and safe diagnostics.
- If no tools are available, answer directly with FINAL.
- When you use a tool, choose a real tool name exactly as listed.
- Return exactly one of these formats:
THOUGHT: <brief reasoning>
ACTION: tool_name
ARGS: {"key": "value"}

or

THOUGHT: <brief reasoning>
FINAL: <answer>
"""


def build_controller_prompt(
    *,
    user_query: str,
    tool_registry: ToolRegistry,
    session: LilbotSession,
    allowed_tools: Sequence[str] | None = None,
) -> str:
    tools_text = tool_registry.describe(allowed_tools)
    if allowed_tools is not None and not allowed_tools:
        tool_guidance = "No tools are available for this request. Respond with FINAL."
    else:
        tool_guidance = "Use tools only when the answer depends on local machine state, files, logs, or repository contents."

    if not session.steps:
        history_block = "(no prior steps)"
    else:
        lines: list[str] = []
        for step in session.steps:
            lines.append(f"Step {step.number}:")
            if step.thought:
                lines.append(f"- thought: {step.thought}")
            if step.action_name:
                lines.append(f"- action: {step.action_name}")
                lines.append(f"- args: {step.action_args}")
            if step.observation:
                lines.append(f"- observation: {step.observation}")
            if step.error:
                lines.append(f"- error: {step.error}")
        history_block = "\n".join(lines)

    return "\n\n".join(
        [
            SYSTEM_PROMPT.strip(),
            tool_guidance,
            "Available tools:",
            tools_text,
            f"User request:\n{user_query}",
            f"Prior transcript:\n{history_block}",
            "Respond with the next THOUGHT/ACTION/ARGS block or a THOUGHT/FINAL block.",
        ]
    )
