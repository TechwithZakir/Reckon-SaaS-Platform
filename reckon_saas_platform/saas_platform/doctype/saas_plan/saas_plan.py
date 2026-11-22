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
        from reckon_saas_platform.plan_yearly import yearly_price

        on = self.billing_cycle == "Monthly" and self.get("allow_yearly_payment")
        self.yearly_price = yearly_price(self.price, self.yearly_months_charged) if on else 0
