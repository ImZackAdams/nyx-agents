"""Deterministic operational planning engine."""

from __future__ import annotations

from collections.abc import Sequence
import re

from lilbot.ops.models import ChangePlan, RunbookRecord, StandardsRecord, TicketRecord


def build_change_plan(
    ticket: TicketRecord,
    *,
    runbooks: Sequence[RunbookRecord] = (),
    standards: Sequence[StandardsRecord] = (),
) -> ChangePlan:
    operation = ticket.operation_type.strip() or "General Request"
    lowered = operation.lower()
    standard_values = _merged_standard_attributes(standards)

    if "new user" in lowered or "provision" in lowered:
        plan = _new_user_plan(ticket, standard_values)
    elif "group access" in lowered or "membership" in lowered:
        plan = _group_access_plan(ticket)
    elif "disable" in lowered or "termination" in lowered:
        plan = _disable_account_plan(ticket)
    elif "password" in lowered and "reset" in lowered:
        plan = _password_reset_plan(ticket)
    elif "azure vm" in lowered or "vm provisioning" in lowered:
        plan = _azure_vm_plan(ticket, standard_values)
    elif "server build" in lowered:
        plan = _server_build_plan(ticket)
    elif "patch" in lowered:
        plan = _patch_window_plan(ticket)
    else:
        plan = _generic_plan(ticket)

    plan.references = _matching_references(operation, runbooks)
    return plan


def render_change_plan(plan: ChangePlan) -> str:
    lines = [
        "CHANGE PLAN",
        "",
        f"Ticket: {plan.ticket_id}",
        f"Operation: {plan.operation_type}",
        f"Summary: {plan.summary}",
        "",
        "Steps:",
    ]
    for index, step in enumerate(plan.steps, start=1):
        lines.append(f"{index}. {step}")

    lines.extend(["", "Risk:"])
    for risk in plan.risks:
        lines.append(f"- {risk}")

    lines.extend(["", "Rollback:"])
    for rollback_step in plan.rollback:
        lines.append(f"- {rollback_step}")

    if plan.required_approvals:
        lines.extend(["", "Required Approvals:"])
        for approval in plan.required_approvals:
            lines.append(f"- {approval}")

    if plan.references:
        lines.extend(["", "References:"])
        for reference in plan.references:
            lines.append(f"- {reference}")

    return "\n".join(lines)


def _new_user_plan(ticket: TicketRecord, standards: dict[str, str]) -> ChangePlan:
    user_label = ticket.user or "requested user"
    default_ou = standards.get("default_ou", "OU=Users,<domain components>")
    steps = [
        "Verify requester identity and HR approval record.",
        f"Create AD user object for {user_label}.",
        f"Place account in the approved OU ({default_ou}).",
        "Assign baseline security groups and MFA policy.",
        "Provision mailbox/license and validate login flow.",
    ]
    if ticket.access_requests:
        steps.append(
            "Grant requested access: " + ", ".join(ticket.access_requests) + "."
        )
    return ChangePlan(
        ticket_id=ticket.ticket_id,
        operation_type=ticket.operation_type,
        summary=f"Provision a new identity for {user_label} with least-privilege access.",
        steps=tuple(steps),
        risks=(
            "Incorrect OU placement may break policy inheritance.",
            "Over-broad group assignment can create excess privilege.",
        ),
        rollback=(
            "Disable the account immediately.",
            "Remove assigned group memberships.",
            "Delete the AD object after retention checks.",
        ),
        required_approvals=("HR approval", "Manager approval", "Security policy validation"),
    )


def _group_access_plan(ticket: TicketRecord) -> ChangePlan:
    subject = ticket.user or "requested user"
    requested_groups = ", ".join(ticket.access_requests) if ticket.access_requests else "requested groups"
    return ChangePlan(
        ticket_id=ticket.ticket_id,
        operation_type=ticket.operation_type,
        summary=f"Apply least-privilege group changes for {subject}.",
        steps=(
            "Validate ticket ownership and business justification.",
            f"Resolve canonical group names for {requested_groups}.",
            "Apply group membership updates with change logging.",
            "Validate effective access and remove temporary elevation.",
        ),
        risks=(
            "Incorrect group mapping may grant unintended access.",
            "Nested group side effects can be difficult to detect quickly.",
        ),
        rollback=(
            "Remove newly assigned group memberships.",
            "Restore previous access baseline from audit records.",
        ),
        required_approvals=("Data owner approval", "Security approval"),
    )


def _disable_account_plan(ticket: TicketRecord) -> ChangePlan:
    user_label = ticket.user or "target account"
    return ChangePlan(
        ticket_id=ticket.ticket_id,
        operation_type=ticket.operation_type,
        summary=f"Disable and secure account lifecycle for {user_label}.",
        steps=(
            "Confirm disablement authorization and retention policy.",
            "Disable AD account and revoke active sessions.",
            "Remove high-risk group memberships and delegated roles.",
            "Archive mailbox/data ownership according to policy.",
        ),
        risks=(
            "Disabling the wrong account can interrupt operations.",
            "Residual delegated access may persist if not reviewed.",
        ),
        rollback=(
            "Re-enable account if request is rolled back.",
            "Restore approved baseline group memberships.",
        ),
        required_approvals=("HR or manager approval", "Service owner confirmation"),
    )


