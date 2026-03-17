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
        return "\n".join(_disk_usage_snapshot_lines(self.config.workspace_root))


class MemoryUsageTool(Tool):
    name = "memory_usage"
    description = "Inspect current memory and swap usage."
    args_schema: dict[str, str] = {}

    def execute(self, **kwargs: object) -> str:
        del kwargs
        return "\n".join(_memory_snapshot_lines())


class CpuSnapshotTool(Tool):
    name = "cpu_snapshot"
    description = "Inspect load average, uptime, and top CPU-consuming processes."
    args_schema: dict[str, str] = {}

    def execute(self, **kwargs: object) -> str:
        del kwargs
        return "\n".join(_cpu_snapshot_lines(self.config.shell_timeout_seconds))


class InspectSystemTool(Tool):
    name = "inspect_system"
    description = (
        "Gather a deterministic performance snapshot with CPU, memory, disk, "
        "and top-process details. Prefer this for slow-system diagnosis."
    )
    args_schema: dict[str, str] = {}

    def execute(self, **kwargs: object) -> str:
        del kwargs
        lines = ["System inspection snapshot:"]
        lines.extend(_system_overview_lines())
        lines.extend(_memory_details_lines())
        lines.extend(_disk_detail_lines(self.config.workspace_root))
        lines.extend(
            _formatted_process_section(
                self.config.shell_timeout_seconds,
                sort_key="-%cpu",
                label="top_cpu_processes",
            )
        )
        lines.extend(
            _formatted_process_section(
                self.config.shell_timeout_seconds,
                sort_key="-%mem",
                label="top_memory_processes",
            )
        )
        return "\n".join(lines)


def _disk_usage_snapshot_lines(workspace_root: Path) -> list[str]:
    lines = ["Disk usage snapshot:"]
    for line in _disk_detail_lines(workspace_root):
        if line.startswith("- workspace_disk:"):
            lines.append(line.replace("- workspace_disk:", "- workspace:", 1))
        elif line.startswith("- root_disk:"):
            lines.append(line.replace("- root_disk:", "- root:", 1))
        else:
            lines.append(line)
    return lines


def _memory_snapshot_lines() -> list[str]:
    detail_lines = _memory_details_lines()
    if detail_lines:
        return ["Memory snapshot:", *detail_lines]
    return ["Memory usage is unavailable on this platform."]


def _cpu_snapshot_lines(timeout_seconds: int) -> list[str]:
    lines = ["CPU snapshot:"]
    lines.extend(_system_overview_lines())

    top_processes = _top_process_rows(timeout_seconds)
    if top_processes:
        lines.append("- top_cpu_processes:")
        for row in top_processes:
            lines.append(f"  {row}")
    return lines


def _system_overview_lines() -> list[str]:
    lines: list[str] = []
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
    return lines


def _memory_details_lines() -> list[str]:
    meminfo = _read_meminfo()
    if not meminfo:
        return []

    lines: list[str] = []
    total_kb = meminfo.get("MemTotal", 0)
    available_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    used_kb = max(total_kb - available_kb, 0)
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
    return lines


def _disk_detail_lines(workspace_root: Path) -> list[str]:
    lines: list[str] = []
    seen: set[Path] = set()
    for candidate, label in (
        (workspace_root, "workspace_disk"),
        (Path("/"), "root_disk"),
    ):
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate

        if resolved in seen:
            continue
        seen.add(resolved)

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
    return lines


def _formatted_process_section(
    timeout_seconds: int,
    *,
    sort_key: str,
    label: str,
    limit: int = 5,
) -> list[str]:
    rows = _ps_rows(timeout_seconds, sort_key=sort_key, limit=limit)
    if not rows:
        return []

    lines = [f"- {label}:"]
    for pid, command, cpu_percent, mem_percent in rows:
        lines.append(
            f"  pid={pid} command={command} cpu={cpu_percent}% mem={mem_percent}%"
        )
    return lines


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
    rows = _ps_rows(timeout_seconds, sort_key="-%cpu", limit=limit)
    return [f"{pid} {command} {cpu_percent} {mem_percent}" for pid, command, cpu_percent, mem_percent in rows]


def _ps_rows(
    timeout_seconds: int,
    *,
    sort_key: str,
    limit: int = 5,
) -> list[tuple[str, str, str, str]]:
    try:
        completed = subprocess.run(
            ["ps", "-eo", "pid=,comm=,%cpu=,%mem=", f"--sort={sort_key}"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return []

    if completed.returncode != 0:
        return []

    rows: list[tuple[str, str, str, str]] = []
    for raw_line in completed.stdout.splitlines():
        rendered = raw_line.strip()
        if not rendered:
            continue
        parts = rendered.split(None, 3)
        if len(parts) != 4:
            continue
        rows.append((parts[0], parts[1], parts[2], parts[3]))
        if len(rows) >= limit:
            break
    return rows


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
