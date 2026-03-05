from __future__ import annotations

from typing import Dict


def build_prompt(user_request: str, memory: str, tools: Dict[str, dict], scratchpad: str) -> str:
    tool_lines = []
    for name, spec in tools.items():
        tool_lines.append(f"- {name}: {spec['description']} | input: {spec['input_schema']}")

    return (
        "You are a local agent runtime. Decide when to call tools.\n"
        "Return either:\n"
        "TOOL: <tool_name>\nINPUT: <json>\n"
        "or\nFINAL: <answer>\n\n"
        f"User request:\n{user_request}\n\n"
        f"Conversation memory:\n{memory}\n\n"
        "Available tools:\n"
        + "\n".join(tool_lines)
        + "\n\n"
        f"Scratchpad:\n{scratchpad}\n"
    )
