"""Lilbot command line interface."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import sys

from lilbot.agent import LilbotAgent
from lilbot.config import LilbotConfig
from lilbot.model import build_model
from lilbot.tools import build_default_tool_registry
from lilbot.utils.logging import StepLogger


VALID_BACKENDS = ("hf",)
VALID_DEVICES = ("auto", "cpu", "cuda")
CHAT_EXIT_WORDS = {"exit", "quit", ":q"}
CHAT_CLEAR_WORDS = {"clear", ":clear"}
MAX_CHAT_HISTORY_TURNS = 6


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lilbot",
        description="Local-first AI command line assistant for developers and system administrators.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="A free-form query or a Lilbot subcommand such as repo, logs, or explain-command. Omit it to start interactive chat mode.",
    )
    parser.add_argument(
        "--model",
        "--model-path",
        dest="model",
        default=None,
        help="Local model path or cached Hugging Face model identifier.",
    )
    parser.add_argument(
        "--backend",
        choices=VALID_BACKENDS,
        default=None,
        help="Local model backend. Only Hugging Face is implemented today.",
    )
    parser.add_argument(
        "--device",
        choices=VALID_DEVICES,
        default=None,
        help="Preferred inference device.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=None,
        help="Maximum number of new tokens generated per model step.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature. Use 0 for deterministic output.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Maximum controller iterations before Lilbot stops.",
    )
    parser.add_argument(
        "--workspace-root",
        default=None,
        help="Workspace root used for safe filesystem and repository access.",
    )
    parser.add_argument(
        "--shell-timeout",
        type=int,
        default=None,
        help="Timeout in seconds for safe shell commands.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable step-by-step controller logging on stderr.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    args, extras = parser.parse_known_args(raw_argv)

    config = LilbotConfig.from_sources(
        backend=args.backend,
        model=args.model,
        device=args.device,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        max_steps=args.max_steps,
        workspace_root=args.workspace_root,
        shell_timeout_seconds=args.shell_timeout,
        verbose=args.verbose,
    )

    mode, payload = _resolve_mode(parser, args.command, extras)

    try:
        if mode == "query":
            print(_run_query(" ".join(payload), config))
            return
        if mode == "interactive":
            _run_chat_loop(config)
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
        return "interactive", []
    return "query", parts


def _run_query(query: str, config: LilbotConfig) -> str:
    model = build_model(config)
    _emit_model_diagnostics(model)
    agent = LilbotAgent(
        model,
        build_default_tool_registry(config),
        max_steps=config.max_steps,
        logger=StepLogger(enabled=config.verbose),
    )
    return agent.answer(query).answer


def _run_chat_loop(config: LilbotConfig) -> None:
    model = build_model(config)
    _emit_model_diagnostics(model)
    agent = LilbotAgent(
        model,
        build_default_tool_registry(config),
        max_steps=config.max_steps,
        logger=StepLogger(enabled=config.verbose),
    )
    conversation: list[tuple[str, str]] = []

    print("Lilbot interactive mode")
    print("Type a request and press Enter.")
    print("Use `clear` to reset context or `exit` to leave.")

    while True:
        try:
            raw_input_text = input("lilbot> ")
        except EOFError:
            print()
            print("Leaving Lilbot.")
            return
        except KeyboardInterrupt:
            print()
            print("Leaving Lilbot.")
            return

        user_message = raw_input_text.strip()
        if not user_message:
            continue

        normalized = user_message.lower()
        if normalized in CHAT_EXIT_WORDS:
            print("Leaving Lilbot.")
            return
        if normalized in CHAT_CLEAR_WORDS:
            conversation.clear()
            print("Conversation cleared.")
            continue

        request = _build_chat_request(user_message, conversation)
        try:
            answer = agent.answer(request).answer
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            continue

        print(answer)
        conversation.append((user_message, answer))
        if len(conversation) > MAX_CHAT_HISTORY_TURNS:
            conversation[:] = conversation[-MAX_CHAT_HISTORY_TURNS:]


def _run_repo_command(parts: list[str], config: LilbotConfig) -> str:
    parser = argparse.ArgumentParser(prog="lilbot repo")
    parser.add_argument("action", choices=("summarize", "trace-function"))
    parsed, remainder = parser.parse_known_args(parts)
    registry = build_default_tool_registry(config)

    if parsed.action == "summarize":
        summarize_parser = argparse.ArgumentParser(prog="lilbot repo summarize")
        summarize_parser.add_argument("path", nargs="?", default=".")
        summarize_args = summarize_parser.parse_args(remainder)
        return registry.execute("summarize_repo", {"path": summarize_args.path})

    trace_parser = argparse.ArgumentParser(prog="lilbot repo trace-function")
    trace_parser.add_argument("name")
    trace_parser.add_argument("path", nargs="?", default=".")
    trace_args = trace_parser.parse_args(remainder)
    return registry.execute(
        "find_function",
        {"name": trace_args.name, "path": trace_args.path},
    )


def _run_logs_command(parts: list[str], config: LilbotConfig) -> str:
    parser = argparse.ArgumentParser(prog="lilbot logs")
    parser.add_argument("action", choices=("analyze",))
    parser.add_argument("path")
    parsed = parser.parse_args(parts)
    registry = build_default_tool_registry(config)
    return registry.execute("summarize_log", {"path": parsed.path})


def _run_explain_command(parts: list[str], config: LilbotConfig) -> str:
    command = " ".join(parts).strip()
    if not command:
        raise SystemExit("explain-command requires a shell command string")

    prompt = (
        "Explain the following shell command for a developer or system administrator.\n"
        "Break down the flags, describe the effect, and mention risks or side effects.\n"
        "Do not assume the command is safe just because it is common.\n\n"
        f"Command: {command}"
    )
    model = build_model(config)
    _emit_model_diagnostics(model)
    agent = LilbotAgent(
        model,
        build_default_tool_registry(config),
        max_steps=max(1, min(config.max_steps, 2)),
        logger=StepLogger(enabled=config.verbose),
    )
    return agent.answer(prompt, allowed_tools=[]).answer


def _emit_model_diagnostics(model: object) -> None:
    runtime_summary = getattr(model, "runtime_summary", "")
    if runtime_summary:
        print(runtime_summary, file=sys.stderr)


def _build_chat_request(
    user_message: str,
    conversation: Sequence[tuple[str, str]],
) -> str:
    if not conversation:
        return user_message

    lines = [
        "Interactive session context:",
        "Previous turns are provided for continuity. Focus on the latest user message.",
    ]
    for index, (prior_user, prior_answer) in enumerate(conversation[-MAX_CHAT_HISTORY_TURNS:], start=1):
        lines.append(f"Turn {index} user: {prior_user}")
        lines.append(f"Turn {index} lilbot: {prior_answer}")
    lines.append("Latest user message:")
    lines.append(user_message)
    return "\n".join(lines)
