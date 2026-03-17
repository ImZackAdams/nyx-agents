from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from lilbot.cli import main
from lilbot.model.base import BaseModel


class FakeModel(BaseModel):
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.runtime_summary = "Loaded fake model on cpu"

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
