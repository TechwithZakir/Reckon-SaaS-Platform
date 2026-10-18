from __future__ import annotations

import frappe

MODULE_DOCTYPE = "SaaS Module"


def get_saas_modules() -> list[frappe._dict]:
    """Module definitions from every installed app's ``reckon_saas_modules`` hook."""
    modules: list[frappe._dict] = []
    for app in frappe.get_installed_apps():
        for module in frappe.get_hooks("reckon_saas_modules", app_name=app) or []:
            if isinstance(module, str):
                module = frappe.get_attr(module)()
            module = frappe._dict(module)
            module.setdefault("app", app)
            modules.append(module)
    return modules


def get_default_module() -> frappe._dict | None:
    modules = get_saas_modules()
    return modules[0] if modules else None


def get_module_definition(module_key: str | None) -> frappe._dict | None:
    for module in get_saas_modules():
        if module.get("key") == module_key:
            return module
    return None


def get_default_module_key() -> str | None:
    module = get_default_module()
    return module.get("key") if module else None


def get_landing_workspace(module_key: str | None = None) -> str:
    modules = get_saas_modules()
    if module_key:
        for module in modules:
            if module.get("key") == module_key:
                return module.get("workspace") or "distribution"

    default = modules[0] if modules else None
    return default.get("workspace") if default else "distribution"


def get_seed_handlers(module_keys: list[str] | set[str] | None = None) -> list[str]:
    """Seed handlers, limited to ``module_keys`` when given."""
    return [
        module.seed_handler
        for module in get_saas_modules()
        if module.get("seed_handler") and (module_keys is None or module.get("key") in module_keys)
    ]


def sync_saas_modules() -> list[str]:
    """Create or refresh a SaaS Module record for each hook definition.

    Code-owned fields (app, landing route, seed handler, features) follow the
    hook. Vendor-owned fields (name, availability, description) are only set
    when the record is first created.
    """
    if not frappe.db.exists("DocType", MODULE_DOCTYPE):
        return []
    synced = []
    for module in get_saas_modules():
        key = module.get("key")
        if not key:
            continue
        code_owned = {
            "app_name": module.get("app") or "",
            "landing_workspace": module.get("workspace") or "",
            "seed_handler": module.get("seed_handler") or "",
            "features": "\n".join(module.get("subscription_features") or []),
        }
        if frappe.db.exists(MODULE_DOCTYPE, key):
            doc = frappe.get_doc(MODULE_DOCTYPE, key)
            if any((doc.get(field) or "") != value for field, value in code_owned.items()):
                doc.update(code_owned)
                doc.save(ignore_permissions=True)
        else:
            frappe.get_doc(
                {
                    "doctype": MODULE_DOCTYPE,
                    "module_key": key,
                    "module_name": module.get("label") or key.replace("_", " ").title(),
                    "enabled": 1,
                    "description": module.get("description") or "",
                    **code_owned,
                }
            ).insert(ignore_permissions=True)
        synced.append(key)
    return synced


def backfill_plan_modules() -> int:
    """Assign plans created before modules existed to the default module."""
    default = get_default_module_key()
    if not default or not frappe.db.exists(MODULE_DOCTYPE, default):
        return 0
    count = 0
    for doctype in ("SaaS Plan", "SaaS Registration", "SaaS Subscription"):
        if not frappe.db.has_column(doctype, "saas_module"):
            continue
        names = frappe.get_all(doctype, filters={"saas_module": ["in", ["", None]]}, pluck="name")
        for name in names:
            frappe.db.set_value(doctype, name, "saas_module", default, update_modified=False)
        count += len(names)
    return count
