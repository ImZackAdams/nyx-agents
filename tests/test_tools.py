from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from lilbot.tools.filesystem import list_directory, read_file
from lilbot.tools.logs import summarize_log
from lilbot.tools.repo import find_function, summarize_repo
from lilbot.tools.shell import inspect_system, run_shell
from lilbot.utils.config import LilbotConfig, discover_default_model_path, is_complete_model_path


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        (self.workspace / "pkg").mkdir()
        (self.workspace / "pkg" / "service.py").write_text(
            "def authenticate_user(name: str) -> bool:\n    return bool(name)\n",
            encoding="utf-8",
        )
        (self.workspace / "README.md").write_text("Lilbot repo summary fixture\n", encoding="utf-8")
        (self.workspace / "system.log").write_text(
            "INFO boot complete\nWARNING almost full\nERROR worker failed\n",
            encoding="utf-8",
        )
        self.config = LilbotConfig.from_sources(workspace_root=self.tempdir.name, verbose_agent=False)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_filesystem_tools_read_and_list_workspace(self) -> None:
        listing = list_directory(self.config, ".")
        preview = read_file(self.config, "README.md")

        self.assertIn("pkg/", listing)
        self.assertIn("README.md", listing)
        self.assertIn("Lilbot repo summary fixture", preview)

    def test_run_shell_blocks_dangerous_commands(self) -> None:
        result = run_shell(self.config, "rm -rf /")

        self.assertIn("Blocked shell command", result)

    def test_run_shell_block_message_mentions_inspect_system(self) -> None:
        result = run_shell(self.config, "top -b -n 1 | head -n 5")

        self.assertIn("inspect_system", result)

    def test_repo_summary_reports_structure(self) -> None:
        result = summarize_repo(self.config, ".")

        self.assertIn("Repository summary for .:", result)
        self.assertIn(".py", result)
        self.assertIn("README.md", result)

    def test_find_function_reports_definitions_and_references(self) -> None:
        result = find_function(self.config, "authenticate_user", ".")

        self.assertIn("definition", result)
        self.assertIn("pkg/service.py:1", result)

    def test_log_summary_counts_errors_and_warnings(self) -> None:
        result = summarize_log(self.config, "system.log")

        self.assertIn("errors: 1", result)
        self.assertIn("warnings: 1", result)

    def test_inspect_system_returns_snapshot_sections(self) -> None:
        result = inspect_system(self.config)

        self.assertIn("System inspection snapshot:", result)
        self.assertIn("memory:", result)
        self.assertIn("workspace_disk:", result)

    def test_default_model_path_discovers_bundled_checkpoint(self) -> None:
        model_path = discover_default_model_path()

        self.assertIsNotNone(model_path)
        assert model_path is not None
        self.assertTrue(is_complete_model_path(model_path))
        self.assertEqual(Path(model_path).name, "falcon3_10b_instruct")
