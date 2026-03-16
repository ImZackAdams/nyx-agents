"""Read-only shell inspection tools."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import subprocess

from lilbot.utils.config import LilbotConfig


SAFE_COMMANDS = {
    "df",
    "dmesg",
    "free",
    "git",
    "ip",
    "iostat",
    "journalctl",
    "lsblk",
    "lscpu",
    "mount",
    "netstat",
    "ps",
    "pwd",
    "ss",
    "top",
    "uname",
    "uptime",
    "vmstat",
    "whoami",
}
SAFE_GIT_SUBCOMMANDS = {"branch", "diff", "log", "rev-parse", "show", "status"}
BLOCKED_SUBSTRINGS = ("&&", "||", ";", "|", ">", "<", "\n", "`", "$(")


def run_shell(config: LilbotConfig, command: str) -> str:
    """Run a read-only, allowlisted shell command."""

    rendered = str(command or "").strip()
    if not rendered:
        return "No shell command was provided."
    if any(token in rendered for token in BLOCKED_SUBSTRINGS):
        return (
            "Blocked shell command: shell metacharacters and pipes are not allowed. "
            "Use a single safe command, or prefer inspect_system for performance diagnosis."
        )

    try:
        parts = shlex.split(rendered)
    except ValueError as exc:
        return f"Invalid shell command: {exc}"

    if not parts:
        return "No shell command was provided."

    program = parts[0]
    if program not in SAFE_COMMANDS:
        return f"Blocked shell command: `{program}` is not in the safe allowlist."
    if program == "git" and len(parts) > 1 and parts[1] not in SAFE_GIT_SUBCOMMANDS:
        return f"Blocked shell command: `git {parts[1]}` is not allowed."
    if program == "top" and "-b" not in parts:
        return "Blocked shell command: use `top -b -n 1` for non-interactive output."

    try:
        completed = subprocess.run(
            parts,
            cwd=str(config.workspace_root),
            capture_output=True,
            text=True,
            timeout=config.shell_timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return f"Shell command not found: {program}"
    except subprocess.TimeoutExpired:
        return f"Shell command timed out after {config.shell_timeout_seconds} seconds."
    except OSError as exc:
        return f"Shell command failed: {exc}"

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    chunks = []
    if stdout:
        chunks.append(stdout)
    if stderr:
        chunks.append(f"[stderr]\n{stderr}")
    output = "\n".join(chunks).strip() or "(no output)"
    if len(output) > config.shell_max_output_chars:
        output = output[: config.shell_max_output_chars] + "\n... (truncated)"

    return (
        f"Shell command: {rendered}\n"
        f"Exit code: {completed.returncode}\n"
        f"Output:\n{output}"
    )


def inspect_system(config: LilbotConfig) -> str:
    """Gather a deterministic local performance snapshot without using shell pipelines."""

    lines = ["System inspection snapshot:"]

    load_averages = _load_averages()
    if load_averages is not None:
        lines.append(
            "- load_average: "
            f"1m={load_averages[0]:.2f}, 5m={load_averages[1]:.2f}, 15m={load_averages[2]:.2f}"
        )

    cpu_count = os.cpu_count()
    if cpu_count is not None:
        lines.append(f"- logical_cpus: {cpu_count}")

    uptime_seconds = _uptime_seconds()
    if uptime_seconds is not None:
        lines.append(f"- uptime: {_format_duration(uptime_seconds)}")

    meminfo = _read_meminfo()
    if meminfo:
        total_kb = meminfo.get("MemTotal", 0)
        available_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        used_kb = max(total_kb - available_kb, 0)
        if total_kb > 0:
            lines.append(
                "- memory: "
                f"used={_format_bytes(used_kb * 1024)} / total={_format_bytes(total_kb * 1024)} "
                f"({used_kb / total_kb * 100:.1f}% used)"
            )

        swap_total_kb = meminfo.get("SwapTotal", 0)
        swap_free_kb = meminfo.get("SwapFree", 0)
        if swap_total_kb > 0:
            swap_used_kb = max(swap_total_kb - swap_free_kb, 0)
            lines.append(
                "- swap: "
                f"used={_format_bytes(swap_used_kb * 1024)} / total={_format_bytes(swap_total_kb * 1024)} "
                f"({swap_used_kb / swap_total_kb * 100:.1f}% used)"
            )

    lines.extend(_disk_usage_lines(config))
    lines.extend(_process_table_lines(config, sort_key="-%cpu", label="top_cpu_processes"))
    lines.extend(_process_table_lines(config, sort_key="-%mem", label="top_memory_processes"))

    return "\n".join(lines)


def _load_averages() -> tuple[float, float, float] | None:
    try:
        return os.getloadavg()
    except (AttributeError, OSError):
        return None


def _uptime_seconds() -> float | None:
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as handle:
            first_token = handle.read().split()[0]
    except OSError:
        return None

    try:
        return float(first_token)
    except ValueError:
        return None


def _read_meminfo() -> dict[str, int]:
    info: dict[str, int] = {}
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for raw_line in handle:
                if ":" not in raw_line:
                    continue
                key, value = raw_line.split(":", 1)
                amount = value.strip().split()[0]
                try:
                    info[key] = int(amount)
                except ValueError:
                    continue
    except OSError:
        return {}
    return info


def _disk_usage_lines(config: LilbotConfig) -> list[str]:
    candidates = [config.workspace_root, Path("/")]
    lines: list[str] = []
    seen: set[Path] = set()

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        try:
            usage = shutil.disk_usage(resolved)
        except OSError:
            continue
        used = usage.total - usage.free
        percent = (used / usage.total * 100.0) if usage.total else 0.0
        label = "workspace_disk" if resolved == config.workspace_root else f"disk_{resolved}"
        lines.append(
            f"- {label}: used={_format_bytes(used)} / total={_format_bytes(usage.total)} ({percent:.1f}% used)"
        )

    return lines


def _process_table_lines(
    config: LilbotConfig,
    *,
    sort_key: str,
    label: str,
    limit: int = 5,
) -> list[str]:
    try:
        completed = subprocess.run(
            [
                "ps",
                "-eo",
                "pid=,comm=,%cpu=,%mem=",
                f"--sort={sort_key}",
            ],
            capture_output=True,
            text=True,
            timeout=config.shell_timeout_seconds,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return []

    if completed.returncode != 0:
        return []

    rows = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not rows:
        return []

    lines = [f"- {label}:"]
    for row in rows[:limit]:
        parts = row.split(None, 3)
        if len(parts) != 4:
            lines.append(f"  {row}")
            continue
        pid, command, cpu_percent, mem_percent = parts
        lines.append(
            f"  pid={pid} command={command} cpu={cpu_percent}% mem={mem_percent}%"
        )
    return lines


def _format_bytes(value: int) -> str:
    suffixes = ("B", "KiB", "MiB", "GiB", "TiB")
    size = float(value)
    for suffix in suffixes:
        if size < 1024.0 or suffix == suffixes[-1]:
            return f"{size:.1f}{suffix}"
        size /= 1024.0
    return f"{size:.1f}TiB"


def _format_duration(total_seconds: float) -> str:
    seconds = int(total_seconds)
    days, remainder = divmod(seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, seconds = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or parts:
        parts.append(f"{hours}h")
    if minutes or parts:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


TOOL_DEFINITIONS = [
    {
        "name": "inspect_system",
        "description": (
            "Gather a deterministic performance snapshot with load average, memory usage, disk usage, "
            "and top CPU and memory processes. Prefer this for 'system is slow' questions."
        ),
        "parameters": {},
        "function": inspect_system,
    },
    {
        "name": "run_shell",
        "description": (
            "Run a read-only allowlisted shell command for local inspection. "
            "Use a single command only: no pipes, redirects, or shell operators."
        ),
        "parameters": {
            "command": "A single safe shell command such as `df -h` or `ps aux`.",
        },
        "function": run_shell,
    }
]
