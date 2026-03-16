from __future__ import annotations

import io
from pathlib import Path
import tempfile
import unittest

from lilbot.agent import LilbotAgent
from lilbot.tools import build_tool_registry
from lilbot.utils.config import LilbotConfig
from lilbot.utils.logging import AgentTraceLogger


class FakeModel:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)

    def generate(self, prompt: str) -> str:
        del prompt
        return self.outputs.pop(0)


class FakeToolRegistry:
    def __init__(self, observations: dict[str, str]) -> None:
        self.observations = observations

    def describe(self, allowed_tools=None) -> str:
        del allowed_tools
        return "\n".join(sorted(self.observations))

    def execute(self, name: str, arguments=None) -> str:
        del arguments
        return self.observations[name]


class AgentLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        (self.workspace / "README.md").write_text("Lilbot prototype\n", encoding="utf-8")
        self.config = LilbotConfig.from_sources(
            workspace_root=self.tempdir.name,
            verbose_agent=False,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_agent_calls_tool_then_returns_final_answer(self) -> None:
        model = FakeModel(
            [
                'THOUGHT: inspect the README\nACTION: {"tool": "read_file", "arguments": {"path": "README.md"}}',
                "THOUGHT: summarize the file\nFINAL: The README identifies this as a Lilbot prototype.",
            ]
        )
        trace = io.StringIO()
        agent = LilbotAgent(
            model,
            build_tool_registry(self.config),
            max_steps=2,
            trace_logger=AgentTraceLogger(enabled=True, stream=trace),
        )

        result = agent.answer("What is this project?")

        self.assertEqual(result.answer, "The README identifies this as a Lilbot prototype.")
        self.assertIn("[THOUGHT] inspect the README", trace.getvalue())
        self.assertIn("[ACTION] read_file", trace.getvalue())
        self.assertIn("[OBSERVATION] File preview for ./README.md:", trace.getvalue())

    def test_agent_blocks_repeated_tool_calls(self) -> None:
        model = FakeModel(
            [
                'THOUGHT: read the file\nACTION: {"tool": "read_file", "arguments": {"path": "README.md"}}',
                'THOUGHT: do it again\nACTION: {"tool": "read_file", "arguments": {"path": "README.md"}}',
            ]
        )
        agent = LilbotAgent(model, build_tool_registry(self.config), max_steps=2)

        result = agent.answer("Read the README twice")

        self.assertIn("maximum reasoning step limit", result.answer)
        self.assertIn("Repeated tool call blocked", result.answer)

    def test_slow_system_request_auto_summarizes_after_inspect_system(self) -> None:
        model = FakeModel(
            [
                'THOUGHT: inspect the system\nACTION: {"tool": "inspect_system", "arguments": {}}',
                'THOUGHT: this should not be used\nFINAL: unreachable',
            ]
        )
        tool_registry = FakeToolRegistry(
            {
                "inspect_system": "\n".join(
                    [
                        "System inspection snapshot:",
                        "- load_average: 1m=2.64, 5m=2.88, 15m=2.74",
                        "- logical_cpus: 24",
                        "- memory: used=8.3GiB / total=31.1GiB (26.8% used)",
                        "- swap: used=5.9GiB / total=8.0GiB (74.0% used)",
                        "- workspace_disk: used=746.9GiB / total=914.8GiB (81.6% used)",
                        "- top_cpu_processes:",
                        "  pid=169225 command=Wrath.exe cpu=212% mem=8.0%",
                        "  pid=173155 command=python cpu=109% mem=3.5%",
                        "  pid=172417 command=python cpu=102% mem=12.5%",
                    ]
                )
            }
        )
        agent = LilbotAgent(model, tool_registry, max_steps=4)

        result = agent.answer("why is my system slow?")

        self.assertEqual(result.steps, 1)
        self.assertIn("CPU pressure", result.answer)
        self.assertIn("Wrath.exe", result.answer)
        self.assertIn("Swap usage is elevated", result.answer)
