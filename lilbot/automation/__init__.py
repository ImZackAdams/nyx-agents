"""Automation template generators for directory operations."""

from lilbot.automation.azure_vm_generator import generate_azure_vm_template
from lilbot.automation.powershell_generator import generate_powershell_script

__all__ = [
    "generate_azure_vm_template",
    "generate_powershell_script",
]
