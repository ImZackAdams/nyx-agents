"""Workspace indexing and artifact loading for directory operations."""

from lilbot.workspace.artifact_loader import load_ticket_text, read_text_artifact
from lilbot.workspace.vault_indexer import (
    WorkspaceIndex,
    find_ticket_path,
    index_workspace,
    resolve_ops_root,
)

__all__ = [
    "WorkspaceIndex",
    "find_ticket_path",
    "index_workspace",
    "load_ticket_text",
    "read_text_artifact",
    "resolve_ops_root",
]
