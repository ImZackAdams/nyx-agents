from __future__ import annotations

from typing import Dict


def build_prompt(user_request: str, memory: str, tools: Dict[str, dict], scratchpad: str) -> str:
    tool_lines = []
    for name, spec in tools.items():
        tool_lines.append(f"- {name}: {spec['description']} | input: {spec['input_schema']}")

    return (
        "You are a local agent runtime. Decide when to call tools.\n"
        "Respond in exactly one of the following formats.\n\n"
        "Tool call format (exactly two lines):\n"
        "TOOL: <tool_name>\n"
        "INPUT: <json>\n\n"
        "Final answer format (single line):\n"
        "FINAL: <answer>\n\n"
        "Only call tools when they are strictly necessary to answer.\n"
        "Do not call tools for greetings, small talk, or general knowledge.\n"
        "If you call a tool, you must provide valid JSON with all required fields.\n\n"
        "Example tool call:\n"
        "TOOL: search_docs\n"
        "INPUT: {\"query\": \"lilbot agent loop\", \"top_k\": 3}\n\n"
        "Example final:\n"
        "FINAL: The agent loop is the cycle of reasoning, tool use, and memory updates.\n\n"
        f"User request:\n{user_request}\n\n"
        f"Conversation memory:\n{memory}\n\n"
        "Available tools:\n"
        + "\n".join(tool_lines)
        + "\n\n"
        f"Scratchpad:\n{scratchpad}\n"
    )
