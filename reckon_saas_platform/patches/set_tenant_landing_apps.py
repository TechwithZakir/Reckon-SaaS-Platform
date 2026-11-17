import frappe


def execute():
    """Give every tenant user a landing app that matches what their companies subscribe to (not Reckon Accounts by default)."""
    from reckon_saas_platform.team import _sync_landing_app

    for user in frappe.get_all("Tenant User Assignment", filters={"active": 1}, pluck="user", distinct=True):
        if user and user not in ("Administrator", "Guest") and frappe.db.exists("User", user):
            _sync_landing_app(user)
    frappe.clear_cache()
