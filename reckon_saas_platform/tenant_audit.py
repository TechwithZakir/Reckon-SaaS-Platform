"""Find doctypes a module opens to tenants without any company scope.

A module lists the doctypes tenants may open (``desk_doctypes``). Each must be filtered and protected by a
``permission_query_conditions`` and a ``has_permission`` hook (from any app: hooks are merged), unless it is a
child table or a vendor-wide reference record the module declares in ``desk_reference_doctypes`` (read-only
for tenants, so nothing of another company can leak or be changed through it).

``report()`` runs on a site (``bench --site <site> execute reckon_saas_platform.tenant_audit.report``) and the
module tests call ``find_unscoped`` with their own hooks, so a new module cannot ship an open doctype unnoticed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

# Records every tenant may read and none may change; any module can use them without declaring them.
COMMON_REFERENCE_DOCTYPES = frozenset({
    "DocType", "Report", "Page", "List Filter", "Language", "Country", "Currency", "Print Format", "Letter Head",
    "UOM Conversion Factor", "Dynamic Link", "File", "Comment", "Version", "Module Def", "Role", "User Permission",
})


def find_unscoped(
    doctypes: Iterable[str],
    query_hooks: Mapping[str, object],
    permission_hooks: Mapping[str, object],
    child_tables: Iterable[str] = (),
    reference: Iterable[str] = (),
    singles: Iterable[str] = (),
) -> list[tuple[str, str]]:
    """``(doctype, what is missing)`` for every doctype that has no company scope."""
    exempt = COMMON_REFERENCE_DOCTYPES | set(reference) | set(child_tables)
    singles = set(singles)  # one record, no rows to filter: a permission rule alone is enough
    findings = []
    for doctype in sorted(set(doctypes) - exempt):
        has_query = bool(query_hooks.get(doctype)) or doctype in singles
        has_permission = bool(permission_hooks.get(doctype))
        if has_query and has_permission:
            continue
        findings.append((doctype, "no row filter and no permission rule" if not has_query and not has_permission
                         else ("no row filter" if not has_query else "no permission rule")))
    return findings


def audit_modules() -> dict[str, list[tuple[str, str]]]:
    """Run ``find_unscoped`` for every registered module against the site's real hooks and doctypes."""
    import frappe

    from reckon_saas_platform.module_registry import get_saas_modules

    query_hooks = {dt: v for dt, v in (frappe.get_hooks("permission_query_conditions") or {}).items()}
    permission_hooks = {dt: v for dt, v in (frappe.get_hooks("has_permission") or {}).items()}
    out = {}
    for module in get_saas_modules():
        doctypes = [dt for dt in (module.get("desk_doctypes") or []) if frappe.db.exists("DocType", dt)]
        children = [dt for dt in doctypes if frappe.get_meta(dt).istable]
        singles = [dt for dt in doctypes if frappe.get_meta(dt).issingle]
        out[module.get("key") or module.get("name")] = find_unscoped(
            doctypes, query_hooks, permission_hooks, children, module.get("desk_reference_doctypes") or (), singles)
    return out


def report() -> None:
    """Print the gaps per module (``bench execute``). Nothing is changed."""
    for key, findings in audit_modules().items():
        print(f"{key}: {len(findings)} open")
        for doctype, why in findings:
            print(f"   {doctype}: {why}")


def assert_scoped(module_key: str | None = None) -> None:
    """CI step: fail when a module (or any module) opens a doctype to tenants without a company scope.

    ``bench --site <site> execute reckon_saas_platform.tenant_audit.assert_scoped --kwargs "{'module_key': 'hrms'}"``
    """
    gaps = {key: f for key, f in audit_modules().items() if f and (module_key is None or key == module_key)}
    if gaps:
        lines = [f"{key}: " + ", ".join(f"{dt} ({why})" for dt, why in f) for key, f in gaps.items()]
        raise AssertionError("Doctypes open to tenants without a company scope:\n" + "\n".join(lines))
    print("Tenant scoping audit: no open doctypes" + (f" in {module_key}" if module_key else ""))


def log_gaps() -> None:
    """``after_migrate``: record gaps in the Error Log so a new module's open doctypes are noticed on deploy."""
    import frappe

    try:
        gaps = {key: f for key, f in audit_modules().items() if f}
        if gaps:
            frappe.log_error(
                title="Tenant scoping gaps",
                message="\n".join(f"{key}: " + ", ".join(dt for dt, _why in f) for key, f in gaps.items()),
            )
    except Exception:  # noqa: BLE001  (an audit must never fail a migrate)
        frappe.log_error(title="Tenant scoping audit failed")
