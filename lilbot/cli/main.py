from __future__ import annotations

import argparse

import os

from lilbot.llm.provider import EchoProvider, LocalHFProvider


def _default_model_path() -> str | None:
    candidates = []
    env_path = os.getenv("LILBOT_MODEL_PATH") or os.getenv("TEXT_MODEL_PATH")
    if env_path:
        candidates.append(env_path)
    candidates.append(os.path.join(os.getcwd(), "src", "ml", "text", "model_files", "falcon3_10b_instruct"))
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def main() -> None:
    parser = argparse.ArgumentParser(prog="lilbot")
    sub = parser.add_subparsers(dest="command")

    run_cmd = sub.add_parser("run", help="Run the agent")
    run_cmd.add_argument("--system", help="Optional system prompt", default=os.getenv("LILBOT_SYSTEM_PROMPT", ""))
    run_cmd.add_argument("--model-path", help="Local HF model path", default=None)
    run_cmd.add_argument("--device", help="auto|cpu|cuda", default=os.getenv("LILBOT_DEVICE", "auto"))
    run_cmd.add_argument("--max-new-tokens", type=int, default=int(os.getenv("LILBOT_MAX_NEW_TOKENS", "200")))
    run_cmd.add_argument(
        "--quantize-4bit",
        action="store_true",
        default=os.getenv("LILBOT_QUANTIZE_4BIT", "0").lower() in {"1", "true", "yes", "on"},
        help="Enable 4-bit quantization (GPU)",
    )
    run_cmd.add_argument("--prompt", help="Run a single prompt non-interactively", default=None)

    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        return

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

    if args.prompt:
        prompt = _build_prompt(args.system, args.prompt)
        result = llm.generate(prompt)
        print(f"\n{result}\n")
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
        prompt = _build_prompt(args.system, user_request)
        result = llm.generate(prompt)
        print(f"\n{result}\n")


def _build_prompt(system_prompt: str, user_request: str) -> str:
    if system_prompt:
        return f"{system_prompt}\n\nUser: {user_request}\nAssistant:"
    return f"User: {user_request}\nAssistant:"


if __name__ == "__main__":
    main()
