"""Signup visitors who gave their details but did not finish: a lead in the seller company's CRM, with their visit history.

The signup page sends what a visitor has typed once it holds a usable email address or mobile number, together with the
pages they looked at, the currency and language they chose and the modules they went through (kept in their own browser
until then). The lead goes to the CRM of the seller company (SaaS Platform Settings, CRM Leads from Signup). When the
same person comes back on a later day, the same lead gets a new entry in its visit log instead of a second lead. A
visitor who submits the form is marked as having completed signup.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, validate_email_address

LEAD = "CRM Lead"
DEFAULT_SOURCE = "ReckonERP Signup (not completed)"
MAX_EVENTS = 150
LOG_MARK = "Visit log"  # every visit entry on a lead starts with this, so the next visit can find today's


def _settings():
    return frappe.get_cached_doc("SaaS Platform Settings")


def seller_company() -> str | None:
    """The company that owns these leads: the one chosen in Settings, else the one that sells (posts invoices)."""
    settings = _settings()
    company = settings.get("crm_leads_company") or settings.get("erp_company")
    return company if company and frappe.db.exists("Company", company) else None


def enabled() -> bool:
    try:
        return bool(cint(_settings().get("crm_leads_enabled")) and frappe.db.exists("DocType", LEAD) and seller_company())
    except Exception:
        return False


def _clean(value, limit=140) -> str:
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(value or "")).strip()[:limit]


def _phone(value) -> str:
    from reckon_saas_platform.sms import normalize_international_mobile

    digits = normalize_international_mobile(_clean(value, 30)) if value else None
    return f"+{digits}" if digits else ""


def _email(value) -> str:
    email = _clean(value, 140).lower()
    return email if email and validate_email_address(email) else ""


def _as_admin(fn):
    """Run as Administrator: the visitor is a Guest, and the CRM's company rules only let system users set the company."""
    caller = frappe.session.user
    frappe.set_user("Administrator")
    try:
        return fn()
    finally:
        frappe.set_user(caller)


def _ensure_source() -> str:
    source = _clean(_settings().get("crm_lead_source"), 140) or DEFAULT_SOURCE
    if not frappe.db.exists("CRM Lead Source", source):
        frappe.get_doc({"doctype": "CRM Lead Source", "source_name": source}).insert(ignore_permissions=True)
    return source


def _find_lead(company: str, email: str, phone: str) -> str | None:
    for field, value in (("email", email), ("mobile_no", phone)):
        if value:
            name = frappe.db.get_value(LEAD, {"company": company, field: value}, "name")
            if name:
                return name
    return None


def _already_signed_up(email: str, phone: str) -> bool:
    """A person who already submitted the signup form is a customer in the making, not an abandoned visit."""
    for field, value in (("owner_email", email), ("owner_phone", phone.lstrip("+"))):
        if value and frappe.db.exists("SaaS Registration", {field: value}):
            return True
    return False


def _interest(module, plan) -> str:
    return ", ".join(part for part in (_clean(module, 60), _clean(plan, 80)) if part) or "no module chosen yet"


# ---- what is known about the visit -------------------------------------------------------------------------
def _visitor_ip() -> str:
    """The visitor's address as the server sees it (first hop of X-Forwarded-For behind nginx), or empty."""
    import ipaddress

    raw = (frappe.get_request_header("X-Forwarded-For") or "").split(",")[0].strip() or str(getattr(frappe.local, "request_ip", "") or "")
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return ""


def _zone_countries() -> dict:
    """Time zone name -> two-letter country code, from the server's own zone table (no outside lookup)."""
    table = {}
    for path in ("/usr/share/zoneinfo/zone.tab", "/usr/share/zoneinfo/zone1970.tab"):
        try:
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("#") or not line.strip():
                        continue
                    cols = line.rstrip("\n").split("\t")
                    if len(cols) >= 3:
                        for code in cols[0].split(","):
                            table.setdefault(cols[2], code)
        except OSError:
            continue
    return table


def _country(timezone_name: str) -> str:
    """The visitor's country: the network provider's header when the site sits behind one that sets it, else the
    country of the browser's time zone. Nothing is sent to a third party to work it out."""
    code = (frappe.get_request_header("CF-IPCountry") or frappe.get_request_header("X-Country-Code") or "").strip().upper()
    how = "network header"
    if not re.fullmatch(r"[A-Z]{2}", code or ""):
        code, how = _zone_countries().get(_clean(timezone_name, 60), ""), "browser time zone"
    if not code:
        return ""
    name = frappe.db.get_value("Country", {"code": code.lower()}, "name") or code
    return f"{name} ({how})"


