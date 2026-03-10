from __future__ import annotations

from dataclasses import dataclass
import json
import re

from lilbot.cli._agent_types import ParsedResponse, TokenCallback


PROTOCOL_LINE_PATTERN = re.compile(r"(?m)^(FINAL:|TOOL:)\s*(.*)$", re.DOTALL)
CODE_FENCE_PATTERN = re.compile(r"^```(?:json|text)?\s*(.*?)```$", re.DOTALL)
ROLE_LABEL_PATTERN = re.compile(
    r"^\s*(?:\[[^\]]+\]|(?:assistant|user|system|observation)\s*:)\s*",
    re.IGNORECASE,
)
SPECIAL_TOKEN_PATTERN = re.compile(r"<\|(?:assistant|user|system)\|>")


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

    @property
    def streamed(self) -> bool:
        return bool(self.emitted_text)

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


def _sanitize_answer_text(text: str) -> str:
    normalized = _strip_special_tokens(text).strip()
    if "\nFINAL:" in normalized or "\nTOOL:" in normalized:
        protocol_positions = [
            match.start()
            for match in re.finditer(r"(?m)^(?:FINAL:|TOOL:)\s*", normalized)
        ]
        if protocol_positions:
            normalized = normalized[protocol_positions[-1]:].strip()
            if normalized.startswith("FINAL:"):
                normalized = normalized.partition(":")[2].strip()
    normalized = _strip_role_labels(normalized).strip()
    return normalized


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
