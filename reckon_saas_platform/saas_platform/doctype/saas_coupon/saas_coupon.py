from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document


class SaaSCoupon(Document):
    def validate(self) -> None:
        self.code = re.sub(r"\s+", "", str(self.code or "")).upper()
        if not re.fullmatch(r"[A-Z0-9_-]{3,40}", self.code):
            frappe.throw(_("The coupon code must be 3 to 40 letters, digits, dashes or underscores."))
        if self.discount_type == "Percent":
            if not 0 < float(self.percent or 0) <= 100:
                frappe.throw(_("Percent off must be more than 0 and at most 100."))
            self.amount, self.currency = 0, None
        else:
            if float(self.amount or 0) <= 0 or not self.currency:
                frappe.throw(_("Give the amount off and its currency."))
            self.percent = 0
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            frappe.throw(_("Valid Until must not be before Valid From."))
        if int(self.max_redemptions or 0) < 0:
            frappe.throw(_("Maximum Uses cannot be negative."))
