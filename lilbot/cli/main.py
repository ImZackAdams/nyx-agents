from __future__ import annotations

import argparse
import logging
import os
import shlex
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from lilbot.cli.agent import (
    ConversationMessage,
    DEFAULT_AGENT_MAX_STEPS,
    DEFAULT_HISTORY_MESSAGES,
    run_agent,
)
from lilbot.llm.provider import EchoProvider, LocalHFProvider
from lilbot.tools import ALL_TOOL_DEFS, execute_tool


LOGGER = logging.getLogger("lilbot")
VALID_DEVICES = ("auto", "cpu", "cuda")


@dataclass(frozen=True)
class PrefixCommand:
    name: str
    usage: str
    description: str
    handler: Callable[[list[str]], str]


def _default_model_path() -> str | None:
    candidates: list[Path] = []
    env_path = os.getenv("LILBOT_MODEL_PATH") or os.getenv("TEXT_MODEL_PATH")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    package_model = Path(__file__).resolve().parents[1] / "models" / "falcon3_10b_instruct"
    candidates.append(package_model)
    candidates.append(Path.cwd() / "lilbot" / "models" / "falcon3_10b_instruct")

    for path in candidates:
        if path.exists():
            return str(path.resolve())
    return None


def _bool_env(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        LOGGER.warning("Ignoring invalid integer for %s: %s", name, raw_value)
        return default
    return value if value > 0 else default


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _configure_logging() -> None:
    level_name = os.getenv("LILBOT_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def _device_env(default: str = "auto") -> str:
    value = (os.getenv("LILBOT_DEVICE") or default).strip().lower()
    if value in VALID_DEVICES:
        return value
    LOGGER.warning("Ignoring invalid device for LILBOT_DEVICE: %s", value)
    return default


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lilbot",
        description="Local LLM CLI with direct ! commands.",
        epilog="Prefix commands: !help, !ls [path], !read <file>, !sys, !note <text>, !notes [query]",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        help="Optional explicit 'run' keyword for interactive mode",
    )
    parser.add_argument(
        "--system",
        help="Optional system prompt",
        default=os.getenv("LILBOT_SYSTEM_PROMPT", ""),
    )
    parser.add_argument("--model-path", help="Local HF model path", default=None)
    parser.add_argument(
        "--device",
        help="Preferred inference device",
        choices=VALID_DEVICES,
        default=_device_env(),
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=_int_env("LILBOT_MAX_NEW_TOKENS", 48),
        help="Maximum new tokens per response",
    )
    parser.add_argument(
        "--quantize-4bit",
        action=argparse.BooleanOptionalAction,
        default=_bool_env("LILBOT_QUANTIZE_4BIT", True),
        help="Enable 4-bit quantization when CUDA and bitsandbytes are available",
    )
    parser.add_argument(
        "--sample",
        action=argparse.BooleanOptionalAction,
        default=_bool_env("LILBOT_DO_SAMPLE", False),
        help="Enable sampling; disabling it is faster and more deterministic",
    )
    parser.add_argument(
        "--max-agent-steps",
        type=int,
        default=_int_env("LILBOT_MAX_AGENT_STEPS", DEFAULT_AGENT_MAX_STEPS),
        help="Maximum tool-use steps per LLM request",
    )
    parser.add_argument(
        "--history-messages",
        type=int,
        default=_int_env("LILBOT_HISTORY_MESSAGES", DEFAULT_HISTORY_MESSAGES),
        help="Number of recent conversation messages to retain in session history",
    )
    parser.add_argument("--prompt", help="Run a single prompt non-interactively", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    _load_dotenv()
    _configure_logging()

    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    parser = _build_parser()
    args, extras = parser.parse_known_args(raw_argv)
    inline_request = _infer_inline_request(parser, args.command, extras)
    if args.prompt is None and inline_request is not None:
        args.prompt = inline_request

    llm: EchoProvider | LocalHFProvider | None = None
    llm_error: str | None = None
    session_history: list[ConversationMessage] = []

    # Load the model only when a prompt actually needs the LLM.
    def get_llm() -> EchoProvider | LocalHFProvider | None:
        nonlocal llm, llm_error
        if llm is not None:
            return llm
        if llm_error is not None:
            return None

        model_path = args.model_path or _default_model_path()
        try:
            if model_path:
                llm = LocalHFProvider(
                    model_path,
                    device=args.device,
                    max_new_tokens=args.max_new_tokens,
                    quantize_4bit=args.quantize_4bit,
                    do_sample=args.sample,
                )
                _print_error(llm.runtime_summary)
                for message in llm.load_warnings:
                    _print_error(message)
            else:
                llm = EchoProvider()
        except Exception as exc:
            llm_error = f"Failed to load local model: {exc}"
            LOGGER.error("Model load failed: %s", exc)
            _print_error(llm_error)
            return None
        return llm

    if args.prompt:
        prefix_result = _run_prefix_command(args.prompt)
        if prefix_result is not None:
            print(f"\n{prefix_result}\n")
            return

        provider = get_llm()
        if provider is None:
            return

        response = _run_llm_request(
            provider,
            user_request=args.prompt,
            system_prompt=args.system,
            history=[],
            history_limit=args.history_messages,
            max_steps=args.max_agent_steps,
        )
        if response is None:
            return

        result, elapsed = response
        print(f"\n{result}\n")
        print(f"[completed in {elapsed:.2f}s]\n")
        return

    while True:
        try:
            user_request = input("Request (or 'exit'): ").strip()
        except EOFError:
            print("\nNo interactive input available. Use --prompt for one-shot runs.")
            return
        if not user_request:
            continue
        if user_request.lower() in {"exit", "quit"}:
            print("Bye.")
            return
        if user_request.lower() in {"help", "commands", "?"}:
            print(f"\n{_prefix_help()}\n")
            continue

        prefix_result = _run_prefix_command(user_request)
        if prefix_result is not None:
            print(f"\n{prefix_result}\n")
            continue

        provider = get_llm()
        if provider is None:
            print("\nLLM unavailable. Fix the model configuration and restart lilbot.\n")
            continue

        response = _run_llm_request(
            provider,
            user_request=user_request,
            system_prompt=args.system,
            history=session_history,
            history_limit=args.history_messages,
            max_steps=args.max_agent_steps,
        )
        if response is None:
            continue

        result, elapsed = response
        print(f"\n{result}\n")
        print(f"[completed in {elapsed:.2f}s]\n")


def _run_llm_request(
    llm: EchoProvider | LocalHFProvider,
    *,
    user_request: str,
    system_prompt: str,
    history: list[ConversationMessage],
    history_limit: int,
    max_steps: int,
) -> tuple[str, float] | None:
    try:
        return _generate_with_timing(
            lambda: run_agent(
                llm,
                user_request=user_request,
                system_prompt=system_prompt,
                history=history,
                history_limit=history_limit,
                max_steps=max_steps,
                tool_schemas=ALL_TOOL_DEFS,
                tool_executor=execute_tool,
                status_callback=_emit_tool_status,
            )
        )
    except Exception as exc:
        LOGGER.error("Generation failed: %s", exc)
        _print_error(f"Generation failed: {exc}")
        return None


def _generate_with_timing(operation: Callable[[], str]) -> tuple[str, float]:
    started_at = time.perf_counter()
    result = operation()
    elapsed = time.perf_counter() - started_at
    return result, elapsed


def _run_prefix_command(user_input: str) -> str | None:
    if not user_input.startswith("!"):
        return None

    try:
        parts = shlex.split(user_input[1:].strip())
    except ValueError as exc:
        return f"Command parse error: {exc}"

    if not parts:
        return _prefix_help()

    command, *args = parts
    prefix_command = PREFIX_COMMANDS.get(command)
    if prefix_command is None:
        return f"Unknown command: !{command}\n{_prefix_help()}"

    return prefix_command.handler(args)


def _infer_inline_request(
    parser: argparse.ArgumentParser,
    command: str | None,
    extras: list[str],
) -> str | None:
    if command in {None, "run"}:
        if extras and any(token.startswith("-") for token in extras):
            parser.error(f"unrecognized arguments: {' '.join(extras)}")
        if extras:
            return " ".join(extras)
        return None

    request = " ".join([command, *extras]).strip()
    if not request:
        return None
    if command.startswith("!"):
        return request
    if command in PREFIX_COMMANDS:
        return f"!{request}"
    return request


def _prefix_help() -> str:
    lines = ["Available commands:"]
    for command in PREFIX_COMMANDS.values():
        lines.append(f"{command.usage}  {command.description}")
    return "\n".join(lines)


def _handle_help(_: list[str]) -> str:
    return _prefix_help()


def _handle_ls(args: list[str]) -> str:
    path_parts = [arg for arg in args if not arg.startswith("-")]
    path = " ".join(path_parts) if path_parts else "."
    output = execute_tool("list_files", {"path": path})
    if output.startswith(
        ("Path not found:", "Not a directory:", "Unable to list", "Path is outside", "Invalid path:")
    ):
        return output
    location = "current directory" if path == "." else path
    return f"Files in {location}:\n{output}"


def _handle_read(args: list[str]) -> str:
    if not args:
        return "Usage: !read <file>"
    return execute_tool("read_file", {"path": " ".join(args)})


def _handle_sys(args: list[str]) -> str:
    if args:
        return "Usage: !sys"
    return execute_tool("system_info", {})


def _handle_note(args: list[str]) -> str:
    if not args:
        return "Usage: !note <text>"
    return execute_tool("save_note", {"text": " ".join(args)})


def _handle_notes(args: list[str]) -> str:
    query = " ".join(args).strip()
    params: dict[str, str | int] = {"limit": 10}
    if query:
        params["query"] = query
    return execute_tool("search_notes", params)


def _print_error(message: str) -> None:
    print(f"[lilbot] {message}", file=sys.stderr)


def _emit_tool_status(message: str) -> None:
    _print_error(message)


PREFIX_COMMANDS = {
    command.name: command
    for command in (
        PrefixCommand("help", "!help", "Show command help.", _handle_help),
        PrefixCommand("ls", "!ls [path]", "List files under the workspace root.", _handle_ls),
        PrefixCommand("read", "!read <file>", "Read a text file under the workspace root.", _handle_read),
        PrefixCommand("sys", "!sys", "Show basic system information.", _handle_sys),
        PrefixCommand("note", "!note <text>", "Save a note to persistent memory.", _handle_note),
        PrefixCommand("notes", "!notes [query]", "List recent notes or search saved notes.", _handle_notes),
    )
}


if __name__ == "__main__":
    main()
