from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from lilbot.cli.main import (
    _build_parser,
    _infer_inline_request,
    _run_llm_request,
    _should_persist_assistant_response,
    ConversationMessage,
    main,
)
from lilbot.memory.memory import save_profile_memory


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

    def test_default_max_new_tokens_is_large_enough_for_normal_replies(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            parser = _build_parser()
            args = parser.parse_args([])

        self.assertEqual(args.max_new_tokens, 96)

    def test_profile_prefix_command_is_rewritten_for_inline_usage(self) -> None:
        parser = _build_parser()
        request = _infer_inline_request(parser, "profile", ["preferences"])
        self.assertEqual(request, "!profile preferences")

    def test_placeholder_assistant_responses_are_not_persisted(self) -> None:
        self.assertFalse(_should_persist_assistant_response("(echo provider) No model configured."))
        self.assertFalse(_should_persist_assistant_response("[]"))
        self.assertFalse(_should_persist_assistant_response("FINAL: hello"))
        self.assertFalse(_should_persist_assistant_response("<|assistant|>\nFINAL: hello"))
        self.assertFalse(
            _should_persist_assistant_response(
                "No local model is configured yet, so Lilbot can only run deterministic features right now."
            )
        )
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

    def test_profile_summary_request_does_not_initialize_provider(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        save_profile_memory("name: Zack", "name")

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
                    "cli-profile",
                    "--prompt",
                    "What do you know about me?",
                ]
            )

        self.assertIn("What I know about you:", stdout.getvalue())
        self.assertIn("name: Zack", stdout.getvalue())
        self.assertIn("tool search_profile", stderr.getvalue())

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

    def test_echo_backend_prompt_shows_setup_guidance(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            main(["--backend", "echo", "--prompt", "hello"])

        self.assertIn("No local model is configured yet", stdout.getvalue())
        self.assertIn("python -m lilbot doctor", stdout.getvalue())
        self.assertNotIn("(echo provider)", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_doctor_command_reports_setup_details(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch.dict(os.environ, {"LILBOT_HOME": self.tempdir.name}, clear=False),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["doctor"])

        output = stdout.getvalue()
        self.assertIn("Lilbot doctor", output)
        self.assertIn("Dependency check:", output)
        self.assertIn("Default model directory:", output)
        self.assertEqual(stderr.getvalue(), "")

    def test_init_command_creates_env_from_template(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        workspace = Path(self.tempdir.name) / "workspace"
        workspace.mkdir()
        (workspace / ".env.example").write_text("LILBOT_BACKEND=auto\n", encoding="utf-8")
        app_home = Path(self.tempdir.name) / "app-home"

        with (
            patch.dict(os.environ, {"LILBOT_HOME": str(app_home)}, clear=False),
            patch("lilbot.cli.main.Path.cwd", return_value=workspace),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["init"])

        self.assertTrue((workspace / ".env").exists())
        self.assertIn("Lilbot init", stdout.getvalue())
        self.assertIn(str(app_home / "models" / "default"), stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")
