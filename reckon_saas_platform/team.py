"""Company team and tenant access for every SaaS module, driven by module definitions.

A module takes part by declaring ``tenant_role_prefix`` (and optionally
``tenant_doctypes`` and ``tenant_grants``) in its ``reckon_saas_modules`` definition.
Modules without a prefix (for example Distribution, which has its own access rules)
are not touched here.

A user's per-company module roles and Company User Permissions are reconciled from
all their active Tenant User Assignments. Adding, changing or deactivating an
assignment runs the same reconcile.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import validate_email_address

from reckon_saas_platform.module_registry import get_saas_modules
from reckon_saas_platform.tenant_roles import role_kind_for_profile, tenant_role_name

ALLOWED_PROFILES = ("Company Manager", "Company Admin")
DEFAULT_GRANTS = {
    "Admin": {"read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
    "User": {"read": 1, "write": 1, "create": 1},
}
FLAG_FIELDS = ("read", "write", "create", "delete", "submit", "cancel")


def tenant_modules() -> list[dict]:
    return [module for module in get_saas_modules() if module.get("tenant_role_prefix")]


def ensure_tenant_roles(module: dict, company: str) -> dict:
    """Create the company's roles for a module, with their permissions on the module's doctypes."""
    prefix = module["tenant_role_prefix"]
    grants = module.get("tenant_grants") or DEFAULT_GRANTS
    roles = {}
    for kind in ("Admin", "User"):
        role = tenant_role_name(prefix, kind, company)
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
        flags = grants.get(kind, {})
        for doctype in module.get("tenant_doctypes") or []:
            if not frappe.db.exists("DocType", doctype):
                continue
            if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
                continue
            frappe.get_doc({
                "doctype": "Custom DocPerm", "parent": doctype, "parenttype": "DocType",
                "parentfield": "permissions", "role": role, "permlevel": 0,
                **{k: flags.get(k, 0) for k in FLAG_FIELDS},
            }).insert(ignore_permissions=True)
        roles[kind] = role
    return roles


def shared_roles_for(module: dict, row) -> set[str]:
    """Shared Frappe roles a module grants for one assignment: the chosen module role, or the default.

    Company Admin also gets the module's admin shared role (for example HR Manager). Shared roles carry no
    company rights of their own; company scoping comes from the platform's tenant rules.
    """
    role_map = module.get("tenant_role_map") or {}
    if not role_map:
        return set()
    if row.role_profile == "Company Admin":
        return {role_map[module["tenant_admin_map"]]} if module.get("tenant_admin_map") in role_map else set()
    chosen = row.get("module_role") or module.get("tenant_default_role")
    return {role_map[chosen]} if chosen in role_map else set()


def sync_company_permission(user: str, companies: list[str]) -> None:
    """One standard Company User Permission per company the user is actively assigned to."""
    existing = frappe.get_all(
        "User Permission", filters={"user": user, "allow": "Company"}, fields=["name", "for_value"]
    )
    for row in existing:
        if row.for_value not in companies:
            frappe.delete_doc("User Permission", row.name, ignore_permissions=True, force=True)
    have = {row.for_value for row in existing if row.for_value in companies}
    for company in companies:
        if company not in have:
            frappe.get_doc({
                "doctype": "User Permission", "user": user, "allow": "Company", "for_value": company,
                "apply_to_all_doctypes": 1, "is_default": 1,
            }).insert(ignore_permissions=True)


def reconcile_user(user: str) -> None:
    """Make the user's module roles and Company permissions match their active assignments.

    Role changes run as Administrator even when a company admin triggered them; the
    caller's session is restored afterwards.
    """
    if not user or user in {"Guest", "Administrator"} or not frappe.db.exists("User", user):
        return
    caller = frappe.session.user
    frappe.set_user("Administrator")
    try:
        _reconcile(user)
    finally:
        frappe.set_user(caller)


def _reconcile(user: str) -> None:
    from reckon_saas_platform.saas import is_subscription_active

    rows = frappe.get_all(
        "Tenant User Assignment", filters={"user": user, "active": 1}, fields=["company", "role_profile", "module_role"]
    )
    modules = tenant_modules()
    desired = set()
    for row in rows:
        for module in modules:
            if not is_subscription_active(row.company, module["key"]):
                continue
            roles = ensure_tenant_roles(module, row.company)
            desired.add(roles[role_kind_for_profile(row.role_profile)])
            desired.update(shared_roles_for(module, row))
            # A module may also need a shared role for its workspace access (no data rights of its own).
            shared = module.get("tenant_shared_role")
            if shared:
                if not frappe.db.exists("Role", shared):
                    frappe.get_doc({"doctype": "Role", "role_name": shared, "desk_access": 1}).insert(
                        ignore_permissions=True
                    )
                desired.add(shared)

    prefixes = tuple(module["tenant_role_prefix"] + " " for module in modules)
    managed = {
        role for role in frappe.get_all("Role", pluck="name")
        if prefixes and role.startswith(prefixes) and " - " in role
    }
    managed |= {role for module in modules for role in (module.get("tenant_role_map") or {}).values()}
    managed |= {module["tenant_shared_role"] for module in modules if module.get("tenant_shared_role")}
    doc = frappe.get_doc("User", user)
    current = set(frappe.get_roles(user))
    for role in sorted(desired - current):
        doc.add_roles(role)
    for role in sorted((managed & current) - desired):
        doc.remove_roles(role)
    # Keep permissions for every company the user is still assigned to, in any module.
    sync_company_permission(user, sorted({row.company for row in rows}))
    _sync_landing_app(user)
    frappe.clear_cache(user=user)


def _sync_landing_app(user: str) -> None:
    """A user whose companies subscribe to exactly one guarded module lands on that module's app."""
    from reckon_saas_platform.desk_module_guard import guarded_module_for_user

    module = guarded_module_for_user(user)
    target = module.get("app") if module else None
    if target and frappe.db.get_value("User", user, "default_app") != target:
        frappe.db.set_value("User", user, "default_app", target, update_modified=False)


