"""Load workspace artifacts with deterministic local I/O."""

from __future__ import annotations

from pathlib import Path
import re

from lilbot.workspace.vault_indexer import WorkspaceIndex, find_ticket_path, index_workspace


TICKET_HEADER_PATTERN = re.compile(r"^\s*Ticket\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def read_text_artifact(path: str | Path) -> str:
    artifact_path = Path(path).expanduser().resolve()
    with artifact_path.open("r", encoding="utf-8") as handle:
        return handle.read()


def load_ticket_text(ticket_id: str, *, ops_root: str | Path | None = None) -> tuple[Path, str]:
    index = index_workspace(ops_root)
    path = find_ticket_path(ticket_id, index)
    if path is not None:
        return path, read_text_artifact(path)

    normalized_ticket = ticket_id.strip().lower().replace("ticket", "").strip(" :-_#")
    if not normalized_ticket:
        raise FileNotFoundError("Ticket id cannot be empty.")

    content_match = _find_ticket_by_header(index, normalized_ticket)
    if content_match is not None:
        return content_match
    raise FileNotFoundError(f"Ticket not found: {ticket_id}")


def _find_ticket_by_header(index: WorkspaceIndex, normalized_ticket: str) -> tuple[Path, str] | None:
    for path in index.tickets:
        text = read_text_artifact(path)
        match = TICKET_HEADER_PATTERN.search(text)
        if match is None:
            continue
        candidate = match.group(1).strip().lower().replace("#", "").strip(" :-_")
        if candidate == normalized_ticket:
            return path, text
    return None
