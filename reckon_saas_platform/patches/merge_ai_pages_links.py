import frappe


def execute():
    """The Ask AI and Aura AI assistant feature pages are one page: point published articles at it."""
    if not frappe.db.exists("DocType", "SEO Article"):
        return
    for name, body in frappe.get_all("SEO Article", fields=["name", "body"], as_list=True):
        new = (body or "").replace("/features/reckon-ai-assistant", "/features/aura-ai-assistant").replace("/features/ask-ai", "/features/aura-ai-assistant")
        new = new.replace("Aura AI assistant", "Aura AI Assistance")
        if new != body:
            frappe.db.set_value("SEO Article", name, "body", new, update_modified=False)
    frappe.clear_cache()
