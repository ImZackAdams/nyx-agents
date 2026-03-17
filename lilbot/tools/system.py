"""Deterministic system inspection tools."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

from lilbot.tools.base import Tool


class DiskUsageTool(Tool):
    name = "disk_usage"
    description = "Inspect workspace and root filesystem usage."
    args_schema: dict[str, str] = {}

    def execute(self, **kwargs: object) -> str:
        del kwargs
        lines = ["Disk usage snapshot:"]
        for candidate, label in (
            (self.config.workspace_root, "workspace"),
            (Path("/"), "root"),
        ):
            try:
                usage = shutil.disk_usage(candidate)
            except OSError as exc:
                lines.append(f"- {label}: unavailable ({exc})")
                continue
            used = usage.total - usage.free
            percent = (used / usage.total * 100.0) if usage.total else 0.0
            lines.append(
                f"- {label}: used={_format_bytes(used)} / total={_format_bytes(usage.total)} "
                f"({percent:.1f}% used)"
            )
        return "\n".join(lines)


class MemoryUsageTool(Tool):
    name = "memory_usage"
    description = "Inspect current memory and swap usage."
    args_schema: dict[str, str] = {}

    def execute(self, **kwargs: object) -> str:
        del kwargs
        meminfo = _read_meminfo()
        if not meminfo:
            return "Memory usage is unavailable on this platform."

        total_kb = meminfo.get("MemTotal", 0)
        available_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        used_kb = max(total_kb - available_kb, 0)
        lines = ["Memory snapshot:"]
        if total_kb > 0:
            lines.append(
                f"- memory: used={_format_bytes(used_kb * 1024)} / total={_format_bytes(total_kb * 1024)} "
                f"({used_kb / total_kb * 100:.1f}% used)"
            )

        swap_total_kb = meminfo.get("SwapTotal", 0)
        swap_free_kb = meminfo.get("SwapFree", 0)
        if swap_total_kb > 0:
            swap_used_kb = max(swap_total_kb - swap_free_kb, 0)
            lines.append(
                f"- swap: used={_format_bytes(swap_used_kb * 1024)} / total={_format_bytes(swap_total_kb * 1024)} "
                f"({swap_used_kb / swap_total_kb * 100:.1f}% used)"
            )
        return "\n".join(lines)


class CpuSnapshotTool(Tool):
    name = "cpu_snapshot"
    description = "Inspect load average, uptime, and top CPU-consuming processes."
    args_schema: dict[str, str] = {}

    def execute(self, **kwargs: object) -> str:
        del kwargs
        lines = ["CPU snapshot:"]

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

        top_processes = _top_process_rows(self.config.shell_timeout_seconds)
        if top_processes:
            lines.append("- top_cpu_processes:")
            for row in top_processes:
                lines.append(f"  {row}")
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


def _top_process_rows(timeout_seconds: int, limit: int = 5) -> list[str]:
    try:
        completed = subprocess.run(
            ["ps", "-eo", "pid=,comm=,%cpu=,%mem=", "--sort=-%cpu"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return []

    if completed.returncode != 0:
        return []

    rows = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return rows[:limit]


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
