from __future__ import annotations

import frappe


@frappe.whitelist()
def check_app_permission() -> bool:
    """Show the SaaS Platform app only to vendor and system administrators."""
    user = frappe.session.user
    if user in {"Administrator"}:
        return True
    return bool(
        set(frappe.get_roles(user)).intersection({"System Manager", "Reckon Vendor Superuser"})
    )
