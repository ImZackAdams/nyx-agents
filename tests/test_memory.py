from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from lilbot.memory.memory import (
    load_session_history,
    save_note,
    save_profile_memory,
    save_session_exchange,
    search_notes,
    search_profile_memories,
    search_session_history,
)


def _supports_fts5() -> bool:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
    except sqlite3.OperationalError:
        return False
    finally:
        connection.close()
    return True


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

    def test_profile_singleton_categories_keep_latest_value(self) -> None:
        first = save_profile_memory("name: Zack", "name")
        second = save_profile_memory("name: Zachary", "name")

        results = search_profile_memories("name", limit=5)

        self.assertEqual(first["category"], "name")
        self.assertEqual(second["category"], "name")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "name: Zachary")

    def test_profile_search_returns_saved_preference(self) -> None:
        save_profile_memory("preference: neovim", "preference")

        results = search_profile_memories("neovim", limit=5)

        self.assertTrue(results)
        self.assertEqual(results[0]["text"], "preference: neovim")

    @unittest.skipUnless(_supports_fts5(), "SQLite FTS5 unavailable")
    def test_note_search_reaches_beyond_recent_200_rows(self) -> None:
        save_note("scarletmemorytoken anchor note")
        for index in range(220):
            save_note(f"filler note {index}")

        results = search_notes("scarletmemorytoken", limit=5)

        self.assertTrue(results)
        self.assertEqual(results[0]["text"], "scarletmemorytoken anchor note")

    @unittest.skipUnless(_supports_fts5(), "SQLite FTS5 unavailable")
    def test_session_history_search_reaches_beyond_recent_200_rows(self) -> None:
        save_session_exchange("default", "scarletsessiontoken question", "first answer")
        for index in range(220):
            save_session_exchange("default", f"filler user {index}", f"filler assistant {index}")

        history = search_session_history("default", "scarletsessiontoken", limit=5)

        self.assertTrue(history)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "scarletsessiontoken question")
