from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lilbot.agent import LilbotAgent
from lilbot.config import LilbotConfig
from lilbot.model.base import BaseModel
from lilbot.tools import build_default_tool_registry


class FakeModel(BaseModel):
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.runtime_summary = "Loaded fake model"

    def generate(self, prompt: str) -> str:
        del prompt
        return self.outputs.pop(0)


class AgentLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        (self.workspace / "README.md").write_text("Lilbot prototype\n", encoding="utf-8")
        self.config = LilbotConfig.from_sources(workspace_root=self.tempdir.name)
        self.registry = build_default_tool_registry(self.config)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_controller_exits_on_final(self) -> None:
        agent = LilbotAgent(
            FakeModel(["THOUGHT: answer directly\nFINAL: Lilbot is ready."]),
            self.registry,
            max_steps=3,
        )

        result = agent.answer("what is lilbot?")

        self.assertEqual(result.answer, "Lilbot is ready.")
        self.assertEqual(result.steps, 1)

    def test_controller_handles_malformed_output_safely(self) -> None:
        agent = LilbotAgent(
            FakeModel(["I refuse to follow the protocol"]),
            self.registry,
            max_steps=2,
        )

        result = agent.answer("read the README")

        self.assertIn("malformed output", result.answer)

    def test_controller_runs_tool_then_returns_final(self) -> None:
        agent = LilbotAgent(
            FakeModel(
                [
                    'THOUGHT: inspect the README\nACTION: read_file\nARGS: {"path": "README.md"}',
                    "THOUGHT: summarize\nFINAL: The README identifies this as a Lilbot prototype.",
                ]
            ),
            self.registry,
            max_steps=3,
        )

        result = agent.answer("what is this project?")

        self.assertIn("Lilbot prototype", result.answer)
        self.assertEqual(result.session.actions_taken, ["read_file"])
