from __future__ import annotations

import argparse
import logging
import os
import platform
import shlex
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from lilbot.cli.agent import (
    ConversationMessage,
    DEFAULT_AGENT_MAX_STEPS,
    DEFAULT_HISTORY_MESSAGES,
    maybe_answer_without_llm,
    run_agent,
)
from lilbot.core.session_store import load_session_history, save_session_exchange
from lilbot.llm.provider import EchoProvider, LLMProvider, ProviderConfig, build_provider
from lilbot.paths import (
    app_data_dir,
    configured_model_path,
    default_model_dir,
    default_session_dir,
    ensure_app_directories,
    is_complete_model_path,
    resolve_default_model_path,
)
from lilbot.tools import ALL_TOOL_DEFS, execute_tool
from lilbot.tools.filesystem import get_workspace_root


LOGGER = logging.getLogger("lilbot")
VALID_BACKENDS = ("auto", "hf", "echo")
VALID_DEVICES = ("auto", "cpu", "cuda")
KNOWN_COMMANDS = {"chat", "run", "tools", "models", "doctor"}


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
        description="Minimal local LLM/agent framework with a CLI chat loop, local model providers, and workspace tools.",
        epilog="Interactive commands: !help, !tools, !ls [path], !read <file>, !write <file> <text>, !append <file> <text>, !sys",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="chat",
        help="chat, run, tools, models, doctor, or any inline prompt",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Run a one-shot prompt without entering the chat loop",
    )
    parser.add_argument(
        "--system",
        default=os.getenv("LILBOT_SYSTEM_PROMPT", ""),
        help="Additional system prompt text",
    )
    parser.add_argument(
        "--backend",
        choices=VALID_BACKENDS,
        default=_backend_env(),
        help="Provider backend selection",
    )
    parser.add_argument("--model-path", default=None, help="Path to a local Hugging Face model")
    parser.add_argument(
        "--device",
        choices=VALID_DEVICES,
        default=_device_env(),
        help="Preferred inference device",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=_int_env("LILBOT_MAX_NEW_TOKENS", 192),
        help="Maximum new tokens per response",
    )
    parser.add_argument(
        "--quantize-4bit",
        action=argparse.BooleanOptionalAction,
        default=_bool_env("LILBOT_QUANTIZE_4BIT", True),
        help="Enable 4-bit quantization when supported",
    )
    parser.add_argument(
        "--sample",
        action=argparse.BooleanOptionalAction,
        default=_bool_env("LILBOT_DO_SAMPLE", False),
        help="Enable sampling",
    )
    parser.add_argument(
        "--stream",
        action=argparse.BooleanOptionalAction,
        default=_bool_env("LILBOT_STREAM", True),
        help="Stream final answers when possible",
    )
    parser.add_argument(
        "--max-agent-steps",
        type=int,
        default=_int_env("LILBOT_MAX_AGENT_STEPS", DEFAULT_AGENT_MAX_STEPS),
        help="Maximum tool calls the agent can make per prompt",
    )
    parser.add_argument(
        "--history-messages",
        type=int,
        default=_int_env("LILBOT_HISTORY_MESSAGES", DEFAULT_HISTORY_MESSAGES),
        help="Number of prior chat messages to keep in the prompt",
    )
    parser.add_argument(
        "--session-id",
        default=os.getenv("LILBOT_SESSION_ID", "default"),
        help="Persistent chat session identifier",
    )
    parser.add_argument(
        "--workspace-root",
        default=os.getenv("LILBOT_WORKSPACE_ROOT"),
        help="Workspace root for filesystem tools",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    _load_dotenv()
    _configure_logging()
    ensure_app_directories()

    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    parser = _build_parser()
    args, extras = parser.parse_known_args(raw_argv)
    mode, payload = _resolve_mode(parser, args.command, extras, args.prompt)

    if args.workspace_root:
        os.environ["LILBOT_WORKSPACE_ROOT"] = args.workspace_root

    if mode == "tools":
        print(f"\n{_tool_catalog()}\n")
        return
    if mode == "models":
        print(f"\n{_models_report(args)}\n")
        return
    if mode == "doctor":
        print(f"\n{_doctor_report(args)}\n")
        return
    if mode == "run":
        assert payload is not None
        _run_once(args, payload)
        return

    _run_chat(args)


def _run_once(args: argparse.Namespace, prompt: str) -> None:
    prefix_result = _run_prefix_command(prompt)
    if prefix_result is not None:
        print(f"\n{prefix_result}\n")
        return

    history = _load_messages(args.session_id, args.history_messages)
    direct_response = _run_direct_agent_request(
        user_request=prompt,
        session_id=args.session_id,
        history=history,
        history_limit=args.history_messages,
    )
    if direct_response is not None:
        if _should_persist_assistant_response(direct_response.text):
            _persist_session_exchange(args.session_id, prompt, direct_response.text)
        _render_llm_result(direct_response)
        return

    provider = _get_llm(args)
    if provider is None:
        return
    if isinstance(provider, EchoProvider):
        print(f"\n{_no_model_configured_response()}\n")
        return

    response = _run_llm_request(
        provider,
        user_request=prompt,
        system_prompt=args.system,
        session_id=args.session_id,
        history=history,
        history_limit=args.history_messages,
        max_steps=args.max_agent_steps,
        stream=args.stream,
    )
    if response is None:
        return

    if _should_persist_assistant_response(response.text):
        _persist_session_exchange(args.session_id, prompt, response.text)
    _render_llm_result(response)


def _run_chat(args: argparse.Namespace) -> None:
    history = _load_messages(args.session_id, args.history_messages)
    provider: LLMProvider | None = None

    while True:
        try:
            user_request = input("lilbot> ").strip()
        except EOFError:
            print("\nNo interactive input available. Use `lilbot --prompt \"...\"` for one-shot runs.")
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
            session_id=args.session_id,
            history=history,
            history_limit=args.history_messages,
        )
        if direct_response is not None:
            if _should_persist_assistant_response(direct_response.text):
                _persist_session_exchange(args.session_id, user_request, direct_response.text)
            _render_llm_result(direct_response)
            continue

        if provider is None:
            provider = _get_llm(args)
        if provider is None:
            continue
        if isinstance(provider, EchoProvider):
            print(f"\n{_no_model_configured_response()}\n")
            continue

        response = _run_llm_request(
            provider,
            user_request=user_request,
            system_prompt=args.system,
            session_id=args.session_id,
            history=history,
            history_limit=args.history_messages,
            max_steps=args.max_agent_steps,
            stream=args.stream,
        )
        if response is None:
            continue

        if _should_persist_assistant_response(response.text):
            _persist_session_exchange(args.session_id, user_request, response.text)
        _render_llm_result(response)


