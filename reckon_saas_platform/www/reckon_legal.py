import frappe

from reckon_saas_platform import legal_pages, marketing


def get_context(context):
    slug = (frappe.local.request.path or "").strip("/").split("/")[-1] if getattr(frappe.local, "request", None) else ""
    if slug not in legal_pages.PAGES:
        raise frappe.DoesNotExistError
    marketing.apply_context(context, marketing.legal_page(marketing.site_base(), slug), marketing.get_modules())
