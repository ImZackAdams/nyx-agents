from __future__ import annotations

import subprocess
from typing import Any, Dict, Iterable

from lilbot.tools.base_tool import Tool


class ShellCommandTool(Tool):
    name = "shell_command"
    description = "Run a safe shell command from an allowlist"
    input_schema = {"command": "string", "args": "list"}
    risky = True

    def __init__(self, allowed_commands: Iterable[str]) -> None:
        self.allowed_commands = set(allowed_commands)

    def run(self, input_data: Dict[str, Any]) -> Any:
        command = input_data.get("command")
        args = input_data.get("args", [])
        if command not in self.allowed_commands:
            return {"error": f"command not allowed: {command}"}

        result = subprocess.run([command, *args], capture_output=True, text=True, check=False)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
