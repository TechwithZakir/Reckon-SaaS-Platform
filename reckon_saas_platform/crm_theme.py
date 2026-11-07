"""Reckon Aura Theme for Reckon CRM's ``/crm`` app.

Frappe CRM is a separately built Vue app: Desk stylesheets (``app_include_css``)
and website stylesheets (``web_include_css``) never reach it, so the Aura theme
stops at the CRM's door. This ``after_request`` hook adds one stylesheet and a
small script to the ``/crm`` HTML page. The stylesheet maps Aura's tokens onto
frappe-ui's colour tokens (both the 0.1 and the 1.0 names), so the CRM follows
the theme without changing CRM or Reckon CRM source.

It applies only while Reckon Aura Theme is installed and enabled, and
SaaS Platform Settings > *CRM Follows Aura Theme* is on. The script sets the
same ``data-aura-*`` attributes as the Desk theme (accent, density, aurora),
honours the viewer's own accent and density from the Desk theme when user
override is allowed, and
leaves light and dark mode to CRM's own switch (frappe-ui's ``data-theme``).
"""

from __future__ import annotations

import json
import re

import frappe

STYLESHEET = "/assets/reckon_saas_platform/css/saas_crm_theme.css"
MARKER = 'data-reckon-crm-theme="aura"'
ACCENTS = frozenset({"violet", "cyan", "ember", "custom"})
DENSITIES = frozenset({"comfortable", "compact"})
COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def is_crm_path(path: str | None) -> bool:
    return bool(path) and (path == "/crm" or path.startswith("/crm/"))


def _color(value) -> str:
    value = (value or "").strip()
    return value if COLOR.match(value) else ""


def theme_config() -> dict | None:
    """Aura's public settings for the CRM page, or None when the CRM should keep its own look."""
    if "reckon_aura_theme" not in frappe.get_installed_apps():
        return None
    follow = frappe.db.get_single_value("SaaS Platform Settings", "crm_follow_theme")
    if follow is not None and not int(follow or 0):
        return None
    try:
        from reckon_aura_theme.api import get_public_config

        config = get_public_config() or {}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SaaS CRM theme")
        return None
    if not config.get("enabled"):
        return None
    accent = (config.get("accent") or "violet").lower()
    return {
        "accent": accent if accent in ACCENTS else "violet",
        "custom_accent": _color(config.get("custom_accent")),
        "custom_accent_2": _color(config.get("custom_accent_2")),
        "density": density if (density := (config.get("density") or "").lower()) in DENSITIES else "comfortable",
        "aurora": 0 if config.get("aurora_background") == 0 else 1,
        "allow_user_override": 1 if config.get("allow_user_override") else 0,
    }


def snippet(config: dict) -> str:
    """The tags added before ``</head>``."""
    data = json.dumps(config, separators=(",", ":")).replace("</", "<\\/")
    from reckon_saas_platform import __version__ as version

    return (
        f'<link rel="stylesheet" href="{STYLESHEET}?v={version}" {MARKER}>'
        "<script>(function(c){try{var r=document.documentElement,p={};"
        "if(c.allow_user_override){try{p=JSON.parse(localStorage.getItem('aura:prefs'))||{}}catch(e){}}"
        "var a=p.accent||c.accent;if(a==='custom'&&!c.custom_accent)a='violet';"
        "r.setAttribute('data-reckon-theme','aura');r.setAttribute('data-aura-accent',a);"
        "r.setAttribute('data-aura-aurora',c.aurora?'on':'off');"
        "var d=p.density==='compact'||p.density==='comfortable'?p.density:c.density;"
        "r.setAttribute('data-aura-density',d);"
        "if(a==='custom'){r.style.setProperty('--aura-accent',c.custom_accent);"
        "r.style.setProperty('--aura-accent-2',c.custom_accent_2||c.custom_accent)}"
        f"}}catch(e){{}}}})({data});</script>"
    )


def inject_theme(response, request) -> None:
    """``after_request`` hook: theme the ``/crm`` page."""
    try:
        if response is None or not is_crm_path(getattr(request, "path", None)):
            return
        if response.status_code != 200 or response.direct_passthrough:
            return
        if "text/html" not in (response.content_type or ""):
            return
        config = theme_config()
        if not config:
            return
        html = response.get_data(as_text=True)
        if MARKER in html or "</head>" not in html:
            return
        response.set_data(html.replace("</head>", snippet(config) + "</head>", 1))
    except Exception:
        # A theme problem must never break the CRM page.
        frappe.log_error(frappe.get_traceback(), "SaaS CRM theme")
