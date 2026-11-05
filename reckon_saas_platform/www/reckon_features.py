import frappe

from reckon_saas_platform import marketing


def get_context(context):
    base = marketing.site_base()
    modules = marketing.get_modules()
    slug = marketing.requested("slug")
    if not slug:
        page = marketing.features_page(base)
    else:
        feature = marketing.get_feature(slug)
        if not feature:
            raise frappe.DoesNotExistError
        page = marketing.feature_page(base, feature)
    marketing.apply_context(context, page, modules)
