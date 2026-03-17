"""Safe shell command tool."""

from __future__ import annotations

import shlex
import subprocess

from lilbot.safety.shell_policy import ShellPolicy
from lilbot.tools.base import Tool
from lilbot.utils.formatting import truncate_text


class RunShellTool(Tool):
    name = "run_shell"
    description = (
        "Run a read-oriented shell command in restricted mode. "
        "No pipes, redirects, or mutating commands are allowed."
    )
    args_schema = {"command": "A single safe diagnostic command such as `df -h` or `git status`."}

    def __init__(self, config) -> None:
        super().__init__(config)
        self.policy = ShellPolicy(restricted_mode=True)

    def execute(self, **kwargs: object) -> str:
        command = str(kwargs.get("command", "")).strip()
        decision = self.policy.evaluate(command)
        if not decision.allowed:
            return f"Blocked shell command: {decision.reason}"

        parts = shlex.split(command)
        program = parts[0]

        try:
            completed = subprocess.run(
                parts,
                cwd=str(self.config.workspace_root),
                capture_output=True,
                text=True,
                timeout=self.config.shell_timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            return f"Shell command not found: {program}"
        except subprocess.TimeoutExpired:
            return f"Shell command timed out after {self.config.shell_timeout_seconds} seconds."
        except OSError as exc:
            return f"Shell command failed: {exc}"

        chunks: list[str] = []
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if stdout:
            chunks.append(stdout)
        if stderr:
            chunks.append(f"[stderr]\n{stderr}")

        output = "\n".join(chunks).strip() or "(no output)"
        output = truncate_text(output, self.config.shell_max_output_chars)
        return (
            f"Shell command: {command}\n"
            f"Exit code: {completed.returncode}\n"
            f"Output:\n{output}"
        )
