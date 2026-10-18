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
