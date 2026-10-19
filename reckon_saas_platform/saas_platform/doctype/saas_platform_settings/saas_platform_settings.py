from __future__ import annotations

import frappe
from frappe.model.document import Document


class SaaSPlatformSettings(Document):
    def validate(self) -> None:
        if self.bulksmsbd_sender_id:
            self.bulksmsbd_sender_id = self.bulksmsbd_sender_id.strip()
        if self.recaptcha_site_key:
            self.recaptcha_site_key = self.recaptcha_site_key.strip()
        for fieldname, minimum in (
            ("otp_validity_minutes", 1),
            ("otp_max_attempts", 1),
            ("otp_resend_cooldown_seconds", 0),
            # 0 falls back to site config or the built-in default.
            ("signup_rate_limit_per_hour", 0),
            ("verify_rate_limit_per_hour", 0),
        ):
            if (self.get(fieldname) or 0) < minimum:
                frappe.throw(f"{self.meta.get_label(fieldname)} must be at least {minimum}.")
        score = self.get("recaptcha_min_score")
        if score is not None and not 0 <= score <= 1:
            frappe.throw(f"{self.meta.get_label('recaptcha_min_score')} must be between 0 and 1.")