def _load_messages(session_id: str, history_limit: int) -> list[ConversationMessage]:
    return [
        ConversationMessage(str(message["role"]), str(message["content"]))
        for message in load_session_history(session_id, limit=history_limit)
    ]


def _get_llm(args: argparse.Namespace) -> LLMProvider | None:
    model_path = args.model_path or resolve_default_model_path()
    try:
        provider = build_provider(
            ProviderConfig(
                backend=args.backend,
                model_path=model_path,
                device=args.device,
                max_new_tokens=args.max_new_tokens,
                quantize_4bit=args.quantize_4bit,
                do_sample=args.sample,
            )
        )
    except Exception as exc:
        LOGGER.error("LLM backend initialization failed: %s", exc)
        _print_error(f"Failed to initialize model backend: {exc}")
        _print_error("Run `lilbot doctor` to inspect your local setup.")
        return None

    if not isinstance(provider, EchoProvider):
        _print_error(provider.runtime_summary)
        for warning in provider.load_warnings:
            _print_error(warning)
    return provider


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


def _persist_session_exchange(session_id: str, user_text: str, assistant_text: str) -> None:
    try:
        save_session_exchange(session_id, user_text, assistant_text)
    except OSError as exc:
        LOGGER.warning("Unable to persist session history: %s", exc)
        _print_error(f"Warning: unable to persist session history: {exc}")


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


