import frappe


def execute():
    """The assistant is spelled "Aura AI": update the published articles that say AuraAI or Reckon AI."""
    if not frappe.db.exists("DocType", "SEO Article"):
        return
    for name, body in frappe.get_all("SEO Article", fields=["name", "body"], as_list=True):
        if body and ("AuraAI" in body or "Reckon AI" in body):
            frappe.db.set_value("SEO Article", name, "body", body.replace("AuraAI", "Aura AI").replace("Reckon AI", "Aura AI"), update_modified=False)
    frappe.clear_cache()
