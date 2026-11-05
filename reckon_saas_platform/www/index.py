import frappe

from reckon_saas_platform import marketing


def get_context(context):
    # A signed-in person landing on "/" (for example right after logging in) goes
    # to their module, not the marketing page.
    destination = marketing.landing_for_user(frappe.session.user)
    if destination and destination != "/":
        frappe.local.flags.redirect_location = destination
        raise frappe.Redirect

    modules = marketing.get_modules()
    integrations = marketing.get_integrations()
    page = marketing.home_page(marketing.site_base(), modules, integrations, marketing.get_profiles())
    marketing.apply_context(context, page, modules)
