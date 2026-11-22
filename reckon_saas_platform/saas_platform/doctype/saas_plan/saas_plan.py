from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class SaaSPlan(Document):
    def validate(self) -> None:
        if not self.saas_module:
            from reckon_saas_platform.module_registry import get_default_module_key

            default = get_default_module_key()
            if default and frappe.db.exists("SaaS Module", default):
                self.saas_module = default
        if not self.saas_module:
            frappe.throw(_("Select the module this plan sells."))
        from reckon_saas_platform.plan_yearly import validate_yearly

        problem = validate_yearly(self.billing_cycle, bool(self.get("allow_yearly_payment")), self.get("yearly_months_charged"))
        if problem:
            frappe.throw(_(problem))

    def on_update(self) -> None:
        # The Yearly row follows this Monthly row; its own save must not start the same walk again.
        if not self.flags.get("in_yearly_sync"):
            sync_yearly_plan(self)


def _find_yearly_row(monthly) -> str | None:
    """The Yearly row that belongs to this Monthly one: the linked row, else the same module, currency and tier."""
    from reckon_saas_platform.saas import plan_tier

    linked = monthly.get("yearly_plan")
    if linked and frappe.db.exists("SaaS Plan", linked):
        return linked
    tier = plan_tier(monthly.plan_name)
    for row in frappe.get_all("SaaS Plan", filters={"saas_module": monthly.saas_module, "currency": monthly.currency,
                                                     "billing_cycle": "Yearly"}, fields=["name", "plan_name"], limit=50):
        if plan_tier(row.plan_name) == tier:
            return row.name
    return None


def sync_yearly_plan(monthly) -> str | None:
    """Create or update the Yearly row for a Monthly row that offers paying a year at once. Returns its name."""
    from reckon_saas_platform.plan_yearly import YEARLY_COPY_FIELDS, yearly_plan_name, yearly_price

    months = int(monthly.get("yearly_months_charged") or 0)
    if monthly.billing_cycle != "Monthly" or not monthly.get("allow_yearly_payment") or not months:
        return None
    values = {field: monthly.get(field) for field in YEARLY_COPY_FIELDS}
    values.update(billing_cycle="Yearly", price=yearly_price(monthly.price, months), enabled=monthly.enabled,
                  allow_yearly_payment=0, yearly_months_charged=0)
    rows = [{"feature": r.feature, "included": r.included, "value": r.value} for r in monthly.get("comparison_features") or []]
    name = _find_yearly_row(monthly)
    if name:
        yearly = frappe.get_doc("SaaS Plan", name)
        yearly.update(values)
    else:
        yearly = frappe.get_doc({"doctype": "SaaS Plan", "plan_name": yearly_plan_name(monthly.plan_name), **values})
    yearly.set("comparison_features", rows)
    yearly.flags.in_yearly_sync = True
    yearly.save(ignore_permissions=True)
    if monthly.get("yearly_plan") != yearly.name:
        monthly.db_set("yearly_plan", yearly.name, update_modified=False)
    return yearly.name
