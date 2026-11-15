"""Every tenant user's Company permission is the default, applies to all doctypes, and sets their default Company."""

import frappe

from reckon_saas_platform.team import sync_company_permission


def execute():
    rows = frappe.get_all("Tenant User Assignment", filters={"active": 1}, fields=["user", "company"])
    companies: dict[str, set[str]] = {}
    for row in rows:
        if row.user and row.company:
            companies.setdefault(row.user, set()).add(row.company)
    for user, owned in companies.items():
        if user in {"Administrator", "Guest"} or not frappe.db.exists("User", user):
            continue
        sync_company_permission(user, sorted(owned))
