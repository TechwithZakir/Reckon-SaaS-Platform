import frappe


def execute():
    """Plans saved before Fill with AI had plan settings get it on, with 20 uses per person per day."""
    for name in frappe.get_all("SaaS Plan", pluck="name"):
        values = frappe.db.get_value("SaaS Plan", name, ["ai_fill_enabled", "ai_fill_daily_limit"], as_dict=True)
        if values.get("ai_fill_enabled") in (None, "") and not values.get("ai_fill_daily_limit"):
            frappe.db.set_value("SaaS Plan", name, {"ai_fill_enabled": 1, "ai_fill_daily_limit": 20}, update_modified=False)
    frappe.clear_cache()
