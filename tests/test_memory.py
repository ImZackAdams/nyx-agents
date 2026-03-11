from __future__ import annotations

import os
import tempfile
import unittest

from lilbot.core.session_store import load_session_history, save_session_exchange, save_session_message


class SessionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_home = os.environ.get("LILBOT_HOME")
        os.environ["LILBOT_HOME"] = self.tempdir.name

    def tearDown(self) -> None:
        if self.original_home is None:
            os.environ.pop("LILBOT_HOME", None)
        else:
            os.environ["LILBOT_HOME"] = self.original_home
        self.tempdir.cleanup()

    def test_save_and_load_exchange(self) -> None:
        save_session_exchange("session-a", "hello", "world")

        history = load_session_history("session-a", limit=10)

        self.assertEqual(
            [(item["role"], item["content"]) for item in history],
            [("user", "hello"), ("assistant", "world")],
        )

    def test_history_limit_keeps_tail(self) -> None:
        save_session_message("session-b", "user", "one")
        save_session_message("session-b", "assistant", "two")
        save_session_message("session-b", "user", "three")

        history = load_session_history("session-b", limit=2)

        self.assertEqual(
            [(item["role"], item["content"]) for item in history],
            [("assistant", "two"), ("user", "three")],
        )
