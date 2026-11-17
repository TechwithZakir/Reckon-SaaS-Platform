import frappe

SIDEBARS = ("SaaS Platform", "Reckon SaaS Admin")


def execute():
    """Put Coupons in the SaaS admin menus (they sit before Payments). The menus Desk shows are Sidebar records, not the old file."""
    if not frappe.db.exists("DocType", "Sidebar"):
        return
    for name in SIDEBARS:
        if not frappe.db.exists("Sidebar", name):
            continue
        doc = frappe.get_doc("Sidebar", name)
        items = list(doc.get("items") or [])
        if any((row.get("link_to") or "") == "SaaS Coupon" for row in items):
            continue
        at = next((i for i, row in enumerate(items) if (row.get("link_to") or "") == "SaaS Payment"), None)
        if at is None:
            continue
        doc.append(
            "items",
            {"label": "Coupons", "type": "Link", "link_type": "DocType", "link_to": "SaaS Coupon", "icon": "tag", "child": 1, "indent": 0, "collapsible": 1, "show_arrow": 0},
        )
        rows = list(doc.get("items"))
        new = rows.pop()  # appended last
        rows.insert(at, new)
        for n, row in enumerate(rows, start=1):
            row.idx = n
        doc.set("items", rows)
        doc.flags.ignore_permissions = True
        doc.save()
    frappe.clear_cache()
