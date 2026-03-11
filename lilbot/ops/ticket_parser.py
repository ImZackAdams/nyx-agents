"""Parser for markdown-based operational tickets."""

from __future__ import annotations

from pathlib import Path
import re

from lilbot.ops.models import TicketRecord


FIELD_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 _/-]*)\s*:\s*(.*?)\s*$")
TICKET_ID_PREFIX_PATTERN = re.compile(r"^([A-Za-z0-9]+)")
KEY_ALIASES = {
    "ticket": "ticket_id",
    "ticket_id": "ticket_id",
    "id": "ticket_id",
    "type": "operation_type",
    "operation_type": "operation_type",
    "operation": "operation_type",
    "request_type": "operation_type",
    "requester": "requester",
    "requested_by": "requester",
    "user": "user",
    "username": "user",
    "account": "user",
    "department": "department",
    "business_unit": "department",
    "access_required": "access_required",
    "access_requests": "access_required",
    "access": "access_required",
}


def parse_ticket_file(path: str | Path) -> TicketRecord:
    ticket_path = Path(path).expanduser().resolve()
    text = ticket_path.read_text(encoding="utf-8")
    return parse_ticket_text(text, source_path=ticket_path)


def parse_ticket_text(text: str, *, source_path: str | Path | None = None) -> TicketRecord:
    source = str(source_path or "")
    scalars: dict[str, str] = {
        "ticket_id": "",
        "operation_type": "",
        "requester": "",
        "user": "",
        "department": "",
    }
    attributes: dict[str, str] = {}
    access_requests: list[str] = []

    active_list: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if active_list != "access_required":
                active_list = None
            continue

        list_item = _list_item(stripped)
        if active_list == "access_required" and list_item:
            access_requests.append(list_item)
            continue

        field_match = FIELD_PATTERN.match(line)
        if field_match is None:
            if active_list == "access_required":
                access_requests.append(stripped)
            continue

        key_text = _normalize_key(field_match.group(1))
        value = field_match.group(2).strip()
        canonical_key = KEY_ALIASES.get(key_text, key_text)
        if canonical_key == "access_required":
            active_list = "access_required"
            access_requests.extend(_split_access_value(value))
            continue

        active_list = None
        if canonical_key in scalars:
            scalars[canonical_key] = value
        elif value:
            attributes[canonical_key] = value

    ticket_id = scalars["ticket_id"] or _infer_ticket_id(source_path)
    operation_type = scalars["operation_type"] or _infer_operation_type(text)

    return TicketRecord(
        ticket_id=ticket_id or "unknown",
        operation_type=operation_type or "General Request",
        requester=scalars["requester"],
        user=scalars["user"],
        department=scalars["department"],
        access_requests=tuple(_dedupe_preserving_order(access_requests)),
        attributes=attributes,
        source_path=source,
        raw_text=text,
    )


def _normalize_key(key: str) -> str:
    return "_".join(part for part in re.split(r"[^A-Za-z0-9]+", key.lower()) if part)


def _list_item(stripped: str) -> str:
    if stripped.startswith("- ") or stripped.startswith("* "):
        return stripped[2:].strip()
    return ""


def _split_access_value(value: str) -> list[str]:
    if not value:
        return []
    chunks = [chunk.strip() for chunk in re.split(r"[;,]", value) if chunk.strip()]
    return chunks if chunks else [value.strip()]


def _infer_ticket_id(source_path: str | Path | None) -> str:
    if source_path is None:
        return ""
    stem = Path(source_path).stem
    match = TICKET_ID_PREFIX_PATTERN.match(stem)
    if match is None:
        return ""
    return match.group(1)


def _infer_operation_type(text: str) -> str:
    lowered = text.lower()
    if "new user" in lowered or "provision" in lowered:
        return "New User Provisioning"
    if "group access" in lowered:
        return "Group Access Request"
    if "disable" in lowered:
        return "Account Disablement"
    if "password reset" in lowered:
        return "Password Reset"
    if "patch" in lowered:
        return "Patch Window Planning"
    if "azure vm" in lowered or "new-azvm" in lowered or "vm provisioning" in lowered:
        return "Azure VM Provisioning"
    if "server build" in lowered:
        return "Server Build"
    return ""


def _dedupe_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = " ".join(item.split())
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered
