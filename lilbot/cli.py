"""Lilbot command line interface."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import sys

from lilbot.agent import LilbotAgent
from lilbot.model import build_model
from lilbot.tools import build_tool_registry
from lilbot.tools.logs import summarize_log
from lilbot.tools.repo import find_function, summarize_repo
from lilbot.utils.config import LilbotConfig
from lilbot.utils.logging import AgentTraceLogger


VALID_DEVICES = ("auto", "cpu", "cuda")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lilbot",
        description="Local AI-powered CLI assistant for developers and system administrators.",
    )
    parser.add_argument("command", nargs="?", help="A free-form query or a Lilbot subcommand")
    parser.add_argument("--model-path", default=None, help="Path to a local Hugging Face model")
    parser.add_argument("--device", choices=VALID_DEVICES, default=None, help="Preferred inference device")
    parser.add_argument("--max-new-tokens", type=int, default=None, help="Maximum new tokens to generate")
    parser.add_argument("--max-steps", type=int, default=None, help="Maximum reasoning steps")
    parser.add_argument(
        "--quantize-4bit",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable optional 4-bit loading when supported",
    )
    parser.add_argument("--workspace-root", default=None, help="Workspace root for safe file access")
    parser.add_argument("--shell-timeout", type=int, default=None, help="Timeout for safe shell commands")
    parser.add_argument(
        "--quiet-agent",
        action="store_true",
        help="Disable [THOUGHT]/[ACTION]/[OBSERVATION] telemetry",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    args, extras = parser.parse_known_args(raw_argv)
    config = LilbotConfig.from_sources(
        model_path=args.model_path,
        device=args.device,
        max_new_tokens=args.max_new_tokens,
        max_steps=args.max_steps,
        quantize_4bit=args.quantize_4bit,
        workspace_root=args.workspace_root,
        shell_timeout_seconds=args.shell_timeout,
        verbose_agent=not args.quiet_agent,
    )

    mode, payload = _resolve_mode(parser, args.command, extras)
    try:
        if mode == "query":
            print(_run_query(" ".join(payload), config))
            return
        if mode == "repo":
            print(_run_repo_command(payload, config))
            return
        if mode == "logs":
            print(_run_logs_command(payload, config))
            return
        if mode == "explain-command":
            print(_run_explain_command(payload, config))
            return
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    parser.error(f"Unsupported mode: {mode}")


def _resolve_mode(
    parser: argparse.ArgumentParser,
    command: str | None,
    extras: list[str],
) -> tuple[str, list[str]]:
    if command in {"repo", "logs", "explain-command"}:
        if not extras:
            parser.error(f"{command} requires additional arguments")
        return command, extras

    parts = [part for part in [command, *extras] if part]
    if not parts:
        parser.error("a query or subcommand is required")
    return "query", parts


def _run_query(parts: str, config: LilbotConfig) -> str:
    model = build_model(config)
    _emit_model_diagnostics(model)
    trace_logger = AgentTraceLogger(enabled=config.verbose_agent)
    agent = LilbotAgent(
        model,
        build_tool_registry(config),
        max_steps=config.max_steps,
        trace_logger=trace_logger,
    )
    return agent.answer(parts).answer


def _run_repo_command(parts: list[str], config: LilbotConfig) -> str:
    parser = argparse.ArgumentParser(prog="lilbot repo")
    parser.add_argument("action", choices=("summarize", "trace-function"))
    parsed, remainder = parser.parse_known_args(parts)

    if parsed.action == "summarize":
        summarize_parser = argparse.ArgumentParser(prog="lilbot repo summarize")
        summarize_parser.add_argument("path", nargs="?", default=".")
        summarize_args = summarize_parser.parse_args(remainder)
        return summarize_repo(config, summarize_args.path)

    trace_parser = argparse.ArgumentParser(prog="lilbot repo trace-function")
    trace_parser.add_argument("name")
    trace_parser.add_argument("path", nargs="?", default=".")
    trace_args = trace_parser.parse_args(remainder)
    return find_function(config, trace_args.name, trace_args.path)


def _run_logs_command(parts: list[str], config: LilbotConfig) -> str:
    parser = argparse.ArgumentParser(prog="lilbot logs")
    parser.add_argument("action", choices=("analyze",))
    parser.add_argument("path")
    parsed = parser.parse_args(parts)
    return summarize_log(config, parsed.path)


def _run_explain_command(parts: list[str], config: LilbotConfig) -> str:
    command = " ".join(parts).strip()
    if not command:
        raise SystemExit("explain-command requires a shell command string")

    prompt = (
        "Explain the following shell command for a developer or system administrator.\n"
        "Break down the flags, describe the effect, and mention any risks.\n\n"
        f"Command: {command}"
    )
    model = build_model(config)
    _emit_model_diagnostics(model)
    trace_logger = AgentTraceLogger(enabled=config.verbose_agent)
    agent = LilbotAgent(
        model,
        build_tool_registry(config),
        max_steps=max(1, min(config.max_steps, 2)),
        trace_logger=trace_logger,
    )
    return agent.answer(prompt, allowed_tools=[]).answer


def _emit_model_diagnostics(model: object) -> None:
    runtime_summary = getattr(model, "runtime_summary", "")
    if runtime_summary:
        print(runtime_summary, file=sys.stderr)

    for warning in getattr(model, "load_warnings", []):
        print(f"Warning: {warning}", file=sys.stderr)
