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


def ai_fill_policy(user: str | None = None) -> dict:
    """Whether Fill with AI is on for a person, and how many uses a day they get (``None`` is unlimited).

    Vendor staff and people with no company are never held back. ``create`` says whether it may offer to create
    missing customers, suppliers and items (on if any live plan allows it). A company is held to its live plans: it is on if
    any plan has it on, and the best daily limit among those plans applies (blank or 0 is unlimited).
    """
    user = user or frappe.session.user
    companies = [] if not user or user_can_bypass_tenant(user) else get_user_companies(user)
    if not companies:
        return {"enabled": True, "daily_limit": None, "create": True}
    plans = []
    for company in companies:
        plans += frappe.get_all(
            "SaaS Subscription",
            filters={"company": company, "status": ["in", LIVE_SUBSCRIPTION_STATUSES]},
            pluck="plan",
            ignore_permissions=True,
        )
    rows = [frappe.db.get_value("SaaS Plan", plan, ["ai_fill_enabled", "ai_fill_daily_limit", "ai_fill_create_enabled"], as_dict=True) for plan in set(plans) if plan]
    # A plan saved before the field existed counts as on, with the default limit.
    on = [r for r in rows if r and (r.get("ai_fill_enabled") is None or cint(r.get("ai_fill_enabled")))]
    if not on:
        return {"enabled": False, "daily_limit": None, "create": False}
    return {
        "enabled": True,
        "daily_limit": effective_limit([r.get("ai_fill_daily_limit") for r in on]),
        "create": any(r.get("ai_fill_create_enabled") is None or cint(r.get("ai_fill_create_enabled")) for r in on),
    }


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
