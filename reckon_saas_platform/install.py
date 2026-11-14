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
    ensure_site_branding()


def after_migrate() -> None:
    setup_roles()
    setup_modules()
    setup_workspace()
    ensure_workspace_sidebar()
    ensure_signup_settings()
    ensure_marketing_home()
    ensure_site_branding()
    refresh_site_seo()
    audit_tenant_roles()
    ensure_file_storage_tracking()
    ensure_subscription_menu()


SUBSCRIPTION_MENU_ROUTE = "/reckonerp-subscription"
TEAM_MENU_ROUTE = "/reckonerp-team"
NOT_VENDOR = '!frappe.user.has_role("Reckon Vendor Superuser") && frappe.session.user !== "Administrator"'
# label, route, icon, who sees it (a client-side expression)
TENANT_MENU = (
    ("Subscription", SUBSCRIPTION_MENU_ROUTE, "credit-card", NOT_VENDOR),
    ("Team", TEAM_MENU_ROUTE, "users", "frappe.boot.reckon_company_admin && " + NOT_VENDOR),
)


def ensure_subscription_menu() -> None:
    """Put "Subscription" and "Team" on the Desk menu, so a tenant can reach them at any time.

    They are rows of Navbar Settings, added once and left alone afterwards (rename or hide them
    there). Vendor staff have no company subscription, so the rows are hidden for them; Team is
    for the company admin only.
    """
    try:
        if not frappe.db.exists("DocType", "Navbar Settings"):
            return
        settings = frappe.get_single("Navbar Settings")
        present = {(row.get("route") or "") for row in settings.get("settings_dropdown") or []}
        meta = frappe.get_meta("Navbar Item")
        added = False
        for label, route, icon, condition in TENANT_MENU:
            if route in present:
                continue
            row = {"item_label": label, "item_type": "Route", "route": route, "is_standard": 0, "hidden": 0}
            if meta.has_field("condition"):
                row["condition"] = condition
            if meta.has_field("icon"):
                row["icon"] = icon
            settings.append("settings_dropdown", row)
            added = True
        if added:
            settings.save(ignore_permissions=True)
    except Exception:
        frappe.log_error(title="Tenant menu setup failed")


def ensure_file_storage_tracking() -> None:
    """Never let the storage bookkeeping stop a migrate."""
    try:
        from reckon_saas_platform.plan_limits import ensure_file_company_field

        ensure_file_company_field()
    except Exception:
        frappe.log_error(title="File storage tracking setup failed")


def ensure_marketing_home() -> None:
    """Let the site root show the marketing website instead of redirecting to login.

    Website Settings > Home Page wins over the app's ``home_page`` hook, and an
    older site may still point it at the login page. A deliberate custom value
    is left alone.
    """
    if not frappe.db.exists("DocType", "Website Settings"):
        return
    current = frappe.db.get_single_value("Website Settings", "home_page") or ""
    if current in ("login", "index", "home"):
        frappe.db.set_single_value("Website Settings", "home_page", "")
        frappe.clear_cache()


def ensure_site_branding() -> None:
    """Give /login, emails and the footer the same name, logo and "powered by" as the landing page.

    The login page reads these Website Settings and System Settings fields. They
    are kept in step with the landing page on every migrate; set
    ``reckon_saas_keep_branding`` in the site config to manage them by hand.
    """
    if frappe.conf.get("reckon_saas_keep_branding"):
        return
    from reckon_saas_platform.marketing import BRAND_NAME, ICON, LOGO, POWERED_BY, PUBLISHER

    wanted = (
        ("Website Settings", "app_name", BRAND_NAME),
        ("Website Settings", "app_logo", LOGO),
        ("Website Settings", "footer_logo", LOGO),
        ("Website Settings", "footer_powered", POWERED_BY),
        ("Website Settings", "copyright", PUBLISHER),
        ("Website Settings", "favicon", ICON),
        ("System Settings", "app_name", BRAND_NAME),
    )
    changed = False
    for doctype, field, value in wanted:
        if not frappe.db.exists("DocType", doctype) or not frappe.get_meta(doctype).has_field(field):
            continue
        if frappe.db.get_single_value(doctype, field) != value:
            frappe.db.set_single_value(doctype, field, value)
            changed = True
    if changed:
        frappe.clear_cache()


def refresh_site_seo() -> None:
    """After every migrate (a release of this app or the theme) re-check the public site's SEO."""
    from reckon_saas_platform.seo import refresh_seo

    refresh_seo("migrate")


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
    # Frappe v16 requires a workspace type; a fresh install failed on "[Workspace, Reckon SaaS Admin]: type".
    data.setdefault("type", "Workspace")
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
        if item["type"] != "Link" or item.get("link_type") == "URL" or frappe.db.exists(item["link_type"], item["link_to"])
    ]
    return definition