def _password_reset_plan(ticket: TicketRecord) -> ChangePlan:
    user_label = ticket.user or "target account"
    return ChangePlan(
        ticket_id=ticket.ticket_id,
        operation_type=ticket.operation_type,
        summary=f"Perform controlled credential reset for {user_label}.",
        steps=(
            "Validate caller identity with approved verification process.",
            "Reset password and require change at next logon.",
            "Unlock account only if lockout condition has been validated.",
            "Log reset completion and notify requester through approved channel.",
        ),
        risks=(
            "Identity verification gaps may enable unauthorized reset.",
            "Unlocking compromised accounts can reintroduce threat activity.",
        ),
        rollback=(
            "Force another reset and disable account if suspicious activity appears.",
            "Escalate to security incident process when compromise is suspected.",
        ),
        required_approvals=("Service desk verification",),
    )


def _azure_vm_plan(ticket: TicketRecord, standards: dict[str, str]) -> ChangePlan:
    rg = ticket.attributes.get("resource_group") or standards.get("default_resource_group", "IT-Infra")
    vm_name = ticket.attributes.get("vm_name") or "vm-requested"
    return ChangePlan(
        ticket_id=ticket.ticket_id,
        operation_type=ticket.operation_type,
        summary=f"Provision Azure VM {vm_name} in resource group {rg}.",
        steps=(
            "Validate subscription, quota, and naming policy compliance.",
            "Deploy VM from approved image and size baseline.",
            "Attach required network security and monitoring policies.",
            "Handoff credentials and update configuration inventory.",
        ),
        risks=(
            "Incorrect region or SKU selection may violate policy or budget.",
            "Missing baseline security controls can expose workload risk.",
        ),
        rollback=(
            "Deallocate and remove VM resources.",
            "Revoke temporary credentials and clean up access policies.",
        ),
        required_approvals=("Cloud platform approval", "Cost center approval"),
    )


def _server_build_plan(ticket: TicketRecord) -> ChangePlan:
    return ChangePlan(
        ticket_id=ticket.ticket_id,
        operation_type=ticket.operation_type,
        summary="Build server from standard baseline and compliance controls.",
        steps=(
            "Validate approved build request and baseline image selection.",
            "Provision server and apply hardening baseline.",
            "Join domain and register monitoring/backup agents.",
            "Run post-build validation and handoff checklist.",
        ),
        risks=(
            "Baseline drift introduces patching and compliance issues.",
            "Missing monitoring reduces incident detection quality.",
        ),
        rollback=(
            "Decommission server build and revoke issued credentials.",
            "Remove object entries from CMDB/inventory systems.",
        ),
    )


def _patch_window_plan(ticket: TicketRecord) -> ChangePlan:
    return ChangePlan(
        ticket_id=ticket.ticket_id,
        operation_type=ticket.operation_type,
        summary="Execute controlled patch window with rollback guardrails.",
        steps=(
            "Confirm approved maintenance window and impacted systems.",
            "Snapshot/backup critical systems before patching.",
            "Apply patches in phased rings and validate service health.",
            "Document outcomes and unresolved exceptions.",
        ),
        risks=(
            "Unexpected reboot or compatibility regressions may impact service.",
            "Incomplete backup verification weakens rollback confidence.",
        ),
        rollback=(
            "Restore from snapshots/backups for failed systems.",
            "Uninstall problematic patch set where supported.",
        ),
        required_approvals=("Change advisory board approval",),
    )


def _generic_plan(ticket: TicketRecord) -> ChangePlan:
    return ChangePlan(
        ticket_id=ticket.ticket_id,
        operation_type=ticket.operation_type,
        summary="Execute requested operational change with deterministic controls.",
        steps=(
            "Validate request scope and approval chain.",
            "Apply change in a controlled order with logging enabled.",
            "Validate outcome and capture operational evidence.",
        ),
        risks=("Scope ambiguity can introduce unintended side effects.",),
        rollback=("Revert changed objects using pre-change baseline snapshot.",),
    )


def _merged_standard_attributes(standards: Sequence[StandardsRecord]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for record in standards:
        for key, value in record.attributes.items():
            merged[key] = value
    return merged


def _matching_references(operation_type: str, runbooks: Sequence[RunbookRecord]) -> tuple[str, ...]:
    operation_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", operation_type.lower())
        if len(token) > 2
    }
    matches: list[str] = []
    for runbook in runbooks:
        haystack = f"{runbook.title} {runbook.scope}".lower()
        if any(token in haystack for token in operation_tokens):
            source = runbook.source_path or runbook.title
            matches.append(source)
    return tuple(dict.fromkeys(matches))
