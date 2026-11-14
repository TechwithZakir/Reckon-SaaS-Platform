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

import json

import frappe
from frappe import _
from frappe.utils import validate_email_address

from reckon_saas_platform.module_registry import get_saas_modules
from reckon_saas_platform.team_catalog import choices_for
from reckon_saas_platform.tenant_roles import role_kind_for_profile, tenant_role_name

ALLOWED_PROFILES = ("Company Manager", "Company Admin")
DEFAULT_GRANTS = {
    "Admin": {"read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
    "User": {"read": 1, "write": 1, "create": 1},
}
FLAG_FIELDS = ("read", "write", "create", "delete", "submit", "cancel")


class _Row(dict):
    __getattr__ = dict.get


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


def module_profile(user: str, company: str, module_key: str, fallback_profile: str | None = None, fallback_module_role: str = "") -> dict | None:
    """What a person has in one module of a company: ``{"role_profile", "module_role"}``, or ``None`` for no access.

    A person with no module list keeps the old behaviour (every module of the company at their one role),
    and a Company Admin always has every module. Other apps call this from their access sync so one team
    page can give a person some modules and not others.
    """
    name = frappe.db.get_value("Tenant User Assignment", {"user": user, "company": company, "active": 1}, "name")
    legacy = {"role_profile": fallback_profile, "module_role": fallback_module_role}
    if not name or fallback_profile == "Company Admin":
        return legacy
    rows = frappe.get_all(
        "Tenant Module Access", filters={"parenttype": "Tenant User Assignment", "parent": name}, fields=["module", "role_profile", "module_role"],
        parent_doctype="Tenant User Assignment", ignore_permissions=True,
    )
    if not rows:
        return legacy
    mine = next((row for row in rows if row.module == module_key), None)
    return {"role_profile": mine.role_profile or fallback_profile, "module_role": mine.module_role or ""} if mine else None


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
            access = module_profile(user, row.company, module["key"], row.role_profile, row.module_role or "")
            if access is None:
                continue  # this person was not given this module
            mine = _Row(role_profile=access["role_profile"], module_role=access["module_role"])
            roles = ensure_tenant_roles(module, row.company)
            desired.add(roles[role_kind_for_profile(mine.role_profile)])
            desired.update(shared_roles_for(module, mine))
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


def company_modules(company: str) -> list[dict]:
    """The modules the company holds, with the role choices a person can have in each."""
    from reckon_saas_platform.saas import _open_module_keys, module_label

    held = _open_module_keys(company)
    return [
        {"key": m["key"], "name": module_label(m["key"]) or m.get("label") or m["key"], "choices": [c["label"] for c in choices_for(m)]}
        for m in get_saas_modules()
        if m.get("key") in held
    ]


def team_overview(company: str) -> dict:
    """What the Team page shows: who has access to which modules, the seats the plan allows, and the choices."""
    from reckon_saas_platform.tenant_security import company_user_limit

    modules = company_modules(company)
    members = frappe.get_all(
        "Tenant User Assignment", filters={"company": company, "active": 1},
        fields=["name", "user", "role_profile", "module_role"], order_by="creation asc",
    )
    for row in members:
        row["full_name"] = frappe.db.get_value("User", row["user"], "full_name") or row["user"]
        rows = frappe.get_all(
            "Tenant Module Access", filters={"parenttype": "Tenant User Assignment", "parent": row["name"]},
            fields=["module", "role_profile", "module_role"], parent_doctype="Tenant User Assignment", ignore_permissions=True,
        )
        mine = {r["module"]: _choice_label(r) for r in rows}
        if row["role_profile"] == "Company Admin":
            row["access"] = {m["key"]: "Admin" for m in modules}
        elif not rows:
            row["access"] = {m["key"]: "All access" for m in modules}  # no module list yet: every module, as before
        else:
            row["access"] = {m["key"]: mine[m["key"]] for m in modules if m["key"] in mine}
    return {
        "company": company,
        "members": members,
        "used": len({row["user"] for row in members}),
        "limit": company_user_limit(company),
        "modules": modules,
        "profiles": list(ALLOWED_PROFILES),
    }


def _choice_label(row) -> str:
    return row.get("module_role") or {"Company Manager": "Manager"}.get(row.get("role_profile") or "", row.get("role_profile") or "Manager")


def resolve_access(company: str, access) -> list[dict]:
    """The browser's ``[{"module", "choice"}]`` as validated module-access rows.

    Only modules the company holds and choices that module offers are accepted; the role profile and
    module role come from the catalog, never from the browser.
    """
    if isinstance(access, str):
        access = json.loads(access or "[]")
    held = {m["key"]: m for m in get_saas_modules() if m.get("key") in {x["key"] for x in company_modules(company)}}
    rows, seen = [], set()
    for item in access or []:
        key, label = (item or {}).get("module"), (item or {}).get("choice")
        if key not in held:
            frappe.throw(_("The company does not have the module {0}.").format(key))
        choice = next((c for c in choices_for(held[key]) if c["label"] == label), None)
        if not choice:
            frappe.throw(_("{0} is not a role in {1}.").format(label, key))
        if key in seen:
            continue
        seen.add(key)
        rows.append({"module": key, "role_profile": choice["role_profile"], "module_role": choice["module_role"]})
    if not rows:
        frappe.throw(_("Give this person at least one module."))
    return rows


def _write_access(doc, rows: list[dict]) -> None:
    doc.set("module_access", [])
    for row in rows:
        doc.append("module_access", row)
    doc.role_profile = "Company Manager"
    doc.module_role = rows[0]["module_role"] if len(rows) == 1 else ""


@frappe.whitelist(methods=["POST"])
def add_team_member(
    email: str,
    full_name: str | None = None,
    role_profile: str = "Company Manager",
    module_role: str | None = None,
    access: str | list | None = None,
) -> dict:
    company = _admin_company(frappe.session.user)
    email = (email or "").strip().lower()
    if not validate_email_address(email):
        frappe.throw(_("Enter a valid email address."))
    if role_profile not in ALLOWED_PROFILES:
        frappe.throw(_("Unknown role profile."))
    rows = resolve_access(company, access) if (access and role_profile != "Company Admin") else None
    if rows is None and role_profile != "Company Admin" and company_modules(company):
        frappe.throw(_("Give this person at least one module."))
    if frappe.get_all(
        "Tenant User Assignment", filters={"user": email, "active": 1, "company": ["!=", company]}, pluck="name"
    ):
        frappe.throw(_("This user already belongs to another company."))
    from reckon_saas_platform.tenant_security import assert_user_limit_allows

    assert_user_limit_allows(company, email)  # before a login is created for someone who would not fit
    if rows and any(r["module"] == "hrms" and r["module_role"] == "Employee Self Service" for r in rows) and frappe.db.exists("DocType", "Employee"):
        # Frappe HRMS grants self-service only to a login linked to an Employee record of this company.
        if not frappe.db.exists("Employee", {"user_id": email, "company": company}):
            frappe.throw(_("Create the employee record for this user first, then give them HR self-service access."))
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
        doc.active = 1
        doc.role_profile = role_profile
    else:
        doc = frappe.get_doc({
            "doctype": "Tenant User Assignment", "user": email, "company": company,
            "role_profile": role_profile, "active": 1, "is_default": 1,
        })
    if rows:
        _write_access(doc, rows)
    else:
        doc.set("module_access", [])
        doc.module_role = module_role or ""
    doc.flags.ignore_permissions = True
    doc.save() if existing else doc.insert()
    return {"user": email, "company": company, "role_profile": doc.role_profile, "assignment": doc.name}


@frappe.whitelist(methods=["POST"])
def set_member_access(email: str, access: str | list) -> dict:
    """Change which modules a person on the team can use, and their role in each."""
    company = _admin_company(frappe.session.user)
    email = (email or "").strip().lower()
    name = frappe.db.get_value("Tenant User Assignment", {"user": email, "company": company, "active": 1}, "name")
    if not name:
        frappe.throw(_("This user is not on your team."))
    doc = frappe.get_doc("Tenant User Assignment", name)
    if doc.role_profile == "Company Admin":
        frappe.throw(_("A company admin has every module. Change them to a manager first if you want to limit them."))
    _write_access(doc, resolve_access(company, access))
    doc.flags.ignore_permissions = True
    doc.save()
    return {"user": email, "company": company, "modules": [row.module for row in doc.module_access]}


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
