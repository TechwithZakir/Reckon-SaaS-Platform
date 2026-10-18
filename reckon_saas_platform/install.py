from __future__ import annotations

import json

import frappe
from frappe import _

from reckon_saas_platform.constants import PLATFORM_ROLES, SAAS_PLATFORM_WORKSPACE

SAAS_WORKSPACE_ROLES = ["Reckon Vendor Superuser", "System Manager"]

SAAS_SIDEBAR = "SaaS Platform"
DASHBOARD_PAGE = "saas-dashboard"
DASHBOARD_LABEL = "Dashboard"

SAAS_DOCTYPES = [
    ("SaaS Module", "Modules"),
    ("SaaS Plan", "Plans"),
    ("SaaS Registration", "Registrations"),
    ("SaaS Subscription", "Subscriptions"),
    ("SaaS Payment", "Payments"),
    ("Tenant Provisioning Job", "Provisioning Jobs"),
    ("Tenant User Assignment", "Tenant User Assignments"),
    ("Company", "Tenant Companies"),
    ("SaaS Platform Settings", "Signup Settings"),
]

SAAS_WEB_PAGES = [
    ("Vendor SaaS Admin", "/reckon-saas-admin"),
    ("Public Signup", "/reckonerp-signup"),
    ("Tenant Subscription", "/reckonerp-subscription"),
]


def after_install() -> None:
    setup_roles()
    setup_modules()
    setup_workspace()
    ensure_workspace_sidebar()
    ensure_signup_settings()


def after_migrate() -> None:
    setup_roles()
    setup_modules()
    setup_workspace()
    ensure_workspace_sidebar()
    ensure_signup_settings()
    audit_tenant_roles()


def after_app_install(app_name: str | None = None) -> None:
    setup_modules()
    ensure_workspace_sidebar()


def setup_modules() -> None:
    """Register each app's SaaS module and attach older plans to the default one."""
    from reckon_saas_platform.module_registry import backfill_plan_modules, sync_saas_modules

    sync_saas_modules()
    backfill_plan_modules()


def ensure_signup_settings() -> None:
    """Persist SaaS Platform Settings defaults once.

    An unsaved Single reads its Check fields as 0, which would silently switch
    off phone verification and captcha. Saving the defaults makes both required
    until the vendor configures BulkSMSBD and reCAPTCHA.
    """
    doctype = "SaaS Platform Settings"
    if not frappe.db.exists("DocType", doctype):
        return
    if frappe.db.get_singles_dict(doctype):
        return
    settings = frappe.get_single(doctype)
    for df in settings.meta.fields:
        if df.default is not None and settings.get(df.fieldname) in (None, ""):
            settings.set(df.fieldname, df.default)
    settings.save(ignore_permissions=True)


def audit_tenant_roles() -> None:
    from reckon_saas_platform.tenant_security import audit_tenant_role_violations

    audit_tenant_role_violations()


def setup_roles() -> None:
    for role in PLATFORM_ROLES:
        if not frappe.db.exists("Role", role.name):
            frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": role.name,
                    "desk_access": 1,
                    "is_custom": 1,
                }
            ).insert(ignore_permissions=True)
        else:
            frappe.db.set_value("Role", role.name, "desk_access", 1)
            frappe.db.set_value("Role", role.name, "home_page", "")


def setup_workspace() -> None:
    if not frappe.db.exists("Workspace", SAAS_PLATFORM_WORKSPACE):
        frappe.get_doc(_workspace_doc()).insert(ignore_permissions=True)
    else:
        workspace = frappe.get_doc("Workspace", SAAS_PLATFORM_WORKSPACE)
        workspace.update(_workspace_doc(update=True))
        workspace.save(ignore_permissions=True)


def _workspace_shortcuts() -> list[dict]:
    return (
        [{"label": DASHBOARD_LABEL, "type": "Page", "link_to": DASHBOARD_PAGE, "color": "Green"}]
        + [
            {
                "label": label,
                "type": "DocType",
                "link_to": doctype,
                "doc_view": "List",
            }
            for doctype, label in SAAS_DOCTYPES
        ]
        + [{"label": label, "type": "URL", "url": url, "color": "Blue"} for label, url in SAAS_WEB_PAGES]
    )


