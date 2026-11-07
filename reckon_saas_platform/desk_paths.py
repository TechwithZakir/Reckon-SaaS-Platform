"""Pure Desk path rules for the module desk guard. No Frappe import, so they are unit-testable."""

from __future__ import annotations

from urllib.parse import unquote

DESK_PREFIXES = ("/app", "/desk")
RESOURCE_PREFIX = "/api/resource/"
# Desk pages every signed-in user needs, whatever their module.
ALWAYS_ALLOWED_DESK = frozenset({"", "home", "user", "user-profile", "update-password"})


def slugify(name: str | None) -> str:
    """Frappe's Desk route slug for a DocType or Workspace name: "Leave Application" -> "leave-application"."""
    return (name or "").strip().lower().replace(" ", "-")


def classify(path: str) -> tuple[str, str | None]:
    """Return (kind, value) for a request path.

    kind is "desk" (value: first Desk route segment, slugged), "resource" (value: the
    DocType in /api/resource/<doctype>, or None), or "other" (never restricted here).
    """
    path = (path or "").split("?", 1)[0]
    for prefix in DESK_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            parts = [unquote(p) for p in path[len(prefix):].strip("/").split("/") if p]
            return "desk", slugify(parts[0]) if parts else ""
    if path.startswith(RESOURCE_PREFIX):
        parts = [unquote(p) for p in path[len(RESOURCE_PREFIX):].strip("/").split("/") if p]
        return "resource", parts[0] if parts else None
    return "other", None


def is_allowed(kind: str, value: str | None, allowed_doctypes, allowed_workspaces) -> bool:
    if kind == "other":
        return True
    doctypes = set(allowed_doctypes or [])
    if kind == "resource":
        return value is None or value in doctypes
    if value in ALWAYS_ALLOWED_DESK:
        return True
    routes = {slugify(d) for d in doctypes} | {slugify(w) for w in (allowed_workspaces or [])}
    return value in routes
