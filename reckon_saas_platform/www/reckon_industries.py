import frappe

from reckon_saas_platform import marketing


def get_context(context):
    base = marketing.site_base()
    modules = marketing.get_modules()
    slug = marketing.requested("slug")
    if not slug:
        page = marketing.industries_page(base)
    else:
        industry = marketing.get_industry(slug)
        if not industry:
            raise frappe.DoesNotExistError
        page = marketing.industry_page(base, industry, modules)
    marketing.apply_context(context, page, modules)
