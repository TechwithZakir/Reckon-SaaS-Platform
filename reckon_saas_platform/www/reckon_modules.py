import frappe

from reckon_saas_platform import marketing


def get_context(context):
    base = marketing.site_base()
    modules = marketing.get_modules()
    key = marketing.requested("slug")
    if not key:
        page = marketing.modules_page(base, modules)
    else:
        module = marketing.get_module(modules, key)
        if not module:
            raise frappe.DoesNotExistError
        page = marketing.module_page(base, module, modules)
    marketing.apply_context(context, page, modules)
