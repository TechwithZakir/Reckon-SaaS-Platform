"""Per-company role names for tenant modules. No Frappe import, so the rule is unit-testable."""

from __future__ import annotations

ROLE_KINDS = ("Admin", "User")


def tenant_role_name(prefix: str, kind: str, company: str) -> str:
    """For example tenant_role_name("Reckon HRMS", "Admin", "Acme Ltd") -> "Reckon HRMS Admin - Acme Ltd"."""
    if kind not in ROLE_KINDS:
        raise ValueError(f"unknown tenant role kind: {kind}")
    if not prefix or not company:
        raise ValueError("prefix and company are required")
    return f"{prefix} {kind} - {company}"[:140]


def role_kind_for_profile(role_profile: str | None) -> str:
    """Company Admin gets the admin role; every other profile gets the user role."""
    return "Admin" if role_profile == "Company Admin" else "User"
