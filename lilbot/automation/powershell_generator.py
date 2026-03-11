"""Safe PowerShell template generation for directory operations."""

from __future__ import annotations

from collections.abc import Sequence
import re

from lilbot.ops.models import StandardsRecord, TicketRecord


def generate_powershell_script(
    ticket: TicketRecord,
    *,
    standards: Sequence[StandardsRecord] = (),
) -> str:
    operation = ticket.operation_type.lower()
    settings = _merged_standard_attributes(standards)

    if "new user" in operation or "provision" in operation:
        body = _new_user_body(ticket, settings)
    elif "group access" in operation or "membership" in operation:
        body = _group_access_body(ticket, settings)
    elif "disable" in operation:
        body = _disable_account_body(ticket)
    elif "password" in operation and "reset" in operation:
        body = _password_reset_body(ticket)
    else:
        body = _generic_body(ticket)

    return "\n".join(
        [
            "[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]",
            "param()",
            "",
            "Set-StrictMode -Version Latest",
            "$ErrorActionPreference = 'Stop'",
            "",
            f"$TicketId = \"{_escape_ps(ticket.ticket_id)}\"",
            f"$OperationType = \"{_escape_ps(ticket.operation_type)}\"",
            "",
            "try {",
            *[f"    {line}" for line in body],
            "}",
            "catch {",
            "    Write-Error (\"Ticket {0} failed: {1}\" -f $TicketId, $_.Exception.Message)",
            "    throw",
            "}",
        ]
    )


def _new_user_body(ticket: TicketRecord, settings: dict[str, str]) -> list[str]:
    user = ticket.user or "Requested User"
    sam = _sam_account_name(user, fallback=ticket.ticket_id or "newuser")
    domain = settings.get("upn_domain") or settings.get("ad_domain") or settings.get("domain") or "example.local"
    ou_path = settings.get("default_ou") or _ou_for_department(ticket.department, domain)
    upn = f"{sam}@{domain}"
    groups = _group_names(ticket.access_requests)

    lines = [
        f"$DisplayName = \"{_escape_ps(user)}\"",
        f"$SamAccountName = \"{_escape_ps(sam)}\"",
        f"$UserPrincipalName = \"{_escape_ps(upn)}\"",
        f"$OrganizationalUnit = \"{_escape_ps(ou_path)}\"",
        f"$Department = \"{_escape_ps(ticket.department or 'General')}\"",
        "",
        "if ($PSCmdlet.ShouldProcess($SamAccountName, \"Create AD user and baseline access\")) {",
        "    New-ADUser `",
        "      -Name $DisplayName `",
        "      -SamAccountName $SamAccountName `",
        "      -UserPrincipalName $UserPrincipalName `",
        "      -Department $Department `",
        "      -Path $OrganizationalUnit `",
        "      -Enabled $true `",
        "      -ChangePasswordAtLogon $true `",
        "      -WhatIf:$WhatIfPreference `",
        "      -Confirm:$ConfirmPreference",
    ]
    for group_name in groups:
        lines.extend(
            [
                "",
                "    Add-ADGroupMember `",
                f"      -Identity \"{_escape_ps(group_name)}\" `",
                "      -Members $SamAccountName `",
                "      -WhatIf:$WhatIfPreference `",
                "      -Confirm:$ConfirmPreference",
            ]
        )
    lines.append("}")
    return lines


def _group_access_body(ticket: TicketRecord, settings: dict[str, str]) -> list[str]:
    del settings
    user = ticket.user or "requested.user"
    sam = _sam_account_name(user, fallback=ticket.ticket_id or "requested.user")
    groups = _group_names(ticket.access_requests)
    if not groups:
        groups = ["<Required-Group-Name>"]

    lines = [
        f"$SamAccountName = \"{_escape_ps(sam)}\"",
        "if ($PSCmdlet.ShouldProcess($SamAccountName, \"Apply group membership changes\")) {",
    ]
    for group_name in groups:
        lines.extend(
            [
                "    Add-ADGroupMember `",
                f"      -Identity \"{_escape_ps(group_name)}\" `",
                "      -Members $SamAccountName `",
                "      -WhatIf:$WhatIfPreference `",
                "      -Confirm:$ConfirmPreference",
            ]
        )
    lines.append("}")
    return lines


def _disable_account_body(ticket: TicketRecord) -> list[str]:
    user = ticket.user or "requested.user"
    sam = _sam_account_name(user, fallback=ticket.ticket_id or "requested.user")
    return [
        f"$SamAccountName = \"{_escape_ps(sam)}\"",
        "if ($PSCmdlet.ShouldProcess($SamAccountName, \"Disable AD account\")) {",
        "    Disable-ADAccount -Identity $SamAccountName -WhatIf:$WhatIfPreference -Confirm:$ConfirmPreference",
        "}",
    ]


def _password_reset_body(ticket: TicketRecord) -> list[str]:
    user = ticket.user or "requested.user"
    sam = _sam_account_name(user, fallback=ticket.ticket_id or "requested.user")
    return [
        f"$SamAccountName = \"{_escape_ps(sam)}\"",
        "$TemporaryPassword = Read-Host \"Enter temporary password\" -AsSecureString",
        "if ($PSCmdlet.ShouldProcess($SamAccountName, \"Reset password and require change\")) {",
        "    Set-ADAccountPassword -Identity $SamAccountName -Reset -NewPassword $TemporaryPassword -WhatIf:$WhatIfPreference -Confirm:$ConfirmPreference",
        "    Set-ADUser -Identity $SamAccountName -ChangePasswordAtLogon $true -WhatIf:$WhatIfPreference -Confirm:$ConfirmPreference",
        "}",
    ]


def _generic_body(ticket: TicketRecord) -> list[str]:
    return [
        f"Write-Host \"No operation-specific generator found for: {_escape_ps(ticket.operation_type)}\"",
        f"Write-Host \"Ticket: {_escape_ps(ticket.ticket_id)}\"",
        "Write-Host \"Add operation-specific cmdlets here and keep -WhatIf/-Confirm enabled.\"",
    ]


def _merged_standard_attributes(standards: Sequence[StandardsRecord]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for record in standards:
        for key, value in record.attributes.items():
            merged[key] = value
    return merged


def _sam_account_name(display_name: str, *, fallback: str) -> str:
    words = [token for token in re.findall(r"[A-Za-z0-9]+", display_name) if token]
    if len(words) >= 2:
        return (words[0][0] + words[-1]).lower()[:20]
    if words:
        return words[0].lower()[:20]
    tokens = [token for token in re.findall(r"[A-Za-z0-9]+", fallback) if token]
    if tokens:
        return tokens[0].lower()[:20]
    return "user1"


def _dc_components(domain: str) -> str:
    parts = [part for part in domain.split(".") if part]
    if not parts:
        return "DC=example,DC=local"
    return ",".join(f"DC={part}" for part in parts)


def _ou_for_department(department: str, domain: str) -> str:
    clean_department = department.strip() or "General"
    safe_department = re.sub(r"[^A-Za-z0-9 -]", "", clean_department).strip() or "General"
    return f"OU={safe_department},OU=Users,{_dc_components(domain)}"


def _group_names(access_requests: tuple[str, ...]) -> list[str]:
    names: list[str] = []
    for request in access_requests:
        normalized = re.sub(r"[^A-Za-z0-9]+", "-", request).strip("-")
        if normalized:
            names.append(normalized)
    if not names:
        return []
    return list(dict.fromkeys(names))


def _escape_ps(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')
