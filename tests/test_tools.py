from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lilbot.config import LilbotConfig
from lilbot.tools import build_default_tool_registry


class ToolRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        (self.workspace / "cli.py").write_text("print('hello')\n", encoding="utf-8")
        (self.workspace / "pkg").mkdir()
        (self.workspace / "pkg" / "service.py").write_text(
            "def authenticate_user(name: str) -> bool:\n    return bool(name)\n",
            encoding="utf-8",
        )
        (self.workspace / "README.md").write_text("Lilbot fixture\n", encoding="utf-8")
        (self.workspace / "app.log").write_text(
            "INFO boot\nWARNING disk nearly full\nERROR worker failed\n",
            encoding="utf-8",
        )
        self.config = LilbotConfig.from_sources(workspace_root=self.tempdir.name)
        self.registry = build_default_tool_registry(self.config)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_registry_exposes_expected_tools(self) -> None:
        self.assertIn("read_file", self.registry.names())
        self.assertIn("inspect_system", self.registry.names())
        self.assertIn("disk_usage", self.registry.names())
        self.assertIn("cpu_snapshot", self.registry.names())

    def test_repo_and_log_tools_return_deterministic_results(self) -> None:
        summary = self.registry.execute("summarize_repo", {"path": "."})
        trace = self.registry.execute("find_function", {"name": "authenticate_user", "path": "."})
        log_summary = self.registry.execute("summarize_log", {"path": "app.log"})

        self.assertIn("Repository summary for .:", summary)
        self.assertIn("likely_entrypoints", summary)
        self.assertIn("pkg/service.py:1", trace)
        self.assertIn("errors: 1", log_summary)
