from __future__ import annotations

import frappe

UNPROVISIONED = ["Pending Verification", "Provisioning", "Failed", "Rejected", "Cancelled"]
RESULT_FIELDS = ("company", "company_admin", "subscription", "payment", "provisioning_job")


def execute() -> None:
    """Unlink registrations from a Company that provisioning never created for them.

    Frappe filled the empty Company link of new registrations from the global
    default Company, so failed or pending signups pointed at the vendor's own
    company. Provisioning always sets ``company`` and ``company_admin`` together,
    so a registration that is not provisioned and has no admin user owns nothing.
    """
    for row in frappe.get_all(
        "SaaS Registration",
        filters={"status": ["in", UNPROVISIONED], "company": ["is", "set"]},
        fields=["name", "company_admin"],
    ):
        if row.company_admin:
            continue
        frappe.db.set_value(
            "SaaS Registration",
            row.name,
            {field: None for field in RESULT_FIELDS},
            update_modified=False,
        )
