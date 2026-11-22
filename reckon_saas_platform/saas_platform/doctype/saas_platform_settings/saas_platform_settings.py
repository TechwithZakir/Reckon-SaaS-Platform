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
        self._check_paddle_keys()

    def _check_paddle_keys(self) -> None:
        """A Sandbox key in a Live field (or the reverse) would talk to the wrong Paddle account: refuse it."""
        for fieldname, prefix in (
            ("paddle_client_token", "test_"),
            ("paddle_live_client_token", "live_"),
        ):
            value = (self.get(fieldname) or "").strip()
            self.set(fieldname, value)
            if value and not value.startswith(prefix):
                frappe.throw(f"{self.meta.get_label(fieldname)} must start with {prefix}.")
        for fieldname, prefix in (("paddle_api_key", "pdl_sdbx_"), ("paddle_live_api_key", "pdl_live_")):
            value = (self.get(fieldname) or "").strip()
            # An unchanged password comes back masked; only a newly typed key is checked.
            if value and not set(value) <= {"*"} and not value.startswith(prefix):
                frappe.throw(f"{self.meta.get_label(fieldname)} must start with {prefix}.")
