"""Minimal Lilbot reasoning loop."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import json
import re
from typing import Any, Protocol

from lilbot.tools import ToolRegistry
from lilbot.utils.logging import AgentTraceLogger


CODE_FENCE_PATTERN = re.compile(r"^```(?:json|text)?\s*(.*?)```$", re.DOTALL)
SPECIAL_TOKEN_PATTERN = re.compile(r"<\|(?:assistant|user|system)\|>")
ROLE_PREFIX_PATTERN = re.compile(r"^\s*(?:assistant|user|system)\s*:\s*", re.IGNORECASE)
THOUGHT_PATTERN = re.compile(r"(?mi)^\s*THOUGHT:\s*(.+)$")
SLOW_SYSTEM_REQUEST_PATTERN = re.compile(
    r"\b(?:why(?:'s| is)?\s+(?:my|the)\s+system\s+slow|system\s+is\s+slow|slow\s+system|slowdown|"
    r"system\s+performance|sluggish|laggy|lagging)\b",
    re.IGNORECASE,
)
PERCENT_USED_PATTERN = re.compile(r"\((?P<percent>[\d.]+)% used\)")
PROCESS_PATTERN = re.compile(
    r"pid=(?P<pid>\d+)\s+command=(?P<command>\S+)\s+cpu=(?P<cpu>[\d.]+)%\s+mem=(?P<mem>[\d.]+)%",
)


class GeneratesText(Protocol):
    def generate(self, prompt: str) -> str:
        ...


@dataclass(frozen=True)
class AgentResult:
    answer: str
    steps: int


@dataclass(frozen=True)
class ParsedResponse:
    thought: str | None
    final_answer: str | None
    tool_name: str | None
    arguments: dict[str, Any]
    raw: str


class LilbotAgent:
    """A small tool-using loop that treats the local model as a reasoning engine."""

    def __init__(
        self,
        model: GeneratesText,
        tool_registry: ToolRegistry,
        *,
        max_steps: int = 4,
        trace_logger: AgentTraceLogger | None = None,
    ) -> None:
        self.model = model
        self.tool_registry = tool_registry
        self.max_steps = max(1, int(max_steps))
        self.trace_logger = trace_logger or AgentTraceLogger(enabled=False)

    def answer(self, request: str, *, allowed_tools: Sequence[str] | None = None) -> AgentResult:
        observations: list[dict[str, str]] = []
        seen_tool_calls: set[tuple[str, str]] = set()

        for step in range(1, self.max_steps + 1):
            prompt = self._build_prompt(request, observations, allowed_tools)
            raw_response = self.model.generate(prompt).strip()
            parsed = _parse_model_response(raw_response)

            if parsed.thought:
                self.trace_logger.thought(parsed.thought)

            if parsed.final_answer is not None:
                return AgentResult(parsed.final_answer.strip(), step)

            if not parsed.tool_name:
                fallback = parsed.raw.strip() or "The model returned an empty response."
                return AgentResult(fallback, step)

            if allowed_tools is not None and parsed.tool_name not in set(allowed_tools):
                observation = (
                    f"Tool blocked: {parsed.tool_name} is not available for this request. "
                    "Use one of the provided tools or answer directly."
                )
            else:
                signature = (
                    parsed.tool_name,
                    json.dumps(parsed.arguments, ensure_ascii=True, sort_keys=True),
                )
                if signature in seen_tool_calls:
                    observation = (
                        f"Repeated tool call blocked for {parsed.tool_name}. "
                        "Use the observation already available and answer."
                    )
                else:
                    seen_tool_calls.add(signature)
                    self.trace_logger.action(
                        f"{parsed.tool_name}({json.dumps(parsed.arguments, ensure_ascii=True, sort_keys=True)})"
                    )
                    observation = self.tool_registry.execute(parsed.tool_name, parsed.arguments)

            self.trace_logger.observation(observation)
            observations.append(
                {
                    "tool": parsed.tool_name,
                    "arguments": json.dumps(parsed.arguments, ensure_ascii=True, sort_keys=True),
                    "observation": observation,
                }
            )

            auto_answer = _maybe_finalize_from_observations(request, observations)
            if auto_answer is not None:
                return AgentResult(auto_answer, step)

        if observations:
            last_observation = observations[-1]["observation"]
            answer = (
                "I hit the maximum reasoning step limit before reaching a final answer.\n"
                f"Last observation:\n{last_observation}"
            )
        else:
            answer = "I hit the maximum reasoning step limit before reaching a final answer."
        return AgentResult(answer, self.max_steps)

    def _build_prompt(
        self,
        request: str,
        observations: list[dict[str, str]],
        allowed_tools: Sequence[str] | None,
    ) -> str:
        tool_text = self.tool_registry.describe(allowed_tools)
        if allowed_tools is not None and not allowed_tools:
            tool_guidance = "No tools are available for this request. Respond with FINAL."
        else:
            tool_guidance = (
                "Use tools when the answer depends on local state, the repository, files, or logs."
            )

        transcript: list[str] = []
        for index, item in enumerate(observations, start=1):
            transcript.extend(
                [
                    f"Step {index} action: {item['tool']} {item['arguments']}",
                    f"Step {index} observation: {item['observation']}",
                ]
            )

        history_block = "\n".join(transcript) if transcript else "(no prior actions)"

        return "\n\n".join(
            [
                "You are Lilbot, a local AI command line assistant for developers and system administrators.",
                "The language model is only a reasoning engine. Deterministic Python tools inspect the system.",
                "Safety rules:",
                "- Prefer read-only tools.",
                "- Never invent tool results.",
                "- Keep thoughts short and operational.",
                "- The run_shell tool only accepts a single command with no pipes, redirection, or shell operators.",
                "- For performance issues such as a slow system, prefer inspect_system before reaching for run_shell.",
                tool_guidance,
                "Reply in exactly one of these formats:",
                "THOUGHT: <brief reasoning>\nACTION: {\"tool\": \"tool_name\", \"arguments\": {\"param\": \"value\"}}",
                "THOUGHT: <brief reasoning>\nFINAL: <answer>",
                "Available tools:",
                tool_text,
                f"User request:\n{request}",
                f"Observations so far:\n{history_block}",
                "Respond with the next THOUGHT/ACTION or THOUGHT/FINAL.",
            ]
        )


def _parse_model_response(raw_response: str) -> ParsedResponse:
    normalized = _normalize_model_response(raw_response)
    thought_match = THOUGHT_PATTERN.search(normalized)
    thought = thought_match.group(1).strip() if thought_match else None

    final_index = normalized.find("FINAL:")
    if final_index >= 0:
        final_answer = normalized[final_index + len("FINAL:") :].strip()
        return ParsedResponse(thought=thought, final_answer=final_answer, tool_name=None, arguments={}, raw=normalized)

    action_index = normalized.find("ACTION:")
    if action_index >= 0:
        payload = normalized[action_index + len("ACTION:") :].strip()
        action = _parse_action_object(payload)
        if action is not None:
            return ParsedResponse(
                thought=thought,
                final_answer=None,
                tool_name=action["tool_name"],
                arguments=action["arguments"],
                raw=normalized,
            )

    tool_match = re.search(r"(?is)\bTOOL:\s*([A-Za-z_][\w-]*)\s*(.*)$", normalized)
    if tool_match is not None:
        tool_name = tool_match.group(1)
        argument_text = tool_match.group(2).strip() or "{}"
        try:
            arguments = json.loads(argument_text)
        except json.JSONDecodeError:
            arguments = {}
        if isinstance(arguments, dict):
            return ParsedResponse(
                thought=thought,
                final_answer=None,
                tool_name=tool_name,
                arguments=arguments,
                raw=normalized,
            )

    plain_text = normalized.strip()
    return ParsedResponse(
        thought=thought,
        final_answer=plain_text or "(empty response)",
        tool_name=None,
        arguments={},
        raw=normalized,
    )


def _parse_action_object(payload: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    start = payload.find("{")
    if start < 0:
        return None

    try:
        action, _ = decoder.raw_decode(payload[start:])
    except json.JSONDecodeError:
        return None

    if not isinstance(action, dict):
        return None

    tool_name = str(action.get("tool", "")).strip()
    if not tool_name:
        return None

    arguments = action.get("arguments", action.get("args", {}))
    if not isinstance(arguments, dict):
        arguments = {}

    return {"tool_name": tool_name, "arguments": arguments}


def _normalize_model_response(raw_response: str) -> str:
    text = raw_response.strip()
    if not text:
        return text

    fence_match = CODE_FENCE_PATTERN.match(text)
    if fence_match is not None:
        text = fence_match.group(1).strip()

    text = SPECIAL_TOKEN_PATTERN.sub("", text).strip()
    text = ROLE_PREFIX_PATTERN.sub("", text).strip()
    return text


def _maybe_finalize_from_observations(
    request: str,
    observations: Sequence[dict[str, str]],
) -> str | None:
    if not SLOW_SYSTEM_REQUEST_PATTERN.search(request):
        return None

    for item in reversed(observations):
        if item.get("tool") == "inspect_system":
            return _summarize_slow_system(item.get("observation", ""))
    return None


def _summarize_slow_system(observation: str) -> str:
    lines = [line.strip() for line in observation.splitlines() if line.strip()]
    if not lines:
        return "I inspected the system, but the snapshot was empty."

    memory_percent = _extract_percent_for_prefix(lines, "- memory:")
    swap_percent = _extract_percent_for_prefix(lines, "- swap:")
    disk_percent = _extract_percent_for_prefix(lines, "- workspace_disk:")
    cpu_processes = _extract_processes(lines, section_name="- top_cpu_processes:")

    conclusions: list[str] = []
    if cpu_processes:
        top_process_text = ", ".join(
            f"{process['command']} ({process['cpu']}% CPU, pid {process['pid']})"
            for process in cpu_processes[:3]
        )
        conclusions.append(f"The strongest bottleneck in this snapshot is CPU pressure from {top_process_text}.")

    if swap_percent is not None and swap_percent >= 50.0:
        if memory_percent is not None and memory_percent < 70.0:
            conclusions.append(
                f"Swap usage is elevated at {swap_percent:.1f}%, which can still cause lag if swapped-out pages are being touched, "
                "even though RAM is not currently near full."
            )
        else:
            conclusions.append(
                f"Swap usage is elevated at {swap_percent:.1f}%, which suggests memory pressure may be contributing to the slowdown."
            )

    if disk_percent is not None:
        if disk_percent >= 90.0:
            conclusions.append(
                f"The workspace disk is very full at {disk_percent:.1f}%, which can also hurt system responsiveness."
            )
        elif disk_percent >= 80.0:
            conclusions.append(
                f"Disk usage is somewhat high at {disk_percent:.1f}%, but it does not look like the primary bottleneck from this snapshot."
            )

    if not conclusions:
        conclusions.append(
            "The system snapshot did not show a single obvious bottleneck, but the top processes and resource counters are the best next clues."
        )

    next_steps: list[str] = []
    if cpu_processes:
        next_steps.append(
            "Start by checking whether the top CPU-heavy processes are expected workloads and whether any can be paused or restarted."
        )
    if swap_percent is not None and swap_percent >= 50.0:
        next_steps.append(
            "If the machine still feels sluggish, investigate active swapping next, because high swap use often makes interactive tasks feel slow."
        )

    answer_lines = ["Based on the current snapshot:"]
    answer_lines.extend(f"- {item}" for item in conclusions)
    if next_steps:
        answer_lines.append("First things to do:")
        answer_lines.extend(f"- {item}" for item in next_steps)
    return "\n".join(answer_lines)


def _extract_percent_for_prefix(lines: Sequence[str], prefix: str) -> float | None:
    for line in lines:
        if not line.startswith(prefix):
            continue
        match = PERCENT_USED_PATTERN.search(line)
        if match is None:
            return None
        try:
            return float(match.group("percent"))
        except ValueError:
            return None
    return None


def _extract_processes(
    lines: Sequence[str],
    *,
    section_name: str,
) -> list[dict[str, str]]:
    in_section = False
    processes: list[dict[str, str]] = []
    for line in lines:
        if line == section_name:
            in_section = True
            continue
        if in_section and line.startswith("- "):
            break
        if not in_section:
            continue

        match = PROCESS_PATTERN.search(line)
        if match is None:
            continue
        processes.append(match.groupdict())
    return processes
