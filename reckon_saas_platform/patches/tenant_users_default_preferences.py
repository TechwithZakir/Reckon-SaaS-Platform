"""Switch the standard list, form and report preferences on for every existing tenant user."""

import frappe

from reckon_saas_platform.team import apply_default_preferences


def execute():
    for user in {row.user for row in frappe.get_all("Tenant User Assignment", fields=["user"]) if row.user}:
        if user not in {"Administrator", "Guest"}:
            apply_default_preferences(user)
