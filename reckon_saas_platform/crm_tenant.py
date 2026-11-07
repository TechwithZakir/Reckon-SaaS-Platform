"""Company-wise tenant isolation for Reckon CRM (Frappe CRM) records.

Frappe CRM has no company on its records, so on a shared SaaS site every CRM
user would see every tenant's leads. This module gives each CRM record a
``company`` (a custom field) and applies the same rule as the platform's other
tenant-owned doctypes (see ``tenant_security``):

- A **tenant user** (an active Tenant User Assignment) lists, opens and writes
  only records of their assigned companies. A new record gets their default
  company; a task, note, call log or field visit takes the company of the lead,
  deal or organization it belongs to. The company cannot change after insert.
- A **vendor user** (Administrator, System Manager or Reckon Vendor Superuser
  without a tenant assignment) sees everything.
- **Any other user** (the vendor's own staff with only a CRM role) sees the
  vendor's records only: those without a company, and never the SaaS signup
  pipeline, which stays vendor-only.

Records without a company belong to the vendor. Rules only narrow access:
Frappe CRM's own roles and Reckon CRM's visit permissions still apply.
"""

from __future__ import annotations

import frappe
from frappe import _

from reckon_saas_platform.tenant_security import (
    CrossCompanyAccessError,
    get_user_companies,
    user_can_bypass_tenant,
)

COMPANY = "company"

# CRM records that belong to one tenant company: Frappe CRM's, then Reckon CRM's.
TENANT_DOCTYPES = (
    "CRM Lead",
    "CRM Deal",
    "CRM Organization",
    "CRM Task",
    "FCRM Note",
    "CRM Call Log",
    "CRM Product",
    "CRM Field Visit",
    "CRM Customer Location",
)
# Where a child record finds the record it belongs to.
REFERENCE_FIELDS = (("reference_doctype", "reference_docname"), ("reference_doctype", "reference_name"))
# A deal belongs to the company of its lead, else of its organization.
PARENT_LINKS = {"CRM Deal": (("lead", "CRM Lead"), ("organization", "CRM Organization"))}

# SaaS signup pipeline: vendor-only even for the vendor's own CRM staff.
SAAS_LINK_FIELDS = {
    "CRM Lead": ("reckon_saas_registration",),
    "CRM Deal": ("reckon_saas_subscription", "reckon_saas_module"),
}


def company_field(doctype: str) -> dict:
    return {
        "fieldname": COMPANY,
        "fieldtype": "Link",
        "label": "Company",
        "options": "Company",
        "insert_after": "naming_series" if doctype in ("CRM Lead", "CRM Deal") else None,
        "in_standard_filter": 1,
        "search_index": 1,
        "no_copy": 1,
        "description": "The tenant company this record belongs to. Empty for the vendor's own records.",
    }


def tenant_custom_fields() -> dict[str, list[dict]]:
    """A ``company`` field for every installed CRM doctype that has none."""
    fields = {}
    for doctype in TENANT_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            continue
        if frappe.get_meta(doctype).has_field(COMPANY) and not frappe.db.exists(
            "Custom Field", {"dt": doctype, "fieldname": COMPANY}
        ):
            continue  # a standard company field already does the job
        field = {k: v for k, v in company_field(doctype).items() if v is not None}
        fields[doctype] = [field]
    return fields


# ---------------------------------------------------------------- who is asking


def _user_companies(user: str) -> list[str]:
    """Active tenant companies of ``user``, read once per request."""
    cache = getattr(frappe.local, "reckon_crm_tenant_companies", None)
    if cache is None:
        cache = {}
        frappe.local.reckon_crm_tenant_companies = cache
    if user not in cache:
        cache[user] = get_user_companies(user)
    return cache[user]


def _ready(doctype: str) -> bool:
    return bool(frappe.db.has_column(doctype, COMPANY))


# ---------------------------------------------------------------- list queries


