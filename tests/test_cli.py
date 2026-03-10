from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from lilbot.cli.main import (
    _build_parser,
    _infer_inline_request,
    _run_llm_request,
    _should_persist_assistant_response,
    ConversationMessage,
    main,
)


class InterruptingLLM:
    runtime_summary = "interrupting llm"
    load_warnings: list[str] = []

    def generate(self, prompt: str, *, on_token=None) -> str:
        del prompt, on_token
        raise KeyboardInterrupt


class CliParsingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.legacy_json_path = os.path.join(self.tempdir.name, "legacy.json")
        self.original_db_path = os.environ.get("LILBOT_MEMORY_DB_PATH")
        self.original_legacy_json_path = os.environ.get("LILBOT_MEMORY_JSON_PATH")
        os.environ["LILBOT_MEMORY_DB_PATH"] = self.db_path
        os.environ["LILBOT_MEMORY_JSON_PATH"] = self.legacy_json_path

    def tearDown(self) -> None:
        if self.original_db_path is None:
            os.environ.pop("LILBOT_MEMORY_DB_PATH", None)
        else:
            os.environ["LILBOT_MEMORY_DB_PATH"] = self.original_db_path

        if self.original_legacy_json_path is None:
            os.environ.pop("LILBOT_MEMORY_JSON_PATH", None)
        else:
            os.environ["LILBOT_MEMORY_JSON_PATH"] = self.original_legacy_json_path

        self.tempdir.cleanup()

    def test_known_prefix_command_is_rewritten_for_inline_usage(self) -> None:
        parser = _build_parser()
        request = _infer_inline_request(parser, "ls", ["-la"])
        self.assertEqual(request, "!ls -la")

    def test_plain_prompt_is_preserved(self) -> None:
        parser = _build_parser()
        request = _infer_inline_request(parser, "summarize", ["this", "repo"])
        self.assertEqual(request, "summarize this repo")

    def test_bang_prefix_is_preserved(self) -> None:
        parser = _build_parser()
        request = _infer_inline_request(parser, "!notes", ["groceries"])
        self.assertEqual(request, "!notes groceries")

    def test_placeholder_assistant_responses_are_not_persisted(self) -> None:
        self.assertFalse(_should_persist_assistant_response("(echo provider) No model configured."))
        self.assertFalse(_should_persist_assistant_response("[]"))
        self.assertFalse(_should_persist_assistant_response("FINAL: hello"))
        self.assertFalse(_should_persist_assistant_response("<|assistant|>\nFINAL: hello"))
        self.assertTrue(_should_persist_assistant_response("real answer"))

    def test_deterministic_agent_request_does_not_initialize_provider(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("lilbot.cli.main.build_provider", side_effect=AssertionError("provider should not load")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(
                [
                    "--backend",
                    "hf",
                    "--model-path",
                    "/tmp/not-used",
                    "--session-id",
                    "cli-direct",
                    "--prompt",
                    "What files are in this project?",
                ]
            )

        self.assertIn("README.md", stdout.getvalue())
        self.assertIn("tool list_files", stderr.getvalue())

    def test_clear_stays_local_in_repl(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("builtins.input", side_effect=["clear", "exit"]),
            patch("lilbot.cli.main.build_provider", side_effect=AssertionError("provider should not load")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["--backend", "hf", "--model-path", "/tmp/not-used", "--session-id", "cli-clear"])

        self.assertIn("\033[2J\033[H", stdout.getvalue())
        self.assertIn("Bye.", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_keyboard_interrupt_during_generation_is_handled_cleanly(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            result = _run_llm_request(
                InterruptingLLM(),
                user_request="hello",
                system_prompt="",
                session_id="cli-interrupt",
                history=[],
                history_limit=8,
                max_steps=2,
                stream=False,
            )

        self.assertIsNone(result)
        self.assertIn("Generation cancelled.", stderr.getvalue())
