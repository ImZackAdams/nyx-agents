from __future__ import annotations

import argparse
import logging
import os
import re
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
    maybe_answer_without_llm,
    run_agent,
)
from lilbot.llm.provider import LLMProvider, ProviderConfig, build_provider
from lilbot.memory.memory import load_session_history, save_session_exchange
from lilbot.tools import ALL_TOOL_DEFS, execute_tool


LOGGER = logging.getLogger("lilbot")
VALID_BACKENDS = ("auto", "hf", "echo")
VALID_DEVICES = ("auto", "cpu", "cuda")
NON_PERSISTENT_ASSISTANT_RESPONSES = {
    "(echo provider) No model configured.",
}
NON_PERSISTENT_ASSISTANT_PATTERN = re.compile(r"^\s*(?:\[\]|\{\}|null|\(empty response\))\s*$", re.IGNORECASE)
NON_PERSISTENT_PROTOCOL_PATTERN = re.compile(
    r"^\s*(?:<\|(?:assistant|user|system)\|>\s*)*(?:FINAL:|TOOL:)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PrefixCommand:
    name: str
    usage: str
    description: str
    handler: Callable[[list[str]], str]


@dataclass(frozen=True)
class LLMRunResult:
    text: str
    elapsed: float
    streamed: bool


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


def _backend_env(default: str = "auto") -> str:
    value = (os.getenv("LILBOT_BACKEND") or default).strip().lower()
    if value in VALID_BACKENDS:
        return value
    LOGGER.warning("Ignoring invalid backend for LILBOT_BACKEND: %s", value)
    return default


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lilbot",
        description="Local LLM CLI with direct ! commands.",
        epilog="Prefix commands: !help, !ls [path], !read <file>, !sys, !note <text>, !notes [query], !history [query]",
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
    parser.add_argument(
        "--backend",
        help="LLM backend selection",
        choices=VALID_BACKENDS,
        default=_backend_env(),
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
        "--stream",
        action=argparse.BooleanOptionalAction,
        default=_bool_env("LILBOT_STREAM", True),
        help="Stream direct final answers as they are generated when it is safe to do so",
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
    parser.add_argument(
        "--session-id",
        default=os.getenv("LILBOT_SESSION_ID", "default"),
        help="Persistent session identifier for conversation history",
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

    llm: LLMProvider | None = None
    llm_error: str | None = None
    session_id = args.session_id.strip() or "default"
    os.environ["LILBOT_SESSION_ID"] = session_id
    session_history = [
        ConversationMessage(str(message["role"]), str(message["content"]))
        for message in load_session_history(session_id, limit=args.history_messages)
    ]

    # Load the model only when a prompt actually needs the LLM.
    def get_llm() -> LLMProvider | None:
        nonlocal llm, llm_error
        if llm is not None:
            return llm
        if llm_error is not None:
            return None

        model_path = args.model_path or _default_model_path()
        try:
            llm = build_provider(
                ProviderConfig(
                    backend=args.backend,
                    model_path=model_path,
                    device=args.device,
                    max_new_tokens=args.max_new_tokens,
                    quantize_4bit=args.quantize_4bit,
                    do_sample=args.sample,
                )
            )
            _print_error(llm.runtime_summary)
            for message in llm.load_warnings:
                _print_error(message)
        except Exception as exc:
            llm_error = f"Failed to initialize LLM backend: {exc}"
            LOGGER.error("LLM backend initialization failed: %s", exc)
            _print_error(llm_error)
            return None
        return llm

    if args.prompt:
        prefix_result = _run_prefix_command(args.prompt)
        if prefix_result is not None:
            print(f"\n{prefix_result}\n")
            return

        direct_response = _run_direct_agent_request(
            user_request=args.prompt,
            session_id=session_id,
            history=session_history,
            history_limit=args.history_messages,
        )
        if direct_response is not None:
            _persist_session_exchange(session_id, args.prompt, direct_response.text)
            _render_llm_result(direct_response)
            return

        provider = get_llm()
        if provider is None:
            return

        response = _run_llm_request(
            provider,
            user_request=args.prompt,
            system_prompt=args.system,
            session_id=session_id,
            history=session_history,
            history_limit=args.history_messages,
            max_steps=args.max_agent_steps,
            stream=args.stream,
        )
        if response is None:
            return

        _persist_session_exchange(session_id, args.prompt, response.text)
        _render_llm_result(response)
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
        if user_request.lower() in {"clear", "cls"}:
            _clear_screen()
            continue
        if user_request.lower() in {"help", "commands", "?"}:
            print(f"\n{_prefix_help()}\n")
            continue

        prefix_result = _run_prefix_command(user_request)
        if prefix_result is not None:
            print(f"\n{prefix_result}\n")
            continue

        direct_response = _run_direct_agent_request(
            user_request=user_request,
            session_id=session_id,
            history=session_history,
            history_limit=args.history_messages,
        )
        if direct_response is not None:
            _persist_session_exchange(session_id, user_request, direct_response.text)
            _render_llm_result(direct_response)
            continue

        provider = get_llm()
        if provider is None:
            print("\nLLM unavailable. Fix the model configuration and restart lilbot.\n")
            continue

        response = _run_llm_request(
            provider,
            user_request=user_request,
            system_prompt=args.system,
            session_id=session_id,
            history=session_history,
            history_limit=args.history_messages,
            max_steps=args.max_agent_steps,
            stream=args.stream,
        )
        if response is None:
            continue

        _persist_session_exchange(session_id, user_request, response.text)
        _render_llm_result(response)


def _run_llm_request(
    llm: LLMProvider,
    *,
    user_request: str,
    system_prompt: str,
    session_id: str,
    history: list[ConversationMessage],
    history_limit: int,
    max_steps: int,
    stream: bool,
) -> LLMRunResult | None:
    stream_printer = StreamPrinter() if stream else None
    try:
        result, elapsed = _generate_with_timing(
            lambda: run_agent(
                llm,
                user_request=user_request,
                system_prompt=system_prompt,
                session_id=session_id,
                history=history,
                history_limit=history_limit,
                max_steps=max_steps,
                tool_schemas=ALL_TOOL_DEFS,
                tool_executor=execute_tool,
                status_callback=_emit_tool_status,
                token_callback=stream_printer.write if stream_printer is not None else None,
            )
        )
        if stream_printer is not None:
            stream_printer.close()
        return LLMRunResult(result, elapsed, streamed=bool(stream_printer and stream_printer.started))
    except KeyboardInterrupt:
        if stream_printer is not None:
            stream_printer.close()
        _print_error("Generation cancelled.")
        return None
    except Exception as exc:
        if stream_printer is not None:
            stream_printer.close()
        LOGGER.error("Generation failed: %s", exc)
        _print_error(f"Generation failed: {exc}")
        return None


def _run_direct_agent_request(
    *,
    user_request: str,
    session_id: str,
    history: list[ConversationMessage],
    history_limit: int,
) -> LLMRunResult | None:
    result, elapsed = _generate_with_timing(
        lambda: maybe_answer_without_llm(
            user_request=user_request,
            session_id=session_id,
            history=history,
            history_limit=history_limit,
            tool_executor=execute_tool,
            status_callback=_emit_tool_status,
        )
    )
    if result is None:
        return None
    return LLMRunResult(result, elapsed, streamed=False)


def _generate_with_timing(operation: Callable[[], str]) -> tuple[str, float]:
    started_at = time.perf_counter()
    result = operation()
    elapsed = time.perf_counter() - started_at
    return result, elapsed


class StreamPrinter:
    def __init__(self) -> None:
        self.started = False
        self._needs_newline = False

    def write(self, text: str) -> None:
        if not text:
            return
        if not self.started:
            print()
            self.started = True
        print(text, end="", flush=True)
        self._needs_newline = not text.endswith("\n")

    def close(self) -> None:
        if self.started and self._needs_newline:
            print()
            self._needs_newline = False


def _render_llm_result(result: LLMRunResult) -> None:
    if not result.streamed:
        print(f"\n{result.text}\n")
    print(f"[completed in {result.elapsed:.2f}s]\n")


def _clear_screen() -> None:
    print("\033[2J\033[H", end="", flush=True)


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


def _handle_history(args: list[str]) -> str:
    query = " ".join(args).strip()
    params: dict[str, str | int] = {"limit": 8}
    if query:
        params["query"] = query
    return execute_tool("search_history", params)


def _print_error(message: str) -> None:
    print(f"[lilbot] {message}", file=sys.stderr)


def _emit_tool_status(message: str) -> None:
    _print_error(message)


def _persist_session_exchange(session_id: str, user_request: str, assistant_response: str) -> None:
    if not _should_persist_assistant_response(assistant_response):
        return
    try:
        save_session_exchange(session_id, user_request, assistant_response)
    except Exception as exc:
        _print_error(f"Unable to persist session history: {exc}")


def _should_persist_assistant_response(response: str) -> bool:
    stripped = response.strip()
    if not stripped:
        return False
    if stripped in NON_PERSISTENT_ASSISTANT_RESPONSES:
        return False
    if NON_PERSISTENT_PROTOCOL_PATTERN.match(stripped) is not None:
        return False
    return NON_PERSISTENT_ASSISTANT_PATTERN.fullmatch(stripped) is None


PREFIX_COMMANDS = {
    command.name: command
    for command in (
        PrefixCommand("help", "!help", "Show command help.", _handle_help),
        PrefixCommand("ls", "!ls [path]", "List files under the workspace root.", _handle_ls),
        PrefixCommand("read", "!read <file>", "Read a text file under the workspace root.", _handle_read),
        PrefixCommand("sys", "!sys", "Show basic system information.", _handle_sys),
        PrefixCommand("note", "!note <text>", "Save a note to persistent memory.", _handle_note),
        PrefixCommand("notes", "!notes [query]", "List recent notes or search saved notes.", _handle_notes),
        PrefixCommand("history", "!history [query]", "List recent session history or search earlier conversation.", _handle_history),
    )
}


if __name__ == "__main__":
    main()