def _resolve_mode(
    parser: argparse.ArgumentParser,
    command: str | None,
    extras: list[str],
    prompt: str | None,
) -> tuple[str, str | None]:
    if prompt is not None:
        return "run", prompt
    if command in {None, "chat"}:
        if extras:
            parser.error(f"unrecognized arguments: {' '.join(extras)}")
        return "chat", None
    if command in {"tools", "models", "doctor"}:
        if extras:
            parser.error(f"{command} does not take extra arguments")
        return command, None
    if command == "run":
        inline_prompt = " ".join(extras).strip()
        if not inline_prompt:
            parser.error("run requires a prompt")
        return "run", inline_prompt

    request = " ".join([command, *extras]).strip()
    if command.startswith("!"):
        return "run", request
    if command in PREFIX_COMMANDS:
        return "run", f"!{request}"
    if command in KNOWN_COMMANDS:
        parser.error(f"Unsupported command usage: {command}")
    return "run", request


def _prefix_help() -> str:
    lines = ["Available chat commands:"]
    for command in PREFIX_COMMANDS.values():
        lines.append(f"{command.usage}  {command.description}")
    return "\n".join(lines)


def _tool_catalog() -> str:
    lines = ["Built-in tools:"]
    for tool in ALL_TOOL_DEFS:
        lines.append(f"- {tool['name']}: {tool['description']}")
    return "\n".join(lines)


def _models_report(args: argparse.Namespace) -> str:
    configured = args.model_path or configured_model_path()
    resolved = args.model_path or resolve_default_model_path()
    lines = [
        f"Backend: {args.backend}",
        f"Configured model path: {configured or '(none)'}",
        f"Resolved model path: {resolved or '(none)'}",
        f"Model path complete: {'yes' if is_complete_model_path(resolved) else 'no'}",
        f"Default model directory: {default_model_dir()}",
    ]
    return "\n".join(lines)


def _doctor_report(args: argparse.Namespace) -> str:
    lines = [
        "Lilbot doctor",
        f"Python: {platform.python_version()}",
        f"App data directory: {app_data_dir()}",
        f"Session directory: {default_session_dir()}",
        f"Workspace root: {get_workspace_root()}",
        f"Backend: {args.backend}",
        f"Model directory: {default_model_dir()}",
        _models_report(args),
    ]
    return "\n".join(lines)


def _handle_ls(args: list[str]) -> str:
    path = args[0] if args else "."
    return execute_tool("list_files", {"path": path})


def _handle_read(args: list[str]) -> str:
    if not args:
        return "Usage: !read <path>"
    return execute_tool("read_file", {"path": " ".join(args)})


def _handle_write(args: list[str], *, mode: str) -> str:
    if len(args) < 2:
        label = "append" if mode == "append" else "write"
        return f"Usage: !{label} <path> <text>"
    return execute_tool(
        "write_file",
        {"path": args[0], "content": " ".join(args[1:]), "mode": mode},
    )


def _handle_sys(_: list[str]) -> str:
    return execute_tool("system_info", {})


def _no_model_configured_response() -> str:
    return (
        "No local model is configured.\n"
        "Set `LILBOT_MODEL_PATH` or pass `--model-path`, then rerun `lilbot models` or `lilbot doctor`."
    )


def _should_persist_assistant_response(response: str) -> bool:
    return bool(response.strip()) and "No local model is configured." not in response


def _emit_tool_status(message: str) -> None:
    print(f"[tool] {message}", file=sys.stderr)


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


PREFIX_COMMANDS = {
    "help": PrefixCommand("help", "!help", "Show interactive command help", lambda _: _prefix_help()),
    "tools": PrefixCommand("tools", "!tools", "List built-in tools", lambda _: _tool_catalog()),
    "ls": PrefixCommand("ls", "!ls [path]", "List files under the workspace root", _handle_ls),
    "read": PrefixCommand("read", "!read <path>", "Read a workspace file", _handle_read),
    "write": PrefixCommand(
        "write",
        "!write <path> <text>",
        "Overwrite a workspace file",
        lambda args: _handle_write(args, mode="overwrite"),
    ),
    "append": PrefixCommand(
        "append",
        "!append <path> <text>",
        "Append to a workspace file",
        lambda args: _handle_write(args, mode="append"),
    ),
    "sys": PrefixCommand("sys", "!sys", "Show basic local system information", _handle_sys),
}