def _device(agent: str) -> str:
    agent = agent or ""
    os_name = next((n for k, n in (("Windows", "Windows"), ("Android", "Android"), ("iPhone", "iPhone"), ("iPad", "iPad"), ("Mac OS", "macOS"), ("Linux", "Linux")) if k in agent), "")
    browser = next((n for k, n in (("Edg/", "Edge"), ("OPR/", "Opera"), ("Chrome/", "Chrome"), ("Firefox/", "Firefox"), ("Safari/", "Safari")) if k in agent), "")
    return ", ".join(x for x in (browser, os_name) if x)


def _ip_country(ip: str) -> str:
    """The country the visitor's IP address belongs to, from the table on our own server."""
    from reckon_saas_platform import geoip

    code = geoip.lookup(ip) if ip else ""
    if not code:
        return ""
    return f"{frappe.db.get_value('Country', {'code': code.lower()}, 'name') or code} (IP address)"


def visit_details(tz=None, language=None, referrer=None, page=None, screen=None) -> list[tuple[str, str]]:
    """What is known about this visit, for the lead. Empty when the setting is off."""
    from frappe.utils import now_datetime

    if not cint(_settings().get("crm_capture_visit_details")):
        return []
    page = _clean(page, 300)
    ip = _visitor_ip()
    tags = ", ".join(f"{k}={v}" for k, v in re.findall(r"[?&](utm_[a-z]+|gclid|fbclid)=([^&#]{1,60})", page))
    rows = [
        ("Time", str(now_datetime())),
        ("IP address", ip),
        ("IP country", _ip_country(ip)),
        ("Country", _country(tz)),
        ("Time zone", _clean(tz, 60)),
        ("Language", _clean(language, 40) or _clean((frappe.get_request_header("Accept-Language") or "").split(",")[0], 20)),
        ("Device", _device(frappe.get_request_header("User-Agent") or "")),
        ("Screen", _clean(screen, 20)),
        ("Came from", _clean(referrer, 200)),
        ("Page", page.split("#")[0]),
        ("Campaign tags", tags),
    ]
    return [(label, value) for label, value in rows if value]


# ---- the pages, language, currency and modules the visitor went through ---------------------------------------
LANGUAGES = {"en": "English", "bn": "Bangla"}


def parse_trail(raw) -> list[dict]:
    """The visitor's activity as sent by the page, cleaned: known kinds only, short strings, at most MAX_EVENTS."""
    try:
        items = json.loads(raw) if isinstance(raw, str) else (raw or [])
    except ValueError:
        return []
    events = []
    for item in (items if isinstance(items, list) else [])[-MAX_EVENTS:]:
        if not isinstance(item, dict) or item.get("e") not in ("view", "cur", "cycle", "lang", "module", "plan"):
            continue
        try:
            at = datetime.fromtimestamp(int(item.get("t")) / 1000, tz=timezone.utc)
        except (TypeError, ValueError, OverflowError, OSError):
            continue
        events.append(
            {"at": at, "e": item["e"], "v": _clean(item.get("v"), 100), "p": _clean(item.get("p"), 120), "l": _clean(item.get("l"), 5).lower()}
        )
    return events


