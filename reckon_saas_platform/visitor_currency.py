"""Which currency to open the plans in: Taka for visitors in Bangladesh, US dollars for everyone else.

The country comes from the network provider's header when the site sits behind one, else from the visitor's IP address looked
up in our own table (see ``geoip``). The page asks for it after it loads, because pages are cached and must look the same for
everyone until then. Nothing is sent to any outside service.
"""

from __future__ import annotations

import re

import frappe
from frappe.rate_limiter import rate_limit

HOME_COUNTRY, HOME_CURRENCY, DEFAULT_CURRENCY = "BD", "BDT", "USD"


def currency_for(country_code: str) -> str:
    """BDT for Bangladesh, USD for any other or unknown country."""
    return HOME_CURRENCY if str(country_code or "").strip().upper() == HOME_COUNTRY else DEFAULT_CURRENCY


def _header_country(read_header) -> str:
    code = (read_header("CF-IPCountry") or read_header("X-Country-Code") or "").strip().upper()
    return code if re.fullmatch(r"[A-Z]{2}", code) and code not in ("XX", "T1") else ""


def visitor_country(read_header, ip: str, lookup) -> str:
    """Two-letter country: the provider header first, then the IP table. Empty when neither knows."""
    return _header_country(read_header) or (lookup(ip) if ip else "") or ""


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=120, seconds=60 * 60)
def visitor_currency() -> dict:
    """The visitor's country and the currency to open plans in. Empty when the country cannot be told."""
    from reckon_saas_platform import geoip, signup_leads

    code = visitor_country(frappe.get_request_header, signup_leads._visitor_ip(), geoip.lookup)
    return {"country": code, "currency": currency_for(code) if code else ""}
