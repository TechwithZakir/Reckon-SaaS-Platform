"""ReckonERP plans include Reckon CRM; asset and project management are shown as available on request."""

import frappe

ASSETS_ROW = "Asset and project management"


def execute():
    for plan in frappe.get_all("SaaS Plan", filters={"name": ["like", "ReckonERP%"]}, fields=["name", "covered_modules"]):
        modules = [m.strip() for m in (plan.covered_modules or "").replace(",", "\n").splitlines() if m.strip()]
        if "crm" not in modules:
            modules.append("crm")
            frappe.db.set_value("SaaS Plan", plan.name, "covered_modules", "\n".join(modules))
        frappe.db.sql(
            "update `tabSaaS Plan Feature` set included = 1, value = '' where parent = %s and feature = 'Reckon CRM'", plan.name
        )
        frappe.db.sql(
            "update `tabSaaS Plan Feature` set included = 1, value = 'On request' where parent = %s and feature = %s",
            (plan.name, ASSETS_ROW),
        )
    frappe.clear_cache()