def _local(at: datetime) -> str:
    from frappe.utils import convert_utc_to_system_timezone

    try:
        return convert_utc_to_system_timezone(at.replace(tzinfo=None)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return at.strftime("%Y-%m-%d %H:%M UTC")


def describe(event: dict) -> str:
    kind, value, path = event["e"], event["v"], event["p"]
    if kind == "view":
        lang = LANGUAGES.get(event["l"][:2], "")
        return f"Viewed {path or '/'}" + (f" ({value})" if value else "") + (f" in {lang}" if lang else "")
    return {
        "cur": f"Chose currency {value}",
        "cycle": f"Chose billing period {value}",
        "lang": f"Switched language to {LANGUAGES.get(value[:2].lower(), value)}",
        "module": f"Picked module {value}",
        "plan": f"Picked plan {value}",
    }[kind]


def trail_summary(events: list[dict]) -> list[tuple[str, str]]:
    """The short version of the activity: languages, currencies, modules and pages."""
    langs, currencies, modules, pages = [], [], [], set()
    for ev in events:
        if ev["e"] == "view":
            pages.add(ev["p"])
            if LANGUAGES.get(ev["l"][:2]) and LANGUAGES[ev["l"][:2]] not in langs:
                langs.append(LANGUAGES[ev["l"][:2]])
            match = re.match(r"/(?:bn/)?modules/([a-z0-9_-]+)", ev["p"])
            if match and match.group(1) not in modules:
                modules.append(match.group(1))
        elif ev["e"] == "lang" and LANGUAGES.get(ev["v"][:2].lower()) and LANGUAGES[ev["v"][:2].lower()] not in langs:
            langs.append(LANGUAGES[ev["v"][:2].lower()])
        elif ev["e"] == "cur" and ev["v"] not in currencies:
            currencies.append(ev["v"])
        elif ev["e"] == "module" and ev["v"] not in modules:
            modules.append(ev["v"])
    rows = [
        ("Languages used", ", ".join(langs)),
        ("Currencies chosen", ", ".join(currencies)),
        ("Modules looked at", ", ".join(modules)),
        ("Pages viewed", str(len(pages)) if pages else ""),
    ]
    return [(label, value) for label, value in rows if value]


def _html(rows) -> str:
    from frappe.utils import escape_html

    return "<br>".join(f"<b>{escape_html(label)}:</b> {escape_html(value)}" for label, value in rows if value)


def _trail_html(events: list[dict]) -> str:
    from frappe.utils import escape_html

    if not events:
        return ""
    lines = [f"{escape_html(_local(ev['at']))} &nbsp;{escape_html(describe(ev))}" for ev in events]
    return "<br><b>" + escape_html(_("Activity")) + ":</b><br>" + "<br>".join(lines)


def _visit_log_html(rows, events) -> str:
    summary = _html(trail_summary(events))
    return "<br>".join(part for part in (_html(rows), summary) if part) + _trail_html(events)


# ---- the endpoint ---------------------------------------------------------------------------------------------
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=40, seconds=60 * 60)
def capture(business_name=None, owner_name=None, owner_email=None, owner_phone=None, module=None, plan=None, website=None,
            timezone=None, language=None, referrer=None, page=None, screen=None, trail=None):
    """Save the lead for a signup that has not been submitted, or add this visit to the log of the lead it already has.

    Quiet by design: it never shows the visitor an error.
    """
    if website:  # a field real visitors never see: only bots fill it
        return {"saved": False}
    if not enabled():
        return {"saved": False}
    email, phone = _email(owner_email), _phone(owner_phone)
    if not email and not phone:
        return {"saved": False}
    if _already_signed_up(email, phone):
        return {"saved": False}
    values = {"organization": _clean(business_name), "name": _clean(owner_name)}
    interest = _interest(module, plan)
    events = parse_trail(trail)
    log = _visit_log_html(visit_details(timezone, language, referrer, page, screen), events)

    def today_has_log(lead_name) -> bool:
        today = frappe.utils.nowdate()
        return bool(
            frappe.db.exists(
                "Comment",
                {"reference_doctype": LEAD, "reference_name": lead_name, "comment_type": "Comment", "content": ["like", f"%{LOG_MARK}%"], "creation": [">=", f"{today} 00:00:00"]},
            )
        )

    def save():
        company = seller_company()
        existing = _find_lead(company, email, phone)
        if existing:
            lead = frappe.get_doc(LEAD, existing)
            if lead.get("status") in ("Converted", "Junk"):
                return {"saved": False}
            changed = False
            for field, value in (("organization", values["organization"]), ("first_name", values["name"]), ("email", email), ("mobile_no", phone)):
                if value and not lead.get(field):
                    lead.set(field, value)
                    changed = True
            if changed:
                lead.save(ignore_permissions=True)
            # A person coming back is one more line in the log, not another lead. Several entries on the same day
            # are only added when there is new activity to report.
            if events or not today_has_log(existing):
                lead.add_comment("Comment", f"<b>{_(LOG_MARK)}</b> — " + _("came back to the signup page. Interested in: {0}.").format(interest) + "<br>" + log)
            return {"saved": True, "lead": existing, "returning": True}
        lead = frappe.get_doc(
            {
                "doctype": LEAD,
                "company": company,
                "first_name": values["name"] or values["organization"] or (email.split("@")[0] if email else phone),
                "organization": values["organization"],
                "email": email or None,
                "mobile_no": phone or None,
                "source": _ensure_source(),
                "status": "New",
            }
        )
        lead.insert(ignore_permissions=True)
        lead.add_comment(
            "Comment",
            f"<b>{_(LOG_MARK)}</b> — "
            + _("started signing up on /reckonerp-signup and did not finish. Interested in: {0}. Follow up to help them complete it.").format(interest)
            + "<br>"
            + log,
        )
        return {"saved": True, "lead": lead.name}

    try:
        return _as_admin(save)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Signup lead capture")
        return {"saved": False}


def mark_signup_submitted(registration, method=None) -> None:
    """``SaaS Registration.after_insert``: the visitor submitted the form, so their lead is no longer an abandoned one."""
    try:
        if not enabled():
            return
        email = _email(registration.get("owner_email"))
        phone = _phone("+" + str(registration.get("owner_phone") or "").lstrip("+")) if registration.get("owner_phone") else ""

        def mark():
            lead = _find_lead(seller_company(), email, phone)
            if not lead:
                return
            frappe.db.set_value(LEAD, lead, "status", "Converted", update_modified=True)
            frappe.get_doc(LEAD, lead).add_comment("Comment", _("Completed signup: {0}.").format(registration.name))

        _as_admin(mark)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Mark signup lead converted")
