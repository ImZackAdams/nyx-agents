from __future__ import annotations

import os
import tempfile
import unittest

from lilbot.cli.agent import ConversationMessage, run_agent
from lilbot.memory.memory import save_note, save_session_exchange
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


class AgentRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.legacy_json_path = os.path.join(self.tempdir.name, "legacy.json")
        self.original_db_path = os.environ.get("LILBOT_MEMORY_DB_PATH")
        self.original_legacy_json_path = os.environ.get("LILBOT_MEMORY_JSON_PATH")
        self.original_session_id = os.environ.get("LILBOT_SESSION_ID")
        os.environ["LILBOT_MEMORY_DB_PATH"] = self.db_path
        os.environ["LILBOT_MEMORY_JSON_PATH"] = self.legacy_json_path
        os.environ["LILBOT_SESSION_ID"] = "test-session"

    def tearDown(self) -> None:
        if self.original_db_path is None:
            os.environ.pop("LILBOT_MEMORY_DB_PATH", None)
        else:
            os.environ["LILBOT_MEMORY_DB_PATH"] = self.original_db_path

        if self.original_legacy_json_path is None:
            os.environ.pop("LILBOT_MEMORY_JSON_PATH", None)
        else:
            os.environ["LILBOT_MEMORY_JSON_PATH"] = self.original_legacy_json_path

        if self.original_session_id is None:
            os.environ.pop("LILBOT_SESSION_ID", None)
        else:
            os.environ["LILBOT_SESSION_ID"] = self.original_session_id
        self.tempdir.cleanup()

    def test_falls_back_to_best_note_observation_after_bad_followups(self) -> None:
        save_note("groceries: buy milk and bread")
        llm = FakeLLM(
            [
                'TOOL: search_notes {"query": "groceries", "limit": 1}',
                '[assistant] TOOL: search_history {"query": "whats my name?"}',
                '[assistant] TOOL: search_history {"query": "whats my name?"}',
                '[assistant] TOOL: search_history {"query": "whats my name?"}',
            ]
        )

        result = run_agent(
            llm,
            user_request="what notes do I have about groceries?",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=4,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("Matching notes:", result)
        self.assertIn("groceries: buy milk and bread", result)

    def test_repository_summary_falls_back_to_listing_summary(self) -> None:
        llm = FakeLLM(
            [
                'TOOL: list_files {"path": ".", "max_entries": 50}',
                "FINAL: .env",
            ]
        )

        result = run_agent(
            llm,
            user_request="summarize this repository",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=4,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("Python CLI project", result)
        self.assertIn("lilbot/", result)

    def test_unknown_personal_fact_returns_unknown_without_evidence(self) -> None:
        llm = FakeLLM(["FINAL: Zack"])

        result = run_agent(
            llm,
            user_request="What is my name?",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertEqual(result, "I don't know based on your saved notes or session history.")

    def test_unknown_personal_fact_ignores_prior_hallucinated_history(self) -> None:
        save_session_exchange("test-session", "What is my name?", "Zack")
        llm = FakeLLM(["FINAL: Zack"])

        result = run_agent(
            llm,
            user_request="What is my name?",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertEqual(result, "I don't know based on your saved notes or session history.")

    def test_streams_safe_direct_final_answers(self) -> None:
        llm = FakeLLM(["FINAL: Hello there"])
        chunks: list[str] = []

        result = run_agent(
            llm,
            user_request="Say hello.",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
            token_callback=chunks.append,
        )

        self.assertEqual(result, "Hello there")
        self.assertEqual("".join(chunks), "Hello there")

    def test_streaming_strips_special_tokens_and_protocol_markers(self) -> None:
        llm = FakeLLM(["<|assistant|>\nFINAL: Hello there"])
        chunks: list[str] = []

        result = run_agent(
            llm,
            user_request="Say hello.",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
            token_callback=chunks.append,
        )

        self.assertEqual(result, "Hello there")
        self.assertEqual("".join(chunks), "Hello there")

    def test_repeated_paragraphs_are_collapsed_in_final_answer(self) -> None:
        llm = FakeLLM(
            [
                "FINAL: Hello again! How can I assist you today? If you have any questions, let me know.\n\nHello! How can I assist you today? If you have",
            ]
        )

        result = run_agent(
            llm,
            user_request="hello",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertNotIn("\n\nHello!", result)
        self.assertIn("Hello again!", result)

    def test_tool_protocol_is_not_streamed_to_stdout(self) -> None:
        llm = FakeLLM(
            [
                'TOOL: system_info {}',
                "FINAL: done",
            ]
        )
        chunks: list[str] = []

        result = run_agent(
            llm,
            user_request="show system info then finish",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
            token_callback=chunks.append,
        )

        self.assertEqual(result, "done")
        self.assertEqual(chunks, [])

    def test_prefetched_note_results_replace_model_refusal(self) -> None:
        save_note("buy milk")
        llm = FakeLLM(
            [
                "I'm sorry, but I don't have access to personal notes unless they have been shared with me in this conversation.",
            ]
        )

        result = run_agent(
            llm,
            user_request="What notes do I have?",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("Matching notes:", result)
        self.assertIn("buy milk", result)

    def test_note_listing_request_bypasses_model_generation(self) -> None:
        save_note("buy milk")
        llm = FakeLLM([])

        result = run_agent(
            llm,
            user_request="What notes do I have?",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("Matching notes:", result)
        self.assertIn("buy milk", result)

    def test_matching_notes_are_collapsed_by_text(self) -> None:
        save_note("buy milk")
        save_note("buy milk")
        llm = FakeLLM(
            [
                "I'm sorry, but I don't have access to personal notes unless they have been shared with me in this conversation.",
            ]
        )

        result = run_agent(
            llm,
            user_request="What notes do I have?",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("buy milk (saved 2 times)", result)

    def test_missing_note_matches_collapse_to_deterministic_reply(self) -> None:
        llm = FakeLLM(
            [
                "I'm sorry, but I don't have any saved notes specifically about groceries.",
            ]
        )

        result = run_agent(
            llm,
            user_request="What notes do I have about groceries?",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertEqual(result, "I couldn't find matching notes.")

    def test_prefetched_readme_summary_replaces_model_refusal(self) -> None:
        llm = FakeLLM(
            [
                "I'm unable to directly read files from repositories or the local system.",
            ]
        )

        result = run_agent(
            llm,
            user_request="read the README and summarize the current CLI behavior",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("CLI", result)
        self.assertNotIn("unable to directly", result.lower())

    def test_prefetched_readme_summary_replaces_echo_placeholder(self) -> None:
        llm = FakeLLM(["(echo provider) No model configured."])

        result = run_agent(
            llm,
            user_request="read the README and summarize the current CLI behavior",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("CLI", result)
        self.assertNotIn("echo provider", result.lower())

    def test_nested_final_summary_is_cleaned_or_replaced(self) -> None:
        llm = FakeLLM(
            [
                "FINAL: ` are installed.\n\nFINAL: This repository contains the code for lilbot, a local CLI agent.",
            ]
        )

        result = run_agent(
            llm,
            user_request="summarize this repository",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertNotIn("FINAL:", result)
        self.assertNotIn("` are installed", result)
        self.assertIn("repository", result.lower())

    def test_prefetched_file_listing_replaces_empty_reply(self) -> None:
        llm = FakeLLM([""])

        result = run_agent(
            llm,
            user_request="What files are in this project?",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("README.md", result)
        self.assertIn("lilbot/", result)

    def test_file_listing_request_bypasses_model_generation(self) -> None:
        llm = FakeLLM([])

        result = run_agent(
            llm,
            user_request="What files are in this project?",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("README.md", result)
        self.assertIn("lilbot/", result)

    def test_file_listing_question_prefers_deterministic_listing(self) -> None:
        llm = FakeLLM(
            [
                "The project contains several files including configuration files like `.env` and `.env.example`",
            ]
        )

        result = run_agent(
            llm,
            user_request="What files are in this project?",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("README.md", result)
        self.assertIn("lilbot/", result)

    def test_cli_routing_question_has_direct_answer(self) -> None:
        llm = FakeLLM(["FINAL: nope"])

        result = run_agent(
            llm,
            user_request="explain how this CLI decides whether to run a !command or the LLM?",
            system_prompt="",
            session_id="test-session",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertIn("starts with `!`", result)
        self.assertIn("sent through the LLM agent", result)

    def test_session_id_questions_are_answered_deterministically(self) -> None:
        llm = FakeLLM(["FINAL: nope"])

        result = run_agent(
            llm,
            user_request="what is my session id?",
            system_prompt="",
            session_id="manual-test",
            history=[],
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertEqual(result, "Your current session id is manual-test.")

    def test_last_question_queries_use_recent_session_history(self) -> None:
        llm = FakeLLM(["FINAL: nope"])
        history = [
            ConversationMessage("user", "read the README and summarize the current CLI behavior"),
            ConversationMessage("assistant", "summary"),
            ConversationMessage("user", "What notes do I have?"),
            ConversationMessage("assistant", "Matching notes:\n- buy milk"),
        ]

        result = run_agent(
            llm,
            user_request="What did I just ask you?",
            system_prompt="",
            session_id="manual-test",
            history=history,
            history_limit=8,
            max_steps=2,
            tool_schemas=ALL_TOOL_DEFS,
            tool_executor=execute_tool,
        )

        self.assertEqual(result, 'You just asked: "What notes do I have?"')