def _workspace_content(shortcuts: list[dict]) -> str:
    blocks = [
        {"id": "intro", "type": "header", "data": {"text": "Reckon SaaS Admin", "col": 12}},
        {
            "id": "summary",
            "type": "paragraph",
            "data": {
                "text": "Modules, plans, registrations, subscriptions, payments and tenant provisioning.",
                "col": 12,
            },
        },
    ]
    blocks += [
        {"id": f"shortcut-{index}", "type": "shortcut", "data": {"shortcut_name": row["label"], "col": 3}}
        for index, row in enumerate(shortcuts)
    ]
    return json.dumps(blocks)


def _workspace_doc(update: bool = False) -> dict:
    shortcuts = _workspace_shortcuts()
    data = {
        "doctype": "Workspace",
        "label": SAAS_PLATFORM_WORKSPACE,
        "title": _("Reckon SaaS Admin"),
        "module": "SaaS Platform",
        "category": "Modules",
        # The app icon opens /desk/reckon-saas-admin. Desk routes that slug to a
        # workspace only when it is public; a private workspace falls through to
        # a Page lookup and 404s. The roles below keep it hidden from tenants.
        "public": 1,
        "for_user": "",
        "is_hidden": 0,
        "icon": "settings",
        "roles": [{"role": role} for role in SAAS_WORKSPACE_ROLES],
        "content": _workspace_content(shortcuts),
        "shortcuts": shortcuts,
        "links": [],
        "charts": [],
        "number_cards": [],
    }
    if not update:
        data["name"] = SAAS_PLATFORM_WORKSPACE
    return data


def ensure_workspace_sidebar() -> None:
    """Rebuild the Desk left rail (Frappe v16 Workspace Sidebar) for the SaaS app.

    v16 otherwise generates a partial sidebar from a few doctypes. The rail is
    application-owned, so its rows are replaced on every migrate.
    """
    if not frappe.db.exists("DocType", "Workspace Sidebar"):
        return  # Frappe v15 has no Workspace Sidebar.
    names = set(frappe.get_all("Workspace Sidebar", filters={"module": "SaaS Platform"}, pluck="name"))
    names.update(
        name for name in (SAAS_SIDEBAR, SAAS_PLATFORM_WORKSPACE) if frappe.db.exists("Workspace Sidebar", name)
    )
    definition = _workspace_sidebar_doc()
    if not names:
        frappe.get_doc(definition).insert(ignore_permissions=True, ignore_links=True)
        return
    for name in sorted(names):
        sidebar = frappe.get_doc("Workspace Sidebar", name)
        sidebar.set("items", definition["items"])
        sidebar.header_icon = definition["header_icon"]
        sidebar.save(ignore_permissions=True)


def _workspace_sidebar_doc() -> dict:
    def section(label: str, icon: str) -> dict:
        return {
            "label": label,
            "type": "Section Break",
            "icon": icon,
            "child": 0,
            "indent": 0,
            "collapsible": 1,
            "keep_closed": 0,
            "show_arrow": 0,
        }

    def link(label: str, link_to: str, link_type: str, icon: str, *, child: bool = True) -> dict:
        return {
            "label": label,
            "link_to": link_to,
            "link_type": link_type,
            "type": "Link",
            "icon": icon,
            "child": int(child),
            "indent": 0,
            "collapsible": 1,
            "show_arrow": 0,
        }

    items = [
        link(DASHBOARD_LABEL, DASHBOARD_PAGE, "Page", "layout-dashboard", child=False),
        section("Catalogue", "boxes"),
        link("Modules", "SaaS Module", "DocType", "boxes"),
        link("Plans", "SaaS Plan", "DocType", "tags"),
        section("Signups & Billing", "credit-card"),
        link("Registrations", "SaaS Registration", "DocType", "user-plus"),
        link("Subscriptions", "SaaS Subscription", "DocType", "repeat"),
        link("Payments", "SaaS Payment", "DocType", "credit-card"),
        section("Tenants", "building-2"),
        link("Tenant Companies", "Company", "DocType", "building-2"),
        link("Tenant User Assignments", "Tenant User Assignment", "DocType", "users"),
        link("Provisioning Jobs", "Tenant Provisioning Job", "DocType", "server-cog"),
        section("Settings", "settings"),
        link("Signup Settings", "SaaS Platform Settings", "DocType", "settings"),
    ]
    items = [
        item
        for item in items
        if item["type"] != "Link" or frappe.db.exists(item["link_type"], item["link_to"])
    ]
    return {
        "doctype": "Workspace Sidebar",
        "name": SAAS_SIDEBAR,
        "app": "reckon_saas_platform",
        "module": "SaaS Platform",
        "title": "SaaS Platform",
        "header_icon": "layout-dashboard",
        "standard": 1,
        "items": items,
    }
