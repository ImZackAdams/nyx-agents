from __future__ import annotations

import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from lilbot.cli import main


class FakeModel:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.runtime_summary = "Loaded fake model on cuda | max_new_tokens=192 | 4-bit"
        self.load_warnings: list[str] = []

    def generate(self, prompt: str) -> str:
        del prompt
        return self.outputs.pop(0)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        (self.workspace / "README.md").write_text("Lilbot CLI test workspace\n", encoding="utf-8")
        (self.workspace / "example.log").write_text(
            "INFO boot complete\nWARNING disk almost full\nERROR service failed\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_repo_summarize_uses_deterministic_tool(self) -> None:
        stdout = io.StringIO()

        with (
            patch("lilbot.cli.build_model", side_effect=AssertionError("model should not load")),
            redirect_stdout(stdout),
        ):
            main(["--workspace-root", self.tempdir.name, "repo", "summarize", "."])

        self.assertIn("Repository summary for .:", stdout.getvalue())
        self.assertIn("README.md", stdout.getvalue())

    def test_logs_analyze_uses_deterministic_tool(self) -> None:
        stdout = io.StringIO()

        with (
            patch("lilbot.cli.build_model", side_effect=AssertionError("model should not load")),
            redirect_stdout(stdout),
        ):
            main(["--workspace-root", self.tempdir.name, "logs", "analyze", "example.log"])

        self.assertIn("Log summary for", stdout.getvalue())
        self.assertIn("errors: 1", stdout.getvalue())

    def test_freeform_query_uses_agent_and_tools(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        model = FakeModel(
            [
                'THOUGHT: inspect the README\nACTION: {"tool": "read_file", "arguments": {"path": "README.md"}}',
                "THOUGHT: answer the user\nFINAL: The workspace README confirms this is a Lilbot CLI test workspace.",
            ]
        )

        with (
            patch("lilbot.cli.build_model", return_value=model),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["--workspace-root", self.tempdir.name, "what does this workspace contain?"])

        self.assertIn("The workspace README confirms this is a Lilbot CLI test workspace.", stdout.getvalue())
        self.assertIn("Loaded fake model on cuda", stderr.getvalue())
        self.assertIn("[THOUGHT] inspect the README", stderr.getvalue())
        self.assertIn("[ACTION] read_file", stderr.getvalue())

    def test_explain_command_uses_model_without_tools(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        model = FakeModel(
            [
                "THOUGHT: explain the rule\nFINAL: This iptables command allows inbound TCP traffic on port 22.",
            ]
        )

        with (
            patch("lilbot.cli.build_model", return_value=model),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(
                [
                    "--workspace-root",
                    self.tempdir.name,
                    "explain-command",
                    "iptables -A INPUT -p tcp --dport 22 -j ACCEPT",
                ]
            )

        self.assertIn("allows inbound TCP traffic on port 22", stdout.getvalue())
        self.assertIn("Loaded fake model on cuda", stderr.getvalue())
        self.assertIn("[THOUGHT] explain the rule", stderr.getvalue())
