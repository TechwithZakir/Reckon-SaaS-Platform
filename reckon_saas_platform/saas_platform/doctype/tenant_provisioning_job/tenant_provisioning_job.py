from __future__ import annotations

import frappe
from frappe.model.document import Document


class TenantProvisioningJob(Document):
    def autoname(self) -> None:
        self.name = frappe.model.naming.make_autoname("TPJ-.#####")

    def validate(self) -> None:
        if not self.idempotency_key:
            self.idempotency_key = f"{self.company}:{self.seed_version}"
        existing = frappe.db.exists(
            self.doctype,
            {"name": ["!=", self.name], "company": self.company, "seed_version": self.seed_version},
        )
        if existing:
            frappe.throw("Provisioning job already exists for this company and seed version.")

    def on_update(self) -> None:
        _invalidate_gate(self.company)

    def on_trash(self) -> None:
        _invalidate_gate(self.company)


def _invalidate_gate(company: str | None) -> None:
    from reckon_saas_platform.saas import invalidate_operational_access_cache

    invalidate_operational_access_cache(company)
