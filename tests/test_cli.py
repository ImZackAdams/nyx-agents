from __future__ import annotations

import io
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from lilbot.cli.main import main
from lilbot.core.session_store import load_session_history


class FakeLLM:
    runtime_summary = "fake llm"
    load_warnings: list[str] = []

    def __init__(self, output: str) -> None:
        self.output = output

    def generate(self, prompt: str, *, on_token=None) -> str:
        del prompt
        if on_token is not None:
            on_token(self.output)
        return self.output


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_home = os.environ.get("LILBOT_HOME")
        self.original_workspace_root = os.environ.get("LILBOT_WORKSPACE_ROOT")
        os.environ["LILBOT_HOME"] = self.tempdir.name
        os.environ["LILBOT_WORKSPACE_ROOT"] = self.tempdir.name
        Path(self.tempdir.name, "README.md").write_text("workspace file\n", encoding="utf-8")

    def tearDown(self) -> None:
        if self.original_home is None:
            os.environ.pop("LILBOT_HOME", None)
        else:
            os.environ["LILBOT_HOME"] = self.original_home

        if self.original_workspace_root is None:
            os.environ.pop("LILBOT_WORKSPACE_ROOT", None)
        else:
            os.environ["LILBOT_WORKSPACE_ROOT"] = self.original_workspace_root
        self.tempdir.cleanup()

    def test_tools_command_lists_builtin_tools(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            main(["tools"])

        self.assertIn("list_files", stdout.getvalue())
        self.assertIn("write_file", stdout.getvalue())

    def test_inline_prefix_command_does_not_initialize_provider(self) -> None:
        stdout = io.StringIO()

        with (
            patch("lilbot.cli.main.build_provider", side_effect=AssertionError("provider should not load")),
            redirect_stdout(stdout),
        ):
            main(["ls"])

        self.assertIn("README.md", stdout.getvalue())

    def test_workspace_listing_question_bypasses_provider(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("lilbot.cli.main.build_provider", side_effect=AssertionError("provider should not load")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["--session-id", "cli-listing", "run", "what files are in this workspace?"])

        self.assertIn("Workspace contents:", stdout.getvalue())
        self.assertIn("README.md", stdout.getvalue())
        self.assertIn("[tool] list_files", stderr.getvalue())

    def test_short_list_files_prompt_bypasses_provider(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("lilbot.cli.main.build_provider", side_effect=AssertionError("provider should not load")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["run", "list files"])

        self.assertIn("Workspace contents:", stdout.getvalue())
        self.assertIn("README.md", stdout.getvalue())
        self.assertIn("[tool] list_files", stderr.getvalue())

    def test_directory_phrase_bypasses_provider(self) -> None:
        Path(self.tempdir.name, "lilbot").mkdir(exist_ok=True)
        Path(self.tempdir.name, "lilbot", "agent.py").write_text("pass\n", encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("lilbot.cli.main.build_provider", side_effect=AssertionError("provider should not load")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["run", "lilbot directory"])

        self.assertIn("Directory contents (lilbot):", stdout.getvalue())
        self.assertIn("agent.py", stdout.getvalue())
        self.assertIn("[tool] list_files", stderr.getvalue())

    def test_file_summary_question_bypasses_provider(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("lilbot.cli.main.build_provider", side_effect=AssertionError("provider should not load")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["run", "Summarize the README.md"])

        self.assertIn("README.md summary:", stdout.getvalue())
        self.assertIn("workspace file", stdout.getvalue())
        self.assertIn("[tool] read_file", stderr.getvalue())

    def test_system_question_bypasses_provider(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("lilbot.cli.main.build_provider", side_effect=AssertionError("provider should not load")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["run", "What is my system?"])

        self.assertIn("OS:", stdout.getvalue())
        self.assertIn("Python:", stdout.getvalue())
        self.assertIn("[tool] system_info", stderr.getvalue())

    def test_run_command_uses_provider_and_persists_session(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("lilbot.cli.main.build_provider", return_value=FakeLLM("FINAL: minimal reply")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["--session-id", "cli-test", "run", "hello"])

        history = load_session_history("cli-test", limit=10)
        self.assertEqual(
            [(item["role"], item["content"]) for item in history],
            [("user", "hello"), ("assistant", "minimal reply")],
        )
        self.assertIn("minimal reply", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "fake llm\n")

    def test_echo_backend_reports_missing_model(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            main(["--backend", "echo", "run", "hello"])

        self.assertIn("No local model is configured.", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_doctor_reports_session_directory(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            main(["doctor"])

        self.assertIn("Session directory:", stdout.getvalue())
        self.assertIn(self.tempdir.name, stdout.getvalue())
