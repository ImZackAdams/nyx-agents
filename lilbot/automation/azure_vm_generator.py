"""Safe Azure VM provisioning template generation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from lilbot.ops.models import StandardsRecord, TicketRecord


def generate_azure_vm_template(
    *,
    ticket: TicketRecord | None = None,
    standards: Sequence[StandardsRecord] = (),
    overrides: Mapping[str, str] | None = None,
) -> str:
    settings = _merged_standard_attributes(standards)
    override_values = dict(overrides or {})
    attrs = ticket.attributes if ticket is not None else {}

    resource_group = _pick_value(
        override_values,
        attrs,
        settings,
        ("resource_group", "default_resource_group"),
        default="IT-Infra",
    )
    vm_name = _pick_value(
        override_values,
        attrs,
        settings,
        ("vm_name", "default_vm_name"),
        default="vm-test01",
    )
    location = _pick_value(
        override_values,
        attrs,
        settings,
        ("location", "default_location", "azure_location"),
        default="EastUS",
    )
    image = _pick_value(
        override_values,
        attrs,
        settings,
        ("image", "default_image"),
        default="Win2022Datacenter",
    )
    vm_size = _pick_value(
        override_values,
        attrs,
        settings,
        ("size", "vm_size", "default_vm_size"),
        default="Standard_B2s",
    )
    ticket_id = ticket.ticket_id if ticket is not None else "manual"

    return "\n".join(
        [
            "[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]",
            "param()",
            "",
            "Set-StrictMode -Version Latest",
            "$ErrorActionPreference = 'Stop'",
            "",
            f"$TicketId = \"{_escape_ps(ticket_id)}\"",
            f"$ResourceGroupName = \"{_escape_ps(resource_group)}\"",
            f"$VmName = \"{_escape_ps(vm_name)}\"",
            f"$Location = \"{_escape_ps(location)}\"",
            f"$Image = \"{_escape_ps(image)}\"",
            f"$VmSize = \"{_escape_ps(vm_size)}\"",
            "",
            "try {",
            "    if ($PSCmdlet.ShouldProcess($VmName, \"Provision Azure VM\")) {",
            "        New-AzVM `",
            "          -ResourceGroupName $ResourceGroupName `",
            "          -Name $VmName `",
            "          -Location $Location `",
            "          -Image $Image `",
            "          -Size $VmSize `",
            "          -WhatIf:$WhatIfPreference `",
            "          -Confirm:$ConfirmPreference",
            "    }",
            "}",
            "catch {",
            "    Write-Error (\"Ticket {0} failed: {1}\" -f $TicketId, $_.Exception.Message)",
            "    throw",
            "}",
        ]
    )


def _merged_standard_attributes(standards: Sequence[StandardsRecord]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for record in standards:
        for key, value in record.attributes.items():
            merged[key] = value
    return merged


def _pick_value(
    overrides: Mapping[str, str],
    attrs: Mapping[str, str],
    standards: Mapping[str, str],
    keys: tuple[str, ...],
    *,
    default: str,
) -> str:
    for key in keys:
        value = overrides.get(key) or attrs.get(key) or standards.get(key)
        if value:
            return value
    return default


def _escape_ps(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')
