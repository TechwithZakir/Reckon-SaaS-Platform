"""ReckonERP plans: name what ReckonBooks covers, and show CRM as an add-on and asset and project management as coming soon."""

import frappe

BOOKS = "ReckonBooks (accounting, sales, purchase, inventory and stock)"
NEW_ROWS = (("Reckon CRM", 1, "Add as a module"), ("Asset and project management", 1, "Coming soon"))


def execute():
    for plan in frappe.get_all("SaaS Plan", filters={"name": ["like", "ReckonERP%"]}, pluck="name"):
        frappe.db.sql(
            "update `tabSaaS Plan Feature` set feature = %s where parent = %s and feature = 'ReckonBooks'", (BOOKS, plan)
        )
        if frappe.db.exists("SaaS Plan Feature", {"parent": plan, "feature": "Reckon CRM"}):
            continue
        anchor = frappe.db.get_value("SaaS Plan Feature", {"parent": plan, "feature": "Reckon Sales AI Agent"}, "idx")
        if not anchor:
            continue
        frappe.db.sql("update `tabSaaS Plan Feature` set idx = idx + %s where parent = %s and idx > %s", (len(NEW_ROWS), plan, anchor))
        for offset, (feature, included, value) in enumerate(NEW_ROWS, start=1):
            frappe.get_doc({
                "doctype": "SaaS Plan Feature", "parent": plan, "parenttype": "SaaS Plan", "parentfield": "comparison_features",
                "idx": anchor + offset, "feature": feature, "included": included, "value": value,
            }).insert(ignore_permissions=True)
    frappe.clear_cache()
