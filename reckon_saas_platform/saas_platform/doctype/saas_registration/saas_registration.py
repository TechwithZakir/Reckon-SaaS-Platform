from __future__ import annotations

import frappe
from frappe.model.document import Document

from reckon_saas_platform.saas_platform.doctype.saas_subscription.saas_subscription import (
    set_module_from_plan,
)


class SaaSRegistration(Document):
    def autoname(self) -> None:
        self.name = frappe.model.naming.make_autoname("REG-.#####")

    def validate(self) -> None:
        set_module_from_plan(self)