def get_query(user: str | None = None, doctype: str | None = None) -> str:
    user = user or frappe.session.user
    if user_can_bypass_tenant(user):
        return ""
    table = f"`tab{doctype}`"
    companies = _user_companies(user)
    if companies:
        if not _ready(doctype):
            return "1 = 0"  # fail closed until migrate adds the field
        values = ", ".join(frappe.db.escape(company) for company in companies)
        return f"{table}.`{COMPANY}` in ({values})"
    clauses = [f"ifnull({table}.`{COMPANY}`, '') = ''"] if _ready(doctype) else []
    clauses += [
        f"ifnull({table}.`{field}`, '') = ''"
        for field in SAAS_LINK_FIELDS.get(doctype, ())
        if frappe.db.has_column(doctype, field)
    ]
    return " and ".join(f"({clause})" for clause in clauses)


# Frappe's permission_query_conditions hook takes one function per doctype.
def lead_query(user=None, **kwargs):
    return get_query(user, "CRM Lead")


def deal_query(user=None, **kwargs):
    return get_query(user, "CRM Deal")


def organization_query(user=None, **kwargs):
    return get_query(user, "CRM Organization")


def task_query(user=None, **kwargs):
    return get_query(user, "CRM Task")


def note_query(user=None, **kwargs):
    return get_query(user, "FCRM Note")


def call_log_query(user=None, **kwargs):
    return get_query(user, "CRM Call Log")


def product_query(user=None, **kwargs):
    return get_query(user, "CRM Product")


def field_visit_query(user=None, **kwargs):
    return get_query(user, "CRM Field Visit")


def customer_location_query(user=None, **kwargs):
    return get_query(user, "CRM Customer Location")


# ---------------------------------------------------------------- documents


def has_permission(doc, user: str | None = None, permission_type: str | None = None):
    """Deny another company's record; never grant more than CRM's own roles do."""
    user = user or frappe.session.user
    if user_can_bypass_tenant(user):
        return None
    company = doc.get(COMPANY) or ""
    companies = _user_companies(user)
    if companies:
        if doc.get("__islocal") and not company and permission_type == "create":
            return None  # bind_company fills it in on validate
        return None if company in companies else False
    if company:
        return False
    if any(doc.get(field) for field in SAAS_LINK_FIELDS.get(doc.doctype, ())):
        return False
    return None


def reference_company(doc) -> str | None:
    """The company of the lead, deal or organization this record belongs to."""
    for doctype_field, name_field in REFERENCE_FIELDS:
        ref_doctype, ref_name = doc.get(doctype_field), doc.get(name_field)
        if ref_doctype in TENANT_DOCTYPES and ref_name and _ready(ref_doctype):
            return frappe.db.get_value(ref_doctype, ref_name, COMPANY) or None
    for field, ref_doctype in PARENT_LINKS.get(doc.doctype, ()):
        if doc.get(field) and _ready(ref_doctype):
            company = frappe.db.get_value(ref_doctype, doc.get(field), COMPANY)
            if company:
                return company
    return None


def bind_company(doc, method=None) -> None:
    """``validate`` hook for every tenant CRM doctype."""
    if not _ready(doc.doctype):
        return
    if not doc.is_new():
        previous = frappe.db.get_value(doc.doctype, doc.name, COMPANY) or ""
        if previous != (doc.get(COMPANY) or ""):
            frappe.throw(_("Company cannot be changed after insert."), CrossCompanyAccessError)

    user = frappe.session.user
    inherited = reference_company(doc)
    if user_can_bypass_tenant(user):
        if doc.is_new() and not doc.get(COMPANY) and inherited:
            doc.set(COMPANY, inherited)
        return

    companies = _user_companies(user)
    if not companies:
        # The vendor's own CRM staff (and public signups) only make vendor records.
        if doc.get(COMPANY) or inherited:
            frappe.throw(_("Only users of that company can add to its CRM records."), CrossCompanyAccessError)
        return

    if doc.is_new() and not doc.get(COMPANY):
        doc.set(COMPANY, inherited if inherited in companies else companies[0])
    if doc.get(COMPANY) not in companies:
        frappe.throw(_("This CRM record belongs to another company."), CrossCompanyAccessError)
    if inherited and inherited != doc.get(COMPANY):
        frappe.throw(_("A record must belong to the same company as the lead or deal it is for."), CrossCompanyAccessError)
