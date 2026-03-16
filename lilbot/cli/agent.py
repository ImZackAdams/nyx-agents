from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Protocol

from lilbot.tools.filesystem import get_workspace_root


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
EXPLICIT_FILE_PATTERN = re.compile(
    r"(?<![\w/.-])("
    r"(?:[./]?[\w.-]+(?:/[\w.-]+)*/[\w.-]+)"
    r"|README(?:\.md)?"
    r"|LICENSE(?:\.[\w.-]+)?"
    r"|pyproject\.toml"
    r"|\.env(?:\.example)?"
    r"|[\w.-]+\.[A-Za-z0-9_-]+"
    r")(?![\w/.-])",
    re.IGNORECASE,
)
DIRECTORY_REFERENCE_PATTERN = re.compile(
    r"^\s*(?:the\s+)?(?P<path>`?[\w./-]+`?)\s+(?:directory|dir|folder)\s*$|"
    r"\b(?:in|inside|under|from)\s+(?:the\s+)?(?P<scoped>`?[\w./-]+`?)\s+(?:directory|dir|folder)\b",
    re.IGNORECASE,
)
LISTING_REQUEST_PATTERN = re.compile(
    r"\b(?:what(?:\s+files?)?\s+(?:are|is|'s)?\s*in|what's\s+in|list(?:\s+the)?\s+files?|show(?:\s+me)?(?:\s+the)?\s+files?|contents?\s+of|files?\s+in)\b|"
    r"^\s*(?:list\s+files?|show\s+files?|files?)\s*$",
    re.IGNORECASE,
)
SYSTEM_REQUEST_PATTERN = re.compile(
    r"\b(?:what is|what's|describe|show|tell me about)\b.*\b(?:my|this)\s+system\b|"
    r"\b(?:system info|system information|machine info|machine information|host info)\b",
    re.IGNORECASE,
)
SUMMARY_REQUEST_PATTERN = re.compile(
    r"\b(?:summari[sz]e|describe|explain|read|show|open|inspect|what is in)\b",
    re.IGNORECASE,
)
NAME_REQUEST_PATTERN = re.compile(
    r"^\s*what(?:'s| is)\s+my\s+name\??\s*$",
    re.IGNORECASE,
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

    def _flush(self, *, allow_plain_text: bool) -> None:
        normalized = _normalize_stream_candidate(self.raw_buffer)
        if self.mode is None:
            if normalized.startswith("TOOL:"):
                self.mode = "tool"
            elif normalized.startswith("FINAL:"):
                self.mode = "final"
            elif allow_plain_text and normalized and not _looks_like_json_payload(normalized):
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
    del session_id, history, history_limit

    if NAME_REQUEST_PATTERN.match(user_request.strip()):
        return "I don't know your name. This minimal Lilbot build does not keep personal profile memory."

    if SYSTEM_REQUEST_PATTERN.search(user_request):
        return _run_direct_tool(
            tool_executor,
            "system_info",
            {},
            status_callback=status_callback,
        )

    if _is_directory_listing_request(user_request):
        directory_path = _extract_directory_reference(user_request) or "."
        observation = _run_direct_tool(
            tool_executor,
            "list_files",
            {"path": directory_path, "max_entries": 50},
            status_callback=status_callback,
        )
        title = "Workspace contents:" if directory_path == "." else f"Directory contents ({directory_path}):"
        return title + "\n" + observation

    file_path = _extract_file_reference(user_request)
    if file_path is not None and SUMMARY_REQUEST_PATTERN.search(user_request):
        observation = _run_direct_tool(
            tool_executor,
            "read_file",
            {"path": file_path, "max_chars": 6000},
            status_callback=status_callback,
        )
        if _looks_like_tool_error(observation):
            return observation
        return _summarize_file_content(file_path, observation)

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
        if _looks_like_json_payload(normalized):
            return ParsedResponse(
                kind="error",
                raw=normalized,
                error="Bare JSON is not a valid reply. Use FINAL: <answer> or TOOL: <tool_name> <json>.",
            )
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


def _run_direct_tool(
    tool_executor: Callable[[str, Mapping[str, Any] | None], str],
    tool_name: str,
    params: Mapping[str, Any],
    *,
    status_callback: Callable[[str], None] | None,
) -> str:
    if status_callback is not None:
        status_callback(_tool_status_message(tool_name, params))
    return _execute_tool(tool_executor, tool_name, params)


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


def _looks_like_json_payload(text: str) -> bool:
    stripped = text.strip()
    if not stripped.startswith(("{", "[")):
        return False
    try:
        json.loads(stripped)
    except json.JSONDecodeError:
        return False
    return True


def _extract_file_reference(user_request: str) -> str | None:
    candidates: list[str] = []
    for match in EXPLICIT_FILE_PATTERN.finditer(user_request):
        value = match.group(1).strip().strip("`'\"")
        if value:
            candidates.append(value)

    lowered = user_request.lower()
    if "readme" in lowered and "README.md" not in candidates:
        candidates.append("README.md")
    if "license" in lowered and "LICENSE" not in candidates:
        candidates.append("LICENSE")

    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        resolved = _resolve_workspace_file_reference(candidate)
        if resolved is not None:
            return resolved
    return None


def _is_directory_listing_request(user_request: str) -> bool:
    lowered = user_request.strip().lower()
    if not lowered:
        return False
    if LISTING_REQUEST_PATTERN.search(user_request):
        return True
    if _extract_directory_reference(user_request) is not None:
        return True
    return lowered in {
        "here",
        "this directory",
        "this folder",
        "current directory",
        "current folder",
        "workspace",
        "repo",
        "repository",
        "project",
    }


def _extract_directory_reference(user_request: str) -> str | None:
    lowered = user_request.lower()
    implicit_root_markers = (
        " here",
        " in here",
        "this workspace",
        "this directory",
        "this folder",
        "current directory",
        "current folder",
        "workspace",
        "repo",
        "repository",
        "project",
    )
    if any(marker in lowered for marker in implicit_root_markers) or lowered.strip() in {
        "here",
        "workspace",
        "repo",
        "repository",
        "project",
    }:
        return "."

    match = DIRECTORY_REFERENCE_PATTERN.search(user_request)
    if match is None:
        return None

    candidate = (match.group("path") or match.group("scoped") or "").strip().strip("`'\"")
    if not candidate:
        return None
    return _resolve_workspace_directory_reference(candidate)


def _resolve_workspace_directory_reference(reference: str) -> str | None:
    root = get_workspace_root()
    candidate = Path(reference).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=False)
    except OSError:
        resolved = candidate

    if resolved.exists() and resolved.is_dir():
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            return None
        return "." if not relative.parts else relative.as_posix()
    return None


