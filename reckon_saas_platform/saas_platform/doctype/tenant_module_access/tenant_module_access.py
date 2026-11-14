from __future__ import annotations

from frappe.model.document import Document


class TenantModuleAccess(Document):
    """One module a person may use in the company, and the role they have in it."""
