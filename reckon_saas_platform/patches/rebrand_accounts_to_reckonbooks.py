"""Show the Accounts module as ReckonBooks: its name and description, and the bundle plans' feature row."""

import frappe

DESCRIPTION = (
    "Complete Accounting, Sales, Purchase, Inventory & Stock management software for your business. "
    "Invoices, bills, payments, inventory and Tally-style books in Bangla and English."
)


def execute():
    if frappe.db.exists("SaaS Module", "accounts"):
        frappe.db.set_value("SaaS Module", "accounts", {"module_name": "ReckonBooks", "description": DESCRIPTION})
    frappe.db.sql("update `tabSaaS Plan Feature` set feature = 'ReckonBooks' where feature = 'Reckon Accounts'")
    frappe.clear_cache()
