from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document


class SaaSModule(Document):
    def validate(self) -> None:
        self.module_key = (self.module_key or "").strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,59}", self.module_key):
            frappe.throw(_("Module Key must be lowercase letters, digits or underscores."))
