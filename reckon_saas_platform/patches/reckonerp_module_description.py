"""Refresh the ReckonERP suite's stored description (the module record keeps the text it was created with)."""

import frappe

from reckon_saas_platform.suite import get_module_definition


def execute():
    if frappe.db.exists("SaaS Module", "reckonerp"):
        frappe.db.set_value("SaaS Module", "reckonerp", "description", get_module_definition()["description"])
    frappe.clear_cache()
