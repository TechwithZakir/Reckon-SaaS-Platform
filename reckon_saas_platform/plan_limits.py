"""Plan limits that count something the tenant has: people and uploaded files.

Files are counted per company. The File record has no company of its own, so ``reckon_company`` is stamped
on it when it is uploaded (from the document it is attached to, else from the uploader's company).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from reckon_saas_platform.entitlements import effective_limit
from reckon_saas_platform.tenant_security import (
    LIVE_SUBSCRIPTION_STATUSES,
    get_user_companies,
    user_can_bypass_tenant,
)

COMPANY_FIELD = "reckon_company"
MB = 1024 * 1024


def plan_limit(company: str, field: str) -> int | None:
    plans = frappe.get_all(
        "SaaS Subscription",
        filters={"company": company, "status": ["in", LIVE_SUBSCRIPTION_STATUSES]},
        pluck="plan",
        ignore_permissions=True,
    )
    return effective_limit([frappe.db.get_value("SaaS Plan", plan, field) for plan in plans if plan])


def storage_used_bytes(company: str) -> int:
    row = frappe.db.sql("select coalesce(sum(file_size), 0) from `tabFile` where reckon_company = %s", company)
    return cint(row[0][0]) if row else 0


def file_company(doc) -> str | None:
    """The company a new file counts against."""
    if doc.get("attached_to_doctype") and doc.get("attached_to_name"):
        try:
            if frappe.get_meta(doc.attached_to_doctype).has_field("company"):
                company = frappe.db.get_value(doc.attached_to_doctype, doc.attached_to_name, "company")
                if company:
                    return company
        except Exception:
            pass
    user = doc.get("owner") or frappe.session.user
    if user_can_bypass_tenant(user):
        return None
    companies = get_user_companies(user)
    return companies[0] if len(companies) == 1 else None


def file_size_of(doc) -> int:
    size = cint(doc.get("file_size"))
    if not size and doc.get("content"):
        size = len(doc.content)
    return size


def format_mb(mb: float) -> str:
    return f"{mb / 1024:g} GB" if mb >= 1024 else f"{mb:.0f} MB"


def check_file_storage(doc, method=None) -> None:
    """File hook (before insert): count the file against its company and refuse it past the plan's storage."""
    try:
        company = file_company(doc)
        if not company:
            return
        doc.set(COMPANY_FIELD, company)
        limit = plan_limit(company, "max_storage_mb")
        if not limit:
            return
        used, size = storage_used_bytes(company), file_size_of(doc)
    except Exception:
        frappe.log_error(title="File storage check failed")  # never block an upload because the check itself broke
        return
    if used + size > limit * MB:
        frappe.throw(
            _("Your plan allows {0} of file storage and {1} is in use. Delete files or move to a larger plan to upload more.").format(
                format_mb(limit), format_mb(used / MB)
            ),
            title=_("File storage limit reached"),
        )


def ensure_file_company_field() -> None:
    """Add the company stamp to File on migrate and attribute files uploaded before it existed."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field

    if not frappe.db.exists("Custom Field", {"dt": "File", "fieldname": COMPANY_FIELD}):
        create_custom_field(
            "File",
            {"fieldname": COMPANY_FIELD, "label": "Company", "fieldtype": "Link", "options": "Company", "read_only": 1, "hidden": 1, "search_index": 1},
        )
    for row in frappe.get_all(
        "File",
        filters={COMPANY_FIELD: ["is", "not set"], "attached_to_doctype": ["is", "set"]},
        fields=["name", "attached_to_doctype", "attached_to_name", "owner"],
        limit=2000,
    ):
        company = file_company(frappe._dict(row))
        if company:
            frappe.db.set_value("File", row["name"], COMPANY_FIELD, company, update_modified=False)
