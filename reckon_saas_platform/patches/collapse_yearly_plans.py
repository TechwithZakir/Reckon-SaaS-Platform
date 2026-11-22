"""There is no separate Yearly plan any more: fold each Yearly SaaS Plan row into its Monthly row.

The Monthly row gets "Allow paying a year at once" with the months its old Yearly price stood for (the yearly price divided
by the monthly price, for example 10), keeps the Yearly row's Paddle price as its own yearly price, and takes over every
subscription, signup, invoice and coupon that pointed at the Yearly row (a subscription keeps billing yearly). The Yearly
row is then deleted. Paddle is not called: the Paddle price moves to the Monthly row instead of being archived.
A Yearly row that has no matching Monthly row, or whose price is not a whole number of monthly prices, is left as it is.
"""

from __future__ import annotations

import frappe


def execute() -> None:
    if not frappe.db.has_column("SaaS Plan", "allow_yearly_payment"):
        return
    from reckon_saas_platform.saas import plan_tier

    links = frappe.get_all("DocField", filters={"fieldtype": "Link", "options": "SaaS Plan"}, fields=["parent", "fieldname"])
    rows = frappe.get_all(
        "SaaS Plan",
        fields=["name", "plan_name", "saas_module", "currency", "billing_cycle", "price", "paddle_price_id", "paddle_environment", "paddle_price_signature", "enabled"],
        limit_page_length=0,
    )
    monthly = {}
    for row in rows:
        if (row.billing_cycle or "Monthly") == "Monthly":
            monthly[(row.saas_module, row.currency, plan_tier(row.plan_name))] = row
    folded = 0
    for yearly in rows:
        if yearly.billing_cycle != "Yearly":
            continue
        base = monthly.get((yearly.saas_module, yearly.currency, plan_tier(yearly.plan_name)))
        if not base or not float(base.price or 0):
            print(f"collapse_yearly_plans: no monthly plan for {yearly.name}; left as it is")
            continue
        months = round(float(yearly.price or 0) / float(base.price))
        if not 1 <= months <= 12 or abs(float(yearly.price) - months * float(base.price)) > 0.01:
            print(f"collapse_yearly_plans: {yearly.name} is not a whole number of months of {base.name}; left as it is")
            continue
        values = {"allow_yearly_payment": 1, "yearly_months_charged": months, "yearly_price": round(float(base.price) * months, 2)}
        same_env = yearly.paddle_price_id and (not base.paddle_environment or base.paddle_environment == yearly.paddle_environment)
        if same_env:
            values.update(
                paddle_yearly_price_id=yearly.paddle_price_id,
                paddle_yearly_price_signature=yearly.paddle_price_signature,
                paddle_environment=yearly.paddle_environment,
            )
        frappe.db.set_value("SaaS Plan", base.name, values, update_modified=False)
        for link in links:
            if frappe.db.has_column(link.parent, link.fieldname):
                frappe.db.sql(f"update `tab{link.parent}` set `{link.fieldname}` = %s where `{link.fieldname}` = %s", (base.name, yearly.name))
        # The Paddle price now belongs to the Monthly row; deleting the Yearly row must not archive it.
        frappe.db.set_value("SaaS Plan", yearly.name, {"paddle_price_id": None, "paddle_price_signature": None}, update_modified=False)
        frappe.delete_doc("SaaS Plan", yearly.name, force=True, ignore_permissions=True)
        folded += 1
    frappe.db.commit()
    print(f"collapse_yearly_plans: folded {folded} Yearly plan rows into their Monthly rows")
    try:
        from reckon_saas_platform.marketing import refresh_public_pages

        refresh_public_pages()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "collapse_yearly_plans: refresh public pages")
