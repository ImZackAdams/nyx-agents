from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from lilbot.cli.agent import ConversationMessage, maybe_answer_without_llm, run_agent
from lilbot.tools import ALL_TOOL_DEFS, execute_tool


class FakeLLM:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)

    def generate(self, prompt: str, *, on_token=None) -> str:
        del prompt
        output = self.outputs.pop(0)
        if on_token is not None:
            for chunk in _chunks(output):
                on_token(chunk)
        return output


def _chunks(text: str, size: int = 4) -> list[str]:
    return [text[index:index + size] for index in range(0, len(text), size)]


class AgentLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_workspace_root = os.environ.get("LILBOT_WORKSPACE_ROOT")
        os.environ["LILBOT_WORKSPACE_ROOT"] = self.tempdir.name
        Path(self.tempdir.name, "README.md").write_text("hello from lilbot\n", encoding="utf-8")

    def tearDown(self) -> None:
        if self.original_workspace_root is None:
            os.environ.pop("LILBOT_WORKSPACE_ROOT", None)
        else:
            os.environ["LILBOT_WORKSPACE_ROOT"] = self.original_workspace_root
        self.tempdir.cleanup()

    def test_agent_can_call_tool_then_finalize(self) -> None:
        llm = FakeLLM(
            [
                'TOOL: read_file {"path": "README.md"}',
                "FINAL: The README says hello from lilbot.",
            ]
        )
        history: list[ConversationMessage] = []

        result = run_agent(
            llm,
            user_request="summarize the readme",
            system_prompt="",
            session_id="agent-test",
            history=history,
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertEqual(result, "The README says hello from lilbot.")
        self.assertEqual(history[-2].role, "user")
        self.assertEqual(history[-1].role, "assistant")

    def test_repeated_tool_call_falls_back_to_last_real_observation(self) -> None:
        llm = FakeLLM(
            [
                'TOOL: read_file {"path": "README.md"}',
                'TOOL: read_file {"path": "README.md"}',
            ]
        )

        result = run_agent(
            llm,
            user_request="read the readme twice",
            system_prompt="",
            session_id="agent-test",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("last tool result was", result)
        self.assertIn("hello from lilbot", result)

    def test_direct_workspace_summary_request_bypasses_model(self) -> None:
        result = maybe_answer_without_llm(
            user_request="Summarize the README.md",
            session_id="agent-test",
            history=[],
            history_limit=8,
            tool_executor=execute_tool,
        )

        assert result is not None
        self.assertIn("README.md summary:", result)
        self.assertIn("hello from lilbot", result)

    def test_listing_request_accepts_here_wording(self) -> None:
        result = maybe_answer_without_llm(
            user_request="what files are in here?",
            session_id="agent-test",
            history=[],
            history_limit=8,
            tool_executor=execute_tool,
        )

        assert result is not None
        self.assertIn("Workspace contents:", result)
        self.assertIn("README.md", result)

    def test_directory_reference_phrase_lists_named_directory(self) -> None:
        Path(self.tempdir.name, "docs").mkdir()
        Path(self.tempdir.name, "docs", "guide.md").write_text("guide\n", encoding="utf-8")

        result = maybe_answer_without_llm(
            user_request="docs directory",
            session_id="agent-test",
            history=[],
            history_limit=8,
            tool_executor=execute_tool,
        )

        assert result is not None
        self.assertIn("Directory contents (docs):", result)
        self.assertIn("guide.md", result)
