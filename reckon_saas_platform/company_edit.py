"""What a tenant's company admin may change on their own Company.

Contact and registration details only. Everything that shapes the books (currency, default accounts, the chart of
accounts, name and abbreviation, ...) stays with Reckon support. The module hooks decide who may *save* a Company;
this decides *what* they may change, whichever module they subscribed to and whether the change comes from the form
or the API.
"""

from __future__ import annotations

import frappe
from frappe import _

from reckon_saas_platform.tenant_security import tenant_company_or_none

EDITABLE_COMPANY_FIELDS = frozenset(
    {
        "email", "phone_no", "fax", "website", "company_description", "registration_details", "tax_id",
        "date_of_incorporation", "date_of_commencement", "company_logo", "default_letter_head",
    }
)
_LAYOUT = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Heading", "Table", "Table MultiSelect"}


def validate_company_edit(doc, method=None) -> None:
    """``Company.validate``: a tenant changes only the editable details. Vendor staff and new records are not limited here."""
    if doc.is_new() or not tenant_company_or_none():
        return
    before = doc.get_doc_before_save()
    if not before:
        return
    changed = [
        _(field.label or field.fieldname)
        for field in doc.meta.fields
        if field.fieldtype not in _LAYOUT
        and field.fieldname not in EDITABLE_COMPANY_FIELDS
        and (before.get(field.fieldname) or None) != (doc.get(field.fieldname) or None)
    ]
    if changed:
        frappe.throw(
            _("Only Reckon support can change: {0}. You can update your contact and registration details.").format(", ".join(changed)),
            frappe.PermissionError,
        )
