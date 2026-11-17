import frappe


def execute():
    """The assistant is called Aura AI Assistance: update published articles that say Aura AI Assistant."""
    if not frappe.db.exists("DocType", "SEO Article"):
        return
    for name, body in frappe.get_all("SEO Article", fields=["name", "body"], as_list=True):
        if body and "Aura AI Assistant" in body:
            frappe.db.set_value("SEO Article", name, "body", body.replace("Aura AI Assistant", "Aura AI Assistance"), update_modified=False)
    frappe.clear_cache()
