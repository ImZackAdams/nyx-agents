"""Typed models for directory operations artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TicketRecord:
    ticket_id: str
    operation_type: str
    requester: str = ""
    user: str = ""
    department: str = ""
    access_requests: tuple[str, ...] = ()
    attributes: dict[str, str] = field(default_factory=dict)
    source_path: str = ""
    raw_text: str = ""


@dataclass(slots=True)
class RunbookRecord:
    title: str
    scope: str = ""
    prerequisites: tuple[str, ...] = ()
    procedure_steps: tuple[str, ...] = ()
    rollback_steps: tuple[str, ...] = ()
    source_path: str = ""


@dataclass(slots=True)
class StandardsRecord:
    domain: str
    rules: tuple[str, ...] = ()
    attributes: dict[str, str] = field(default_factory=dict)
    source_path: str = ""


@dataclass(slots=True)
class ChangePlan:
    ticket_id: str
    operation_type: str
    summary: str
    steps: tuple[str, ...]
    risks: tuple[str, ...]
    rollback: tuple[str, ...]
    required_approvals: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
