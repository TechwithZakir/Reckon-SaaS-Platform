"""ReckonERP, the suite: one subscription that gives a company several modules.

It is a module like the others to the rest of the platform (a page, plans, a subscription), but it owns no app.
Its plans list the modules they include in "Also Includes Modules", and the subscription covers them: Accounts and
HRMS on every plan, Sales AI Agent on the top one.
"""

from __future__ import annotations

MODULE_KEY = "reckonerp"


def get_module_definition() -> dict:
    return {
        "key": MODULE_KEY,
        "label": "ReckonERP",
        "bundle": True,
        "description": "ReckonBooks and Reckon HRMS in one subscription, with biometric attendance, the mobile app and "
        "app-based geo tracking, and Sales AI Agent on the top plan. Reckon CRM can be added as a module; asset and "
        "project management are coming soon.",
        # A suite has no workspace of its own: the company lands in Accounts, as an Accounts tenant would.
        "workspace": "app/accounts-home",
        "home_route": "/desk/accounts-home",
        "admin_role": "Reckon Accounts SaaS Admin",
        "roles": [],
        "subscription_features": ["reckon_accounts", "reckon_hrms", "biometric_attendance", "mobile_app", "geo_tracking"],
    }
