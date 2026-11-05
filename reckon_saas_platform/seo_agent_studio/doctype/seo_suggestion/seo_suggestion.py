import frappe
from frappe.model.document import Document

from reckon_saas_platform.marketing import OVERRIDES_CACHE_KEY


class SEOSuggestion(Document):
    def validate(self):
        # Edited text is checked again here, so an approved suggestion is always publishable.
        from reckon_saas_platform.seo_agent import valid_description, valid_faq, valid_title

        if self.status != "Approved":
            return
        if self.kind == "Title and Description":
            if not (valid_title(self.proposed_title or "") and valid_description(self.proposed_description or "")):
                frappe.throw("Title must be 20-70 characters and description 70-160, without superlatives or the framework name.")
        elif self.kind == "FAQ" and not valid_faq(self.question or "", self.answer or ""):
            frappe.throw("The question must end with ? and the answer must be 40-600 characters, without superlatives or the framework name.")

    def on_update(self):
        # Approved text reaches the website straight away; the SEO check re-runs in the background.
        frappe.cache.delete_value(OVERRIDES_CACHE_KEY)
        frappe.enqueue("reckon_saas_platform.seo.refresh_seo", trigger="approval", queue="short", enqueue_after_commit=True)

    def on_trash(self):
        frappe.cache.delete_value(OVERRIDES_CACHE_KEY)
