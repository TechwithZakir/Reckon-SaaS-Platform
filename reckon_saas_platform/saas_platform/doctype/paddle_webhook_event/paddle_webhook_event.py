from __future__ import annotations

from frappe.model.document import Document


class PaddleWebhookEvent(Document):
    """One verified Paddle notification, named by its event id so a redelivery is never processed twice."""
