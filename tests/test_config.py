from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lilbot.config import LilbotConfig


class UserConfigTests(unittest.TestCase):
    def test_from_sources_loads_user_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "config.json"
            workspace = Path(tempdir) / "workspace"
            workspace.mkdir()
            config_path.write_text(
                json.dumps(
                    {
                        "device": "cpu",
                        "max_new_tokens": 123,
                        "max_steps": 5,
                        "workspace_root": str(workspace),
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"LILBOT_CONFIG_PATH": str(config_path)}, clear=True):
                config = LilbotConfig.from_sources()

            self.assertTrue(config.user_config_loaded)
            self.assertEqual(config.user_config_path, config_path)
            self.assertEqual(config.device, "cpu")
            self.assertEqual(config.max_new_tokens, 123)
            self.assertEqual(config.max_steps, 5)
            self.assertEqual(config.workspace_root, workspace.resolve())

    def test_environment_overrides_user_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = Path(tempdir) / "config.json"
            workspace = Path(tempdir) / "workspace"
            workspace.mkdir()
            config_path.write_text(
                json.dumps(
                    {
                        "device": "cpu",
                        "max_steps": 2,
                        "workspace_root": str(workspace),
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "LILBOT_CONFIG_PATH": str(config_path),
                    "LILBOT_DEVICE": "cuda",
                    "LILBOT_MAX_STEPS": "7",
                },
                clear=True,
            ):
                config = LilbotConfig.from_sources()

            self.assertEqual(config.device, "cuda")
            self.assertEqual(config.max_steps, 7)
