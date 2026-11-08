"""Keeps the public site's SEO current: after every migrate and once a day.

Page titles, descriptions, the sitemap, ``llms.txt`` and structured data are built
from the live module registry on every request, so they never go stale by
themselves. This module adds what a request cannot:

* a health check of every public page (unique titles and descriptions, sizes,
  one heading) with the result stored in SaaS Platform Settings;
* a content fingerprint, so a change (a module installed, switched off or
  renamed, a feature edited in a release) is noticed;
* a website cache clear when the fingerprint changes;
* an optional IndexNow notice to search engines that pages changed. It is off
  until **Notify Search Engines** is ticked; no other message is ever sent.
"""

from __future__ import annotations

import hashlib
import json
import re

import frappe

from reckon_saas_platform import marketing

SETTINGS = "SaaS Platform Settings"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS_PER_NOTICE = 100


def collect_pages(base: str, modules: list[dict], integrations=None, profiles=None, articles=None) -> list[dict]:
    from reckon_saas_platform import blog

    articles = blog.get_articles() if articles is None else articles
    pages = [
        marketing.home_page(base, modules, integrations, profiles, articles),
        marketing.features_page(base),
        marketing.modules_page(base, modules),
        marketing.integrations_page(base, integrations),
        marketing.pricing_page(base, modules),
        marketing.faq_page(base, modules),
    ]
    pages += [marketing.feature_page(base, feature) for feature in marketing.FEATURE_LIST]
    pages += [marketing.module_page(base, module, modules) for module in modules]
    if articles:
        pages.append(blog.blog_page(base, articles))
        pages += [blog.article_page(base, article, articles) for article in articles]
    return pages


def check_pages(pages: list[dict]) -> list[str]:
    """Plain-language problems that would hurt search or AI answers."""
    issues = []
    for field, low, high in (("title", 10, 70), ("description", 50, 160)):
        seen: dict[str, str] = {}
        for page in pages:
            text = page[field]
            if not low <= len(text) <= high:
                issues.append(f"{page['path']}: {field} is {len(text)} characters (aim for {low}-{high})")
            if text in seen:
                issues.append(f"{page['path']}: {field} repeats {seen[text]}")
            seen.setdefault(text, page["path"])
    for page in pages:
        if not page["h1"].strip():
            issues.append(f"{page['path']}: missing main heading")
        if not page["jsonld"]:
            issues.append(f"{page['path']}: no structured data")
    return issues


def fingerprint(pages: list[dict], paths: list[str]) -> str:
    """Changes whenever a page's search-facing content or the list of pages changes."""
    items = [[p["path"], p["title"], p["description"], p["h1"], p["jsonld"]] for p in pages]
    raw = json.dumps([items, paths], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _setting(field):
    return frappe.db.get_single_value(SETTINGS, field)


def _store(**values) -> None:
    for field, value in values.items():
        frappe.db.set_single_value(SETTINGS, field, value)


def _clear_website_cache() -> None:
    try:
        from frappe.website.utils import clear_website_cache

        clear_website_cache()
    except Exception:
        frappe.clear_cache()


def _indexnow_enabled() -> bool:
    return bool(frappe.utils.cint(_setting("indexnow_enabled")))


def refresh_seo(trigger: str = "scheduler") -> dict:
    """Check every public page, store the result, and react when the content changed.

    Runs from ``after_migrate`` (every release of this app or the theme) and daily.
    Never raises: a problem here must not stop a migrate or a scheduler run.
    """
    try:
        if not frappe.db.exists("DocType", SETTINGS):
            return {}
        base = marketing.site_base()
        modules = marketing.get_modules()
        pages = collect_pages(base, modules, marketing.get_integrations(), marketing.get_profiles())
        paths = marketing.public_paths(modules)
        issues = check_pages(pages)
        new_hash = fingerprint(pages, paths)
        changed = new_hash != (_setting("seo_content_hash") or "")
        status = (
            f"OK: {len(paths)} pages checked, no problems ({trigger})."
            if not issues
            else f"{len(issues)} problem(s) found ({trigger}):\n" + "\n".join(issues[:40])
        )
        _store(
            seo_last_checked=frappe.utils.now_datetime(),
            seo_url_count=len(paths),
            seo_status=status,
            seo_content_hash=new_hash,
        )
        if changed:
            _clear_website_cache()
            if _indexnow_enabled():
                frappe.enqueue(
                    "reckon_saas_platform.seo.notify_search_engines",
                    queue="short",
                    enqueue_after_commit=True,
                )
        return {"changed": changed, "issues": issues, "pages": len(paths)}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SEO refresh")
        return {}


def refresh_seo_daily() -> None:
    refresh_seo("daily")


def get_indexnow_key() -> str:
    """The IndexNow key, generated once and kept in SaaS Platform Settings."""
    key = str(_setting("indexnow_key") or "")
    if not re.fullmatch(r"[a-f0-9]{32}", key):
        key = hashlib.sha256(frappe.generate_hash(length=40).encode()).hexdigest()[:32]
        _store(indexnow_key=key)
    return key


def notify_search_engines() -> bool:
    """Tell IndexNow (Bing, Yandex and partners) that the public pages changed.

    Needs **Notify Search Engines** ticked and a public https address; a local or
    test address is never sent anywhere.
    """
    if not _indexnow_enabled():
        return False
    base = marketing.site_base()
    host = re.sub(r"^https?://", "", base)
    if not base.startswith("https://") or host.split(":")[0] == "localhost" or "." not in host:
        return False
    import requests

    key = get_indexnow_key()
    urls = [base + path for path in marketing.public_paths(marketing.get_modules())][:MAX_URLS_PER_NOTICE]
    try:
        response = requests.post(
            INDEXNOW_ENDPOINT,
            json={"host": host, "key": key, "keyLocation": f"{base}/{key}.txt", "urlList": urls},
            timeout=10,
        )
        ok = response.status_code in (200, 202)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IndexNow notice")
        return False
    if ok:
        _store(seo_last_notified=frappe.utils.now_datetime())
    return ok


@frappe.whitelist()
def refresh_seo_now() -> dict:
    """Button on SaaS Platform Settings: run the check now."""
    if not frappe.has_permission(SETTINGS, "write"):
        frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
    result = refresh_seo("manual")
    return {
        "pages": result.get("pages", 0),
        "issues": len(result.get("issues", [])),
        "changed": bool(result.get("changed")),
    }
