from __future__ import annotations

import frappe

from reckon_saas_platform import team


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/reckonerp-team"
        raise frappe.Redirect

    context.no_cache = 1
    context.title = "Team"
    context.account_tab = "team"
    context.is_company_admin = True
    context.app_home = "/desk"
    context.me = frappe.session.user
    context.error = ""
    context.overview = None
    try:
        company = team._admin_company(frappe.session.user)
        context.overview = team.team_overview(company)
    except frappe.PermissionError:
        frappe.clear_messages()
        context.error = "Only the company admin can manage the team."
    return context
