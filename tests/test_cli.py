from __future__ import annotations

import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from lilbot.cli import main
from lilbot.model.base import BaseModel


class FakeModel(BaseModel):
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.runtime_summary = "Loaded fake model on cpu"
        self.load_warnings: list[str] = []
        self.device = "cpu"
        self.quantization_active = False
        self.model_name = "fake-model"

    def generate(self, prompt: str) -> str:
        del prompt
        return self.outputs.pop(0)


class CliTests(unittest.TestCase):
    def test_one_shot_query_still_works(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("lilbot.cli.build_model", return_value=FakeModel(["FINAL: Ready."])),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main(["what is lilbot?"])

        self.assertIn("Ready.", stdout.getvalue())
        self.assertIn("Loaded fake model on cpu", stderr.getvalue())

    def test_no_args_starts_interactive_loop(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch(
                "lilbot.cli.build_model",
                return_value=FakeModel(["THOUGHT: answer\nFINAL: Lilbot is ready."]),
            ),
            patch("builtins.input", side_effect=["what is lilbot?", "exit"]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main([])

        text = stdout.getvalue()
        self.assertIn("Lilbot interactive mode", text)
        self.assertIn("Lilbot is ready.", text)
        self.assertIn("Leaving Lilbot.", text)
        self.assertIn("Loaded fake model on cpu", stderr.getvalue())

    def test_interactive_slash_commands_show_help_and_status(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch("lilbot.cli.build_model", return_value=FakeModel([])),
            patch("builtins.input", side_effect=["/help", "/status", "exit"]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            main([])

        text = stdout.getvalue()
        self.assertIn("Interactive commands:", text)
        self.assertIn("Workspace:", text)
        self.assertIn("Conversation turns: 0", text)

    def test_doctor_command_prints_report(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            main(["doctor"])

        text = stdout.getvalue()
        self.assertIn("Lilbot doctor", text)
        self.assertIn("Configuration", text)
        self.assertIn("Next steps", text)

    def test_init_command_writes_user_config(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "config.json"
            with (
                patch.dict(os.environ, {"LILBOT_CONFIG_PATH": str(config_path)}, clear=True),
                patch("builtins.input", side_effect=["", "none", "cpu", "", "", ""]),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                main(["init"])

            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["device"], "cpu")
            self.assertFalse(saved["quantize_4bit"])
            self.assertIn("workspace_root", saved)
            self.assertIn("Saved Lilbot config", stdout.getvalue())