def sync_tenant_user_access(doc, method=None) -> None:
    """Tenant User Assignment hook: reconcile the user, including when an assignment changes or ends."""
    if doc.get("user"):
        reconcile_user(doc.user)


def _welcome_email_flag() -> int:
    try:
        from reckon_saas_platform.saas import is_outgoing_email_configured

        return int(bool(is_outgoing_email_configured()))
    except Exception:
        return 0


def _admin_company(user: str) -> str:
    if user in {"Guest", "Administrator"}:
        frappe.throw(_("Sign in as a company admin."), frappe.PermissionError)
    companies = frappe.get_all(
        "Tenant User Assignment",
        filters={"user": user, "active": 1, "role_profile": "Company Admin"},
        pluck="company",
    )
    if len(companies) != 1:
        frappe.throw(_("Only a company admin of one company can manage the team."), frappe.PermissionError)
    return companies[0]


@frappe.whitelist(methods=["GET"])
def list_team_members() -> list[dict]:
    company = _admin_company(frappe.session.user)
    return frappe.get_all(
        "Tenant User Assignment", filters={"company": company, "active": 1},
        fields=["user", "role_profile"], order_by="creation asc",
    )


def team_overview(company: str) -> dict:
    """What the Team page shows: who has access, how many seats the plan allows, and the roles on offer."""
    from reckon_saas_platform.saas import _open_module_keys
    from reckon_saas_platform.tenant_security import company_user_limit

    members = frappe.get_all(
        "Tenant User Assignment", filters={"company": company, "active": 1},
        fields=["user", "role_profile", "module_role"], order_by="creation asc",
    )
    for row in members:
        row["full_name"] = frappe.db.get_value("User", row["user"], "full_name") or row["user"]
    held = _open_module_keys(company)
    module_roles = sorted(
        {key for module in tenant_modules() if module.get("key") in held for key in (module.get("tenant_role_map") or {})}
    )
    return {
        "company": company,
        "members": members,
        "used": len({row["user"] for row in members}),
        "limit": company_user_limit(company),
        "profiles": list(ALLOWED_PROFILES),
        "module_roles": module_roles,
    }


@frappe.whitelist(methods=["POST"])
def add_team_member(
    email: str,
    full_name: str | None = None,
    role_profile: str = "Company Manager",
    module_role: str | None = None,
) -> dict:
    company = _admin_company(frappe.session.user)
    email = (email or "").strip().lower()
    offered = {key for module in tenant_modules() for key in (module.get("tenant_role_map") or {})}
    if module_role and module_role not in offered:
        frappe.throw(_("Unknown module role."))
    if module_role == "Employee Self Service" and frappe.db.exists("DocType", "Employee"):
        # Frappe HRMS grants self-service only to a login linked to an Employee record of this company.
        if not frappe.db.exists("Employee", {"user_id": email, "company": company}):
            frappe.throw(_("Create the employee record for this user first, then give them self-service access."))
    if not validate_email_address(email):
        frappe.throw(_("Enter a valid email address."))
    if role_profile not in ALLOWED_PROFILES:
        frappe.throw(_("Unknown role profile."))
    if frappe.get_all(
        "Tenant User Assignment", filters={"user": email, "active": 1, "company": ["!=", company]}, pluck="name"
    ):
        frappe.throw(_("This user already belongs to another company."))
    from reckon_saas_platform.tenant_security import assert_user_limit_allows

    assert_user_limit_allows(company, email)  # before a login is created for someone who would not fit
    if not frappe.db.exists("User", email):
        # Created as the system: Frappe also creates the user's contact, which belongs to no one tenant.
        caller = frappe.session.user
        frappe.set_user("Administrator")
        try:
            frappe.get_doc({
                "doctype": "User", "email": email, "first_name": full_name or email,
                # The welcome email carries the link to set a password; sent only where email is set up.
                "enabled": 1, "send_welcome_email": _welcome_email_flag(),
            }).insert(ignore_permissions=True)
        finally:
            frappe.set_user(caller)
    existing = frappe.db.get_value("Tenant User Assignment", {"user": email, "company": company}, "name")
    if existing:
        doc = frappe.get_doc("Tenant User Assignment", existing)
        doc.db_set({"active": 1, "role_profile": role_profile, "module_role": module_role or ""})
        doc.reload()
        doc.run_method("on_update")  # db_set skips hooks
    else:
        doc = frappe.get_doc({
            "doctype": "Tenant User Assignment", "user": email, "company": company,
            "role_profile": role_profile, "module_role": module_role or "", "active": 1, "is_default": 1,
        }).insert(ignore_permissions=True)
    return {"user": email, "company": company, "role_profile": role_profile, "module_role": module_role or "",
            "assignment": doc.name}


@frappe.whitelist(methods=["POST"])
def remove_team_member(email: str) -> dict:
    company = _admin_company(frappe.session.user)
    email = (email or "").strip().lower()
    if email == frappe.session.user:
        frappe.throw(_("You cannot remove yourself."))
    name = frappe.db.get_value(
        "Tenant User Assignment", {"user": email, "company": company, "active": 1}, "name"
    )
    if not name:
        frappe.throw(_("This user is not on your team."))
    frappe.db.set_value("Tenant User Assignment", name, "active", 0)
    frappe.get_doc("Tenant User Assignment", name).run_method("on_update")
    return {"user": email, "company": company, "removed": True}
