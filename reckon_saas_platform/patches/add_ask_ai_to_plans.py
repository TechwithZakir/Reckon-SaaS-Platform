import frappe

from reckon_saas_platform.paddle import ensure_ask_ai_feature


def execute():
    """Add Ask AI (Aura AI agentic support) to the feature list of every existing plan."""
    for name in frappe.get_all("SaaS Plan", pluck="name"):
        doc = frappe.get_doc("SaaS Plan", name)
        before = doc.features
        ensure_ask_ai_feature(doc)
        if doc.features != before:
            frappe.db.set_value("SaaS Plan", name, "features", doc.features, update_modified=False)
    frappe.clear_cache()
