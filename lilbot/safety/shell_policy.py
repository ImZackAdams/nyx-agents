"""Shell safety policy for Lilbot."""

from __future__ import annotations

from dataclasses import dataclass
import re
import shlex


SAFE_COMMANDS = {
    "cat",
    "df",
    "dmesg",
    "du",
    "env",
    "free",
    "git",
    "head",
    "journalctl",
    "ls",
    "lsblk",
    "lscpu",
    "mount",
    "netstat",
    "ps",
    "pwd",
    "ss",
    "stat",
    "tail",
    "top",
    "uname",
    "uptime",
    "vmstat",
    "whoami",
}
SAFE_GIT_SUBCOMMANDS = {"branch", "diff", "log", "rev-parse", "show", "status"}
BLOCKED_SHELL_TOKENS = ("&&", "||", ";", "|", ">", "<", "\n", "`", "$(", "${")
BLOCKED_PATTERNS = (
    re.compile(r":\(\)\s*\{\s*:\|:&\s*;\s*\}\s*;:?"),
    re.compile(r"(^|\s)rm\s+-rf\b"),
    re.compile(r"(^|\s)(?:shutdown|reboot|poweroff)\b"),
    re.compile(r"(^|\s)mkfs\b"),
    re.compile(r"(^|\s)dd\b"),
    re.compile(r"(^|\s)usermod\b"),
    re.compile(r"(^|\s)chown\s+-R\s+/"),
    re.compile(r"(^|\s)chmod\s+-R\s+/"),
    re.compile(r"\bcurl\b.*\|\s*sh\b"),
    re.compile(r"\bwget\b.*\|\s*sh\b"),
    re.compile(r"(^|\s)(?:sudo|su)\b"),
)


@dataclass(frozen=True)
class ShellPolicyDecision:
    """Result of validating a shell command."""

    allowed: bool
    reason: str


class ShellPolicy:
    """Restrict Lilbot shell execution to read-oriented diagnostics."""

    def __init__(self, *, restricted_mode: bool = True) -> None:
        self.restricted_mode = restricted_mode

    def evaluate(self, command: str) -> ShellPolicyDecision:
        rendered = str(command or "").strip()
        if not rendered:
            return ShellPolicyDecision(False, "no shell command was provided")

        if any(token in rendered for token in BLOCKED_SHELL_TOKENS):
            return ShellPolicyDecision(
                False,
                "shell operators, pipes, redirects, and command chaining are not allowed",
            )

        for pattern in BLOCKED_PATTERNS:
            if pattern.search(rendered):
                return ShellPolicyDecision(False, "the command matches a blocked safety rule")

        try:
            parts = shlex.split(rendered)
        except ValueError as exc:
            return ShellPolicyDecision(False, f"invalid shell syntax: {exc}")
        if not parts:
            return ShellPolicyDecision(False, "no shell command was provided")

        program = parts[0]
        if self.restricted_mode and program not in SAFE_COMMANDS:
            return ShellPolicyDecision(
                False,
                f"`{program}` is not in the safe diagnostic allowlist",
            )

        if program == "git" and len(parts) > 1 and parts[1] not in SAFE_GIT_SUBCOMMANDS:
            return ShellPolicyDecision(
                False,
                f"`git {parts[1]}` is not permitted in restricted mode",
            )
        if program == "top" and "-b" not in parts:
            return ShellPolicyDecision(False, "use `top -b -n 1` for non-interactive output")

        return ShellPolicyDecision(True, "allowed")
