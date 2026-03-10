from __future__ import annotations

import os
import tempfile
import unittest

from lilbot.memory.memory import load_session_history, save_session_exchange, search_session_history


class SessionHistoryFilteringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "memory.db")
        self.original_db_path = os.environ.get("LILBOT_MEMORY_DB_PATH")
        os.environ["LILBOT_MEMORY_DB_PATH"] = self.db_path

    def tearDown(self) -> None:
        if self.original_db_path is None:
            os.environ.pop("LILBOT_MEMORY_DB_PATH", None)
        else:
            os.environ["LILBOT_MEMORY_DB_PATH"] = self.original_db_path
        self.tempdir.cleanup()

    def test_noise_assistant_messages_are_filtered_with_their_user_turns(self) -> None:
        save_session_exchange("default", "hello", "(echo provider) No model configured.")
        save_session_exchange("default", "test", "[]")
        save_session_exchange("default", "real question", "real answer")

        history = load_session_history("default", limit=20)

        self.assertEqual(
            [(item["role"], item["content"]) for item in history],
            [("user", "real question"), ("assistant", "real answer")],
        )

    def test_noise_messages_do_not_show_up_in_search(self) -> None:
        save_session_exchange("default", "hello", "(echo provider) No model configured.")
        save_session_exchange("default", "real question", "real answer")

        history = search_session_history("default", "hello", limit=10)

        self.assertEqual(history, [])

    def test_protocol_leak_messages_are_filtered(self) -> None:
        save_session_exchange("default", "hello", "<|assistant|>\nFINAL: hello")
        save_session_exchange("default", "real question", "real answer")

        history = load_session_history("default", limit=20)

        self.assertEqual(
            [(item["role"], item["content"]) for item in history],
            [("user", "real question"), ("assistant", "real answer")],
        )
