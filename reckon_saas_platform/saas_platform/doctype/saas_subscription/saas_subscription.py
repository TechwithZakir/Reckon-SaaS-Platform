from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class SaaSSubscription(Document):
    def autoname(self) -> None:
        self.name = frappe.model.naming.make_autoname("SUB-.#####")

    def validate(self) -> None:
        set_module_from_plan(self)
        if self.is_new() and self.plan and not cint(self.grace_days):
            self.grace_days = cint(frappe.db.get_value("SaaS Plan", self.plan, "grace_days"))
        if not self.is_new():
            previous_price = frappe.db.get_value(self.doctype, self.name, "price")
            previous_plan_version = frappe.db.get_value(self.doctype, self.name, "plan_version")
            if previous_price is not None and float(previous_price) != float(self.price or 0):
                frappe.throw("Subscription price is preserved for the billing period.")
            if previous_plan_version and previous_plan_version != self.plan_version:
                frappe.throw("Subscription plan version is preserved for the billing period.")

    def on_update(self) -> None:
        _invalidate_gate(self.company)

    def on_trash(self) -> None:
        _invalidate_gate(self.company)


def set_module_from_plan(doc) -> None:
    """Record the plan's module on a registration or subscription.

    Each registration and subscription is for exactly one module: the module
    its plan sells. A module that disagrees with the plan is refused.
    """
    if not doc.plan:
        return
    plan_module = frappe.db.get_value("SaaS Plan", doc.plan, "saas_module")
    if not plan_module:
        return
    if doc.saas_module and doc.saas_module != plan_module:
        frappe.throw(
            _("Plan {0} belongs to module {1}, not {2}.").format(doc.plan, plan_module, doc.saas_module)
        )
    doc.saas_module = plan_module


def _invalidate_gate(company: str | None) -> None:
    from reckon_saas_platform.saas import invalidate_operational_access_cache

    invalidate_operational_access_cache(company)
