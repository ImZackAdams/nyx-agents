from __future__ import annotations

import argparse
import os
import shlex
import time

from lilbot.llm.provider import EchoProvider, LocalHFProvider
from lilbot.tools.filesystem import list_files, read_file
from lilbot.tools.notes import save_note
from lilbot.tools.system import system_info


def _default_model_path() -> str | None:
    candidates = []
    env_path = os.getenv("LILBOT_MODEL_PATH") or os.getenv("TEXT_MODEL_PATH")
    if env_path:
        candidates.append(env_path)
    candidates.append(os.path.join(os.getcwd(), "lilbot", "models", "falcon3_10b_instruct"))
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def main() -> None:
    parser = argparse.ArgumentParser(prog="lilbot")
    sub = parser.add_subparsers(dest="command")

    run_cmd = sub.add_parser("run", help="Run the CLI")
    run_cmd.add_argument("--system", help="Optional system prompt", default=os.getenv("LILBOT_SYSTEM_PROMPT", ""))
    run_cmd.add_argument("--model-path", help="Local HF model path", default=None)
    run_cmd.add_argument("--device", help="auto|cpu|cuda", default=os.getenv("LILBOT_DEVICE", "cuda"))
    run_cmd.add_argument("--max-new-tokens", type=int, default=int(os.getenv("LILBOT_MAX_NEW_TOKENS", "96")))
    run_cmd.add_argument(
        "--quantize-4bit",
        action="store_true",
        default=os.getenv("LILBOT_QUANTIZE_4BIT", "1").lower() in {"1", "true", "yes", "on"},
        help="Enable 4-bit quantization (GPU)",
    )
    run_cmd.add_argument("--prompt", help="Run a single prompt non-interactively", default=None)

    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        return

    llm: EchoProvider | LocalHFProvider | None = None

    # Load the model only when a prompt actually needs the LLM.
    def get_llm() -> EchoProvider | LocalHFProvider:
        nonlocal llm
        if llm is None:
            model_path = args.model_path or _default_model_path()
            if model_path:
                llm = LocalHFProvider(
                    model_path,
                    device=args.device,
                    max_new_tokens=args.max_new_tokens,
                    quantize_4bit=args.quantize_4bit,
                )
            else:
                llm = EchoProvider()
        return llm

    if args.prompt:
        prefix_result = _run_prefix_command(args.prompt)
        if prefix_result is not None:
            print(f"\n{prefix_result}\n")
            return
        prompt = _build_prompt(args.system, args.prompt)
        result, elapsed = _generate_with_timing(get_llm(), prompt)
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
        prefix_result = _run_prefix_command(user_request)
        if prefix_result is not None:
            print(f"\n{prefix_result}\n")
            continue
        prompt = _build_prompt(args.system, user_request)
        result, elapsed = _generate_with_timing(get_llm(), prompt)
        print(f"\n{result}\n")
        print(f"[completed in {elapsed:.2f}s]\n")


def _build_prompt(system_prompt: str, user_request: str) -> str:
    if system_prompt:
        return f"{system_prompt}\n\nUser: {user_request}\nAssistant:"
    return f"User: {user_request}\nAssistant:"


def _generate_with_timing(llm: EchoProvider | LocalHFProvider, prompt: str) -> tuple[str, float]:
    started_at = time.perf_counter()
    result = llm.generate(prompt)
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
    if command == "ls":
        path = " ".join(args) if args else "."
        output = list_files({"path": path})
        if output.startswith(("Path not found:", "Not a directory:")):
            return output
        if path == ".":
            return f"Files in current directory:\n{output}"
        return f"Files in {path}:\n{output}"

    if command == "read":
        if not args:
            return "Usage: !read <file>"
        return read_file({"path": " ".join(args)})

    if command == "sys":
        if args:
            return "Usage: !sys"
        return system_info({})

    if command == "note":
        if not args:
            return "Usage: !note <text>"
        return save_note({"text": " ".join(args)})

    return f"Unknown command: !{command}\n{_prefix_help()}"


def _prefix_help() -> str:
    return "Available commands: !ls [path], !read <file>, !sys, !note <text>"


if __name__ == "__main__":
    main()
