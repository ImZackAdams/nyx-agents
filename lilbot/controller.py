"""Explicit Lilbot controller loop."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import json
import re
from typing import Any

from lilbot.memory.session import LilbotSession, SessionStep
from lilbot.model.base import BaseModel
from lilbot.prompts import build_controller_prompt
from lilbot.tools.registry import ToolRegistry
from lilbot.utils.logging import StepLogger


CODE_FENCE_PATTERN = re.compile(r"^```(?:json|text)?\s*(.*?)```$", re.DOTALL)
ROLE_PREFIX_PATTERN = re.compile(r"^\s*(?:assistant|user|system)\s*:\s*", re.IGNORECASE)
SPECIAL_TOKEN_PATTERN = re.compile(r"<\|(?:assistant|user|system)\|>")
THOUGHT_PATTERN = re.compile(r"(?mi)^\s*THOUGHT:\s*(.+)$")
ACTION_PATTERN = re.compile(r"(?mi)^\s*ACTION:\s*([A-Za-z_][\w-]*)\s*$")
SLOW_SYSTEM_REQUEST_PATTERN = re.compile(
    r"\b(?:why(?:'s| is)?\s+(?:my|the)\s+system\s+slow|system\s+is\s+slow|slow\s+system|slowdown|"
    r"system\s+performance|sluggish|laggy|lagging)\b",
    re.IGNORECASE,
)
PERCENT_USED_PATTERN = re.compile(r"\((?P<percent>[\d.]+)% used\)")
LABELED_PROCESS_PATTERN = re.compile(
    r"pid=(?P<pid>\d+)\s+command=(?P<command>\S+)\s+cpu=(?P<cpu>[\d.]+)%\s+mem=(?P<mem>[\d.]+)%"
)
PLAIN_PROCESS_PATTERN = re.compile(
    r"^(?P<pid>\d+)\s+(?P<command>\S+)\s+(?P<cpu>[\d.]+)\s+(?P<mem>[\d.]+)$"
)


@dataclass(frozen=True)
class ParsedReply:
    """Parsed model reply for a controller step."""

    thought: str | None
    action_name: str | None
    action_args: dict[str, Any]
    final_answer: str | None
    raw: str


class LilbotController:
    """Keep the LLM in a reasoning role while Python controls execution."""

    def __init__(
        self,
        *,
        model: BaseModel,
        tool_registry: ToolRegistry,
        max_steps: int = 4,
        logger: StepLogger | None = None,
    ) -> None:
        self.model = model
        self.tool_registry = tool_registry
        self.max_steps = max(1, int(max_steps))
        self.logger = logger or StepLogger(enabled=False)

    def run(
        self,
        session: LilbotSession,
        *,
        allowed_tools: Sequence[str] | None = None,
    ) -> str:
        seen_tool_calls: set[tuple[str, str]] = set()
        allowed_tool_set = set(allowed_tools) if allowed_tools is not None else None

        for step_number in range(1, self.max_steps + 1):
            prompt = build_controller_prompt(
                user_query=session.user_query,
                tool_registry=self.tool_registry,
                session=session,
                allowed_tools=allowed_tools,
            )
            step = SessionStep(number=step_number, prompt=prompt)
            session.steps.append(step)

            self.logger.step(step_number)
            raw = self.model.generate(prompt).strip()
            step.raw_model_output = raw
            self.logger.raw(raw)

            parsed = parse_model_response(raw)
            step.thought = parsed.thought
            if parsed.thought:
                self.logger.thought(parsed.thought)

            if parsed.final_answer is not None:
                session.final_answer = parsed.final_answer.strip() or "(empty response)"
                self.logger.final(session.final_answer)
                return session.final_answer

            if not parsed.action_name:
                session.final_answer = (
                    "The model returned malformed output. Expected either "
                    "THOUGHT/ACTION/ARGS or FINAL."
                )
                step.error = session.final_answer
                self.logger.error(session.final_answer)
                return session.final_answer

            step.action_name = parsed.action_name
            step.action_args = dict(parsed.action_args)
            self.logger.action(parsed.action_name)
            self.logger.args(parsed.action_args)

            if allowed_tool_set is not None and parsed.action_name not in allowed_tool_set:
                observation = (
                    f"Tool blocked: {parsed.action_name} is not available for this request. "
                    "Answer directly with FINAL."
                )
            else:
                signature = (
                    parsed.action_name,
                    json.dumps(parsed.action_args, ensure_ascii=True, sort_keys=True),
                )
                if signature in seen_tool_calls:
                    observation = (
                        f"Repeated tool call blocked for {parsed.action_name}. "
                        "Use the existing observation and return FINAL."
                    )
                else:
                    seen_tool_calls.add(signature)
                    try:
                        observation = self.tool_registry.execute(parsed.action_name, parsed.action_args)
                    except Exception as exc:
                        observation = f"Tool error from {parsed.action_name}: {exc}"

            step.observation = observation
            self.logger.observation(observation)

            auto_answer = _maybe_finalize_from_observations(session)
            if auto_answer is not None:
                session.final_answer = auto_answer
                self.logger.final(session.final_answer)
                return session.final_answer

        last_observation = session.steps[-1].observation if session.steps else None
        if last_observation:
            session.final_answer = (
                "Lilbot hit the maximum step limit before producing a FINAL answer.\n"
                f"Last observation:\n{last_observation}"
            )
        else:
            session.final_answer = (
                "Lilbot hit the maximum step limit before producing a FINAL answer."
            )
        self.logger.error(session.final_answer)
        return session.final_answer


def parse_model_response(raw_response: str) -> ParsedReply:
    """Parse the text-only controller protocol used by Lilbot."""

    normalized = _normalize_model_output(raw_response)
    thought_match = THOUGHT_PATTERN.search(normalized)
    thought = thought_match.group(1).strip() if thought_match else None

    final_match = re.search(r"(?is)\bFINAL:\s*(.+)$", normalized)
    if final_match is not None:
        return ParsedReply(
            thought=thought,
            action_name=None,
            action_args={},
            final_answer=final_match.group(1).strip(),
            raw=normalized,
        )

    action_match = ACTION_PATTERN.search(normalized)
    if action_match is None:
        return ParsedReply(
            thought=thought,
            action_name=None,
            action_args={},
            final_answer=None,
            raw=normalized,
        )

    args = _parse_args_block(normalized)
    if args is None:
        return ParsedReply(
            thought=thought,
            action_name=None,
            action_args={},
            final_answer=None,
            raw=normalized,
        )

    return ParsedReply(
        thought=thought,
        action_name=action_match.group(1).strip(),
        action_args=args,
        final_answer=None,
        raw=normalized,
    )


def _parse_args_block(text: str) -> dict[str, Any] | None:
    match = re.search(r"(?is)\bARGS:\s*", text)
    if match is None:
        return {}

    payload = text[match.end() :].lstrip()
    if not payload:
        return {}

    start = payload.find("{")
    if start < 0:
        return {}

    decoder = json.JSONDecoder()
    try:
        parsed, _ = decoder.raw_decode(payload[start:])
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _normalize_model_output(raw_response: str) -> str:
    text = str(raw_response or "").strip()
    if not text:
        return ""

    fence_match = CODE_FENCE_PATTERN.match(text)
    if fence_match is not None:
        text = fence_match.group(1).strip()

    text = SPECIAL_TOKEN_PATTERN.sub("", text).strip()
    text = ROLE_PREFIX_PATTERN.sub("", text).strip()
    return text


def _maybe_finalize_from_observations(session: LilbotSession) -> str | None:
    if not SLOW_SYSTEM_REQUEST_PATTERN.search(session.user_query):
        return None

    observation_blocks = [
        step.observation
        for step in session.steps
        if step.observation and step.action_name in {"inspect_system", "cpu_snapshot", "memory_usage", "disk_usage"}
    ]
    if not observation_blocks:
        return None
    return _summarize_slow_system("\n".join(observation_blocks))


def _summarize_slow_system(observation: str) -> str:
    lines = [line.strip() for line in observation.splitlines() if line.strip()]
    if not lines:
        return "I inspected the system, but the snapshot was empty."

    memory_percent = _extract_percent_for_prefix(
        lines,
        prefixes=("- memory:",),
    )
    swap_percent = _extract_percent_for_prefix(
        lines,
        prefixes=("- swap:",),
    )
    disk_percent = _extract_percent_for_prefix(
        lines,
        prefixes=("- workspace_disk:", "- workspace:", "- root_disk:", "- root:"),
    )
    cpu_processes = _extract_processes(lines, section_names=("- top_cpu_processes:",))

    conclusions: list[str] = []
    if cpu_processes:
        top_process_text = ", ".join(
            f"{process['command']} ({process['cpu']}% CPU, pid {process['pid']})"
            for process in cpu_processes[:3]
        )
        conclusions.append(
            f"The strongest bottleneck in this snapshot looks like CPU pressure from {top_process_text}."
        )

    if swap_percent is not None and swap_percent >= 50.0:
        if memory_percent is not None and memory_percent < 70.0:
            conclusions.append(
                f"Swap usage is elevated at {swap_percent:.1f}%, which can still cause lag even though RAM is not currently near full."
            )
        else:
            conclusions.append(
                f"Swap usage is elevated at {swap_percent:.1f}%, which suggests memory pressure may be contributing to the slowdown."
            )

    if disk_percent is not None:
        if disk_percent >= 90.0:
            conclusions.append(
                f"Disk usage is critically high at {disk_percent:.1f}%, which can hurt system responsiveness."
            )
        elif disk_percent >= 80.0:
            conclusions.append(
                f"Disk usage is somewhat high at {disk_percent:.1f}%, but it does not look like the primary bottleneck from this snapshot."
            )

    if not conclusions:
        conclusions.append(
            "The system snapshot did not show a single obvious bottleneck, but the current CPU, memory, and disk signals do not look catastrophic."
        )

    next_steps: list[str] = []
    if cpu_processes:
        next_steps.append(
            "Start by checking whether the top CPU-heavy processes are expected workloads and whether any can be paused or restarted."
        )
    if swap_percent is not None and swap_percent >= 50.0:
        next_steps.append(
            "If the machine still feels sluggish, investigate active swapping next because high swap use often makes interactive work feel slow."
        )
    if disk_percent is not None and disk_percent >= 90.0:
        next_steps.append(
            "Free some disk space on the fuller filesystem before troubleshooting more subtle causes."
        )

    answer_lines = ["Based on the current snapshot:"]
    answer_lines.extend(f"- {item}" for item in conclusions)
    if next_steps:
        answer_lines.append("First things to do:")
        answer_lines.extend(f"- {item}" for item in next_steps)
    return "\n".join(answer_lines)


def _extract_percent_for_prefix(
    lines: Sequence[str],
    *,
    prefixes: Sequence[str],
) -> float | None:
    for line in lines:
        if not any(line.startswith(prefix) for prefix in prefixes):
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
    section_names: Sequence[str],
) -> list[dict[str, str]]:
    in_section = False
    processes: list[dict[str, str]] = []
    for line in lines:
        if line in section_names:
            in_section = True
            continue
        if in_section and line.startswith("- "):
            break
        if not in_section:
            continue

        match = LABELED_PROCESS_PATTERN.search(line)
        if match is None:
            match = PLAIN_PROCESS_PATTERN.search(line)
        if match is None:
            continue
        processes.append(match.groupdict())
    return processes
