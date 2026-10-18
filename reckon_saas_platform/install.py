from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe import _

from reckon_saas_platform.constants import PLATFORM_ROLES, SAAS_PLATFORM_WORKSPACE

APP_PATH = Path(__file__).parent
# Frappe v16's orphan sweep keeps a standard Workspace only when an app ships
# <module>/workspace/<scrub(name)>/<scrub(name)>.json, and a standard Workspace
# Sidebar only when <app>/workspace_sidebar/<scrub(name)>.json exists. These
# files are the single source of truth; after_migrate reads them.
WORKSPACE_FILE = APP_PATH / "saas_platform" / "workspace" / "reckon_saas_admin" / "reckon_saas_admin.json"
SAAS_SIDEBAR = "SaaS Platform"
SIDEBAR_FILE = APP_PATH / "workspace_sidebar" / "saas_platform.json"


def _read_shipped(path: Path) -> dict:
    definition = json.loads(path.read_text(encoding="utf-8"))
    # `modified` only tells Frappe's file import whether to reload the file.
    definition.pop("modified", None)
    return definition


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


def _workspace_doc(update: bool = False) -> dict:
    """The "Reckon SaaS Admin" workspace shipped in ``saas_platform/workspace``.

    It stays public: the app icon opens /desk/reckon-saas-admin, and Desk routes
    that slug to a workspace only when it is public (a private one falls through
    to a Page lookup and 404s). Its roles keep it hidden from tenants.
    """
    data = _read_shipped(WORKSPACE_FILE)
    data["title"] = _(data["title"])
    if update:
        data.pop("name")
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
    """The rail shipped in ``workspace_sidebar/saas_platform.json``, minus links this site lacks."""
    definition = _read_shipped(SIDEBAR_FILE)
    definition["items"] = [
        item
        for item in definition["items"]
        if item["type"] != "Link" or frappe.db.exists(item["link_type"], item["link_to"])
    ]
    return definition
