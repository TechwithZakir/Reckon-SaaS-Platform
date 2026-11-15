"""Desk API for the Tenant Scoping Audit page."""

from __future__ import annotations

import frappe

from reckon_saas_platform.tenant_audit import audit_modules


@frappe.whitelist(methods=["GET"])
def get_audit() -> dict:
    """What the Tenant Scoping Audit page shows: per module, how many doctypes tenants can open and which have no scope."""
    frappe.only_for(["Reckon Vendor Superuser", "System Manager"])
    from reckon_saas_platform.module_registry import get_saas_modules

    gaps = audit_modules()
    rows = []
    for module in get_saas_modules():
        key = module.get("key") or module.get("name")
        rows.append({
            "module": module.get("label") or key,
            "key": key,
            "opened": len(module.get("desk_doctypes") or []),
            "reference": len(module.get("desk_reference_doctypes") or []),
            "open": [{"doctype": dt, "why": why} for dt, why in gaps.get(key, [])],
        })
    return {"modules": rows, "total_open": sum(len(r["open"]) for r in rows)}
