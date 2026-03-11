"""Directory operations workspace indexing."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from lilbot.tools.filesystem import get_workspace_root


OPS_ROOT_ENV = "LILBOT_OPS_ROOT"
OPS_DIRNAME = "directory_ops"
TICKETS_DIR = "tickets"
RUNBOOKS_DIR = "runbooks"
SCRIPTS_DIR = "scripts"
LOGS_DIR = "logs"
STANDARDS_DIR = "standards"
TEXT_SUFFIXES = frozenset({".md", ".txt", ".rst"})
SCRIPT_SUFFIXES = frozenset({".ps1", ".psm1", ".psd1", ".cmd", ".bat", ".sh"})


@dataclass(frozen=True)
class WorkspaceIndex:
    root: Path
    tickets: tuple[Path, ...]
    runbooks: tuple[Path, ...]
    scripts: tuple[Path, ...]
    logs: tuple[Path, ...]
    standards: tuple[Path, ...]


def resolve_ops_root(ops_root: str | Path | None = None) -> Path | None:
    """Resolve the directory_ops root from explicit value, env, or workspace root."""
    if ops_root is not None and str(ops_root).strip():
        candidate = Path(str(ops_root)).expanduser().resolve()
        return candidate if candidate.is_dir() else None

    configured = os.getenv(OPS_ROOT_ENV, "").strip()
    if configured:
        candidate = Path(configured).expanduser().resolve()
        return candidate if candidate.is_dir() else None

    workspace_root = get_workspace_root()
    if workspace_root.name == OPS_DIRNAME and workspace_root.is_dir():
        return workspace_root

    candidate = workspace_root / OPS_DIRNAME
    if candidate.is_dir():
        return candidate.resolve()
    return None


def index_workspace(ops_root: str | Path | None = None) -> WorkspaceIndex:
    root = resolve_ops_root(ops_root)
    if root is None:
        raise FileNotFoundError(
            "Could not locate directory_ops workspace. "
            "Set LILBOT_OPS_ROOT or create ./directory_ops under the workspace root."
        )

    return WorkspaceIndex(
        root=root,
        tickets=_list_artifacts(root / TICKETS_DIR, TEXT_SUFFIXES),
        runbooks=_list_artifacts(root / RUNBOOKS_DIR, TEXT_SUFFIXES),
        scripts=_list_artifacts(root / SCRIPTS_DIR, SCRIPT_SUFFIXES, include_unknown=True),
        logs=_list_artifacts(root / LOGS_DIR, TEXT_SUFFIXES | SCRIPT_SUFFIXES | {".log", ".json", ".jsonl"}),
        standards=_list_artifacts(root / STANDARDS_DIR, TEXT_SUFFIXES),
    )


def list_ticket_ids(index: WorkspaceIndex) -> list[str]:
    return [path.stem for path in index.tickets]


def find_ticket_path(ticket_id: str, index: WorkspaceIndex) -> Path | None:
    clean_ticket = _normalize_ticket_id(ticket_id)
    if not clean_ticket:
        return None

    for path in index.tickets:
        stem = path.stem.lower()
        if stem == clean_ticket or stem.startswith(f"{clean_ticket}_") or stem.startswith(f"{clean_ticket}-"):
            return path

    for path in index.tickets:
        stem = path.stem.lower()
        if clean_ticket in stem:
            return path
    return None


def _list_artifacts(
    directory: Path,
    allowed_suffixes: frozenset[str],
    *,
    include_unknown: bool = False,
) -> tuple[Path, ...]:
    if not directory.is_dir():
        return ()

    files: list[Path] = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if include_unknown or suffix in allowed_suffixes:
            files.append(path.resolve())
    files.sort(key=lambda item: item.as_posix().lower())
    return tuple(files)


def _normalize_ticket_id(ticket_id: str) -> str:
    return ticket_id.strip().lower().replace("ticket", "").replace("#", "").strip(" :-_")
