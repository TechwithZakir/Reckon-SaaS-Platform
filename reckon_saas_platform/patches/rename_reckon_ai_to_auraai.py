import frappe


def execute():
    """The in-ERP assistant is called Aura AI now: update the published articles that still say Reckon AI."""
    if not frappe.db.exists("DocType", "SEO Article"):
        return
    for name, body in frappe.get_all("SEO Article", fields=["name", "body"], as_list=True):
        if body and "Reckon AI" in body:
            frappe.db.set_value("SEO Article", name, "body", body.replace("Reckon AI", "Aura AI"), update_modified=False)
    frappe.clear_cache()
