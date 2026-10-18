from __future__ import annotations

import frappe
from frappe.utils import cint


def execute() -> None:
    """Give existing subscriptions their plan's grace days.

    SaaS Plan had Trial Days and Grace Days fields before anything used them.
    Subscriptions now carry their own copy, so a vendor's grace setting applies
    to tenants who signed up earlier. Trials are not back-dated.
    """
    if not frappe.db.has_column("SaaS Subscription", "grace_days"):
        return
    grace_by_plan = {
        row.name: cint(row.grace_days)
        for row in frappe.get_all("SaaS Plan", fields=["name", "grace_days"])
        if cint(row.grace_days) > 0
    }
    if not grace_by_plan:
        return
    for row in frappe.get_all(
        "SaaS Subscription",
        filters={"plan": ["in", list(grace_by_plan)], "grace_days": ["in", [0, None]]},
        fields=["name", "plan"],
    ):
        frappe.db.set_value(
            "SaaS Subscription", row.name, "grace_days", grace_by_plan[row.plan], update_modified=False
        )
