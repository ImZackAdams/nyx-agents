"""Lilbot command line interface."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from importlib import metadata
import sys

from lilbot.agent import LilbotAgent
from lilbot.config import LilbotConfig
from lilbot.model import build_model
from lilbot.onboarding import (
    render_doctor_report,
    render_self_test_report,
    run_init_wizard,
    run_self_test,
)
from lilbot.tools import build_default_tool_registry
from lilbot.utils.logging import StepLogger


VALID_BACKENDS = ("hf",)
VALID_DEVICES = ("auto", "cpu", "cuda")
CHAT_EXIT_WORDS = {"exit", "quit", ":q"}
CHAT_CLEAR_WORDS = {"clear", ":clear"}
CHAT_HELP_WORDS = {"/help", "help"}
CHAT_STATUS_WORDS = {"/status"}
CHAT_MODEL_WORDS = {"/model"}
CHAT_TOOLS_WORDS = {"/tools"}
CHAT_EXIT_SLASH_WORDS = {"/exit", "/quit"}
CHAT_CLEAR_SLASH_WORDS = {"/clear"}
MAX_CHAT_HISTORY_TURNS = 3
MAX_CHAT_CONTEXT_CHARS = 280


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lilbot",
        description="Local-first AI command line assistant for developers and system administrators.",
        epilog=(
            "Examples:\n"
            "  lilbot init\n"
            "  lilbot doctor\n"
            "  lilbot self-test\n"
            "  lilbot\n"
            "  lilbot \"why is my system slow?\"\n"
            "  lilbot repo summarize .\n"
            "  lilbot logs analyze /var/log/syslog"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_package_version()}",
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="A free-form query or a Lilbot subcommand such as init, doctor, self-test, repo, logs, or explain-command. Omit it to start interactive chat mode.",
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
        "--quantize-4bit",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable optional 4-bit GPU loading when supported.",
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
        quantize_4bit=args.quantize_4bit,
        max_steps=args.max_steps,
        workspace_root=args.workspace_root,
        shell_timeout_seconds=args.shell_timeout,
        verbose=args.verbose,
    )

    _emit_config_diagnostics(config)
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
        if mode == "doctor":
            print(_run_doctor_command(payload, config))
            return
        if mode == "init":
            print(_run_init_command(payload, config))
            return
        if mode == "self-test":
            report, exit_code = _run_self_test_command(payload, config)
            print(report)
            if exit_code:
                raise SystemExit(exit_code)
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
    if command in {"repo", "logs", "explain-command", "doctor", "init", "self-test"}:
        if not extras:
            if command in {"doctor", "init", "self-test"}:
                return command, []
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
    registry = build_default_tool_registry(config)
    _emit_model_diagnostics(model)
    agent = LilbotAgent(
        model,
        registry,
        max_steps=config.max_steps,
        logger=StepLogger(enabled=config.verbose),
    )
    conversation: list[tuple[str, str]] = []

    _print_chat_banner(config, model, registry)

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
        if normalized in CHAT_EXIT_WORDS or normalized in CHAT_EXIT_SLASH_WORDS:
            print("Leaving Lilbot.")
            return
        if normalized in CHAT_CLEAR_WORDS or normalized in CHAT_CLEAR_SLASH_WORDS:
            conversation.clear()
            print("Conversation cleared.")
            continue
        if normalized in CHAT_HELP_WORDS:
            print(_chat_help_text())
            continue
        if normalized in CHAT_STATUS_WORDS:
            print(_chat_status_text(config, model, registry, conversation))
            continue
        if normalized in CHAT_MODEL_WORDS:
            print(_chat_model_text(config, model))
            continue
        if normalized in CHAT_TOOLS_WORDS:
            print(_chat_tools_text(registry))
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


def _run_doctor_command(parts: list[str], config: LilbotConfig) -> str:
    if parts:
        raise SystemExit("doctor does not accept additional arguments")
    return render_doctor_report(config)


def _run_init_command(parts: list[str], config: LilbotConfig) -> str:
    if parts:
        raise SystemExit("init does not accept additional arguments")
    return run_init_wizard(config, input_func=input)


def _run_self_test_command(parts: list[str], config: LilbotConfig) -> tuple[str, int]:
    if parts:
        raise SystemExit("self-test does not accept additional arguments")
    result = run_self_test(config)
    return render_self_test_report(result), result.exit_code


def _emit_config_diagnostics(config: LilbotConfig) -> None:
    if config.user_config_error:
        print(
            f"Warning: Lilbot ignored an invalid config file at {config.user_config_path}: {config.user_config_error}",
            file=sys.stderr,
        )


def _emit_model_diagnostics(model: object) -> None:
    runtime_summary = getattr(model, "runtime_summary", "")
    if runtime_summary:
        print(runtime_summary, file=sys.stderr)
    for warning in getattr(model, "load_warnings", []):
        print(f"Warning: {warning}", file=sys.stderr)


def _print_chat_banner(config: LilbotConfig, model: object, registry: object) -> None:
    print("Lilbot interactive mode")
    print(_chat_status_text(config, model, registry, []))
    print("Commands: /help /status /model /tools /clear /exit")
    print("Type a request and press Enter.")


def _chat_help_text() -> str:
    return "\n".join(
        [
            "Interactive commands:",
            "- /help: show the command list",
            "- /status: show the active model, device, and workspace",
            "- /model: show model runtime details",
            "- /tools: list available tools",
            "- /clear: reset chat context",
            "- /exit: leave Lilbot",
        ]
    )


def _chat_status_text(
    config: LilbotConfig,
    model: object,
    registry: object,
    conversation: Sequence[tuple[str, str]],
) -> str:
    return "\n".join(
        [
            f"Model: {_model_location(model, config)}",
            f"Runtime: {_runtime_mode_text(model, config)}",
            f"Workspace: {config.workspace_root}",
            f"Config: {config.user_config_path}",
            f"Tools: {len(getattr(registry, 'names', lambda: [])())}",
            f"Conversation turns: {len(conversation)}",
        ]
    )


def _chat_model_text(config: LilbotConfig, model: object) -> str:
    summary = getattr(model, "runtime_summary", "") or "Runtime summary unavailable."
    lines = [
        summary,
        f"Model path: {_model_location(model, config)}",
        f"Device preference: {config.device}",
        f"4-bit requested: {'yes' if config.quantize_4bit else 'no'}",
    ]
    warnings = list(getattr(model, "load_warnings", []))
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines)


def _chat_tools_text(registry: object) -> str:
    describe = getattr(registry, "describe", None)
    if callable(describe):
        return "Available tools:\n" + describe()
    return "Available tools are unavailable."


def _model_location(model: object, config: LilbotConfig) -> str:
    return str(getattr(model, "model_name", None) or config.model or "(not configured)")


def _runtime_mode_text(model: object, config: LilbotConfig) -> str:
    device = getattr(model, "device", None)
    device_name = getattr(device, "type", None) or str(device or config.device)
    quantized = bool(getattr(model, "quantization_active", False))
    if quantized:
        return f"{device_name} with 4-bit quantization"
    return device_name


def _package_version() -> str:
    try:
        return metadata.version("lilbot")
    except metadata.PackageNotFoundError:
        return "0+unknown"


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
        lines.append(f"Turn {index} user: {_truncate_chat_context(prior_user)}")
        lines.append(f"Turn {index} lilbot: {_truncate_chat_context(prior_answer)}")
    lines.append("Latest user message:")
    lines.append(user_message)
    return "\n".join(lines)


def _truncate_chat_context(text: str) -> str:
    rendered = " ".join(str(text).split())
    if len(rendered) <= MAX_CHAT_CONTEXT_CHARS:
        return rendered
    return rendered[:MAX_CHAT_CONTEXT_CHARS].rstrip() + " ..."