def _resolve_workspace_file_reference(reference: str) -> str | None:
    root = get_workspace_root()
    candidate = Path(reference).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=False)
    except OSError:
        resolved = candidate
    if resolved.exists() and resolved.is_file():
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            return None

    basename = Path(reference).name.lower()
    visited = 0
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in {".git", ".venv", "__pycache__"}]
        for filename in filenames:
            visited += 1
            if visited > 5000:
                return None
            if filename.lower() != basename:
                continue
            path = Path(current_root) / filename
            return path.relative_to(root).as_posix()
    return None


def _looks_like_tool_error(text: str) -> bool:
    lowered = text.lower()
    return lowered.startswith(
        (
            "path not found",
            "not a file",
            "not a directory",
            "binary file not shown",
            "unable to ",
            "missing required parameter",
            "invalid path",
            "path is outside",
            "tool ",
        )
    )


def _summarize_file_content(path: str, text: str) -> str:
    basename = Path(path).name
    lowered_path = basename.lower()
    lowered_text = text.lower()

    if lowered_path.startswith("license") or "mit license" in lowered_text:
        return _summarize_license(basename, text)
    if lowered_path in {"readme", "readme.md"}:
        return _summarize_markdown_file(basename, text)
    return _summarize_generic_file(basename, text)


def _summarize_license(name: str, text: str) -> str:
    lowered = text.lower()
    if "mit license" in lowered:
        points = [
            "MIT License.",
            "Allows use, modification, distribution, private use, and commercial use.",
            "Requires preserving the copyright and license notice.",
            "Provided without warranty or liability.",
        ]
    elif "apache license" in lowered:
        points = [
            "Apache License.",
            "Allows use, modification, and distribution, including commercial use.",
            "Includes an express patent license.",
            "Requires preserving notices and documenting significant changes.",
        ]
    else:
        points = _key_lines(text, limit=4)

    return "\n".join([f"{name} summary:"] + [f"- {point}" for point in points])


def _summarize_markdown_file(name: str, text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    heading = next((line.lstrip("# ").strip() for line in lines if line.startswith("#")), "")
    bullets = [line.lstrip("-* ").strip() for line in lines if line.startswith(("-", "*"))][:4]
    paragraph = _first_paragraph(text)

    points: list[str] = []
    if heading:
        points.append(heading)
    if paragraph:
        points.append(paragraph)
    points.extend(item for item in bullets if item and item not in points)
    if not points:
        points = _key_lines(text, limit=4)

    return "\n".join([f"{name} summary:"] + [f"- {point}" for point in points[:5]])


def _summarize_generic_file(name: str, text: str) -> str:
    points = _key_lines(text, limit=5)
    return "\n".join([f"{name} summary:"] + [f"- {point}" for point in points])


def _first_paragraph(text: str) -> str:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    if not chunks:
        return ""
    paragraph = " ".join(chunks[0].split())
    return paragraph[:220] + ("..." if len(paragraph) > 220 else "")


def _key_lines(text: str, *, limit: int) -> list[str]:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("#", "//", "/*", "*", "```")):
            line = line.lstrip("#/* ").strip()
        if not line:
            continue
        lines.append(line[:220] + ("..." if len(line) > 220 else ""))
        if len(lines) >= limit:
            break
    return lines or ["File is empty."]


__all__ = [
    "ConversationMessage",
    "DEFAULT_AGENT_MAX_STEPS",
    "DEFAULT_HISTORY_MESSAGES",
    "maybe_answer_without_llm",
    "run_agent",
]
