"""What a company admin can choose for a person in each module.

A module may list its own choices under ``team_roles`` in its ``reckon_saas_modules`` definition
(``[{"label": ..., "role_profile": ..., "module_role": ...}]``); these are the defaults for the modules
Reckon ships. A choice names a role profile (and, for HR, a module role); the server turns the label the
browser sends into those values, so the browser never says which roles to grant.
"""

from __future__ import annotations


def _choice(label: str, role_profile: str = "Company Manager", module_role: str = "") -> dict:
    return {"label": label, "role_profile": role_profile, "module_role": module_role}


DEFAULT_TEAM_ROLES = {
    "accounts": [
        _choice("Manager"), _choice("Accountant", "Accountant"), _choice("Sales", "Sales User"),
        _choice("Purchase", "Purchase User"), _choice("Stock", "Stock User"),
    ],
    "sales_agent": [_choice("Manager"), _choice("Sales", "Sales User")],
    "crm": [_choice("Manager")],
    "hrms": [
        _choice("HR Manager", "Company Manager", "HR Manager"), _choice("Payroll Manager", "Company Manager", "Payroll Manager"),
        _choice("Talent Admin", "Company Manager", "Talent Admin"), _choice("Employee Self Service", "Company Manager", "Employee Self Service"),
    ],
    "distribution": [
        _choice("Manager"), _choice("Master Data Manager", "Master Data Manager"), _choice("SR", "SR"), _choice("DSR", "DSR"),
    ],
}
FALLBACK_CHOICES = [_choice("Manager")]


def choices_for(module: dict) -> list[dict]:
    """The role choices of a module: its own definition first, then the built-in list, then one generic choice."""
    return list(module.get("team_roles") or DEFAULT_TEAM_ROLES.get(module.get("key")) or FALLBACK_CHOICES)
