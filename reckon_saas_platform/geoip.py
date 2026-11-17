"""Country of an IP address, looked up on our own server.

The data is DB-IP's free "IP to Country Lite" table (https://db-ip.com, CC BY 4.0). It is downloaded once a month,
boiled down to a few compact arrays in the site's private folder, and searched with a binary search. A visitor's
IP address is never sent to any outside service.
"""

from __future__ import annotations

import csv
import gzip
import io
import ipaddress
import os
import time
from array import array
from bisect import bisect_right
from datetime import date, timedelta

import frappe

URL = "https://download.db-ip.com/free/dbip-country-lite-{month}.csv.gz"
MAX_DOWNLOAD_BYTES = 40 * 1024 * 1024
MIN_V4_ROWS = 50_000
REFRESH_AFTER_DAYS = 35

_cache: dict = {}


def _dir() -> str:
    return frappe.get_site_path("private", "geoip")


def _path(name: str) -> str:
    return os.path.join(_dir(), name)


def _load() -> dict | None:
    """The tables from disk, once per process (reloaded when the files are replaced)."""
    stamp = os.path.getmtime(_path("v4_start.bin")) if os.path.exists(_path("v4_start.bin")) else None
    if stamp is None:
        return None
    if _cache.get("stamp") == stamp:
        return _cache
    data = {"stamp": stamp}
    for name, code in (("v4_start", "I"), ("v4_end", "I"), ("v6_start", "Q"), ("v6_end", "Q")):
        table = array(code)
        with open(_path(name + ".bin"), "rb") as handle:
            table.frombytes(handle.read())
        data[name] = table
    for name in ("v4_cc", "v6_cc"):
        with open(_path(name + ".bin"), "rb") as handle:
            data[name] = handle.read()
    _cache.clear()
    _cache.update(data)
    return _cache


def lookup(ip: str) -> str:
    """Two-letter country code of ``ip``, or "" when it is private, unknown, or the table is not downloaded yet."""
    try:
        address = ipaddress.ip_address(str(ip).strip())
    except ValueError:
        return ""
    if address.is_private or address.is_loopback or address.is_reserved or address.is_link_local:
        return ""
    data = _load()
    if not data:
        return ""
    if address.version == 4:
        value, starts, ends, codes = int(address), data["v4_start"], data["v4_end"], data["v4_cc"]
    else:
        value, starts, ends, codes = int(address) >> 64, data["v6_start"], data["v6_end"], data["v6_cc"]
    i = bisect_right(starts, value) - 1
    if i < 0 or value > ends[i]:
        return ""
    code = codes[2 * i : 2 * i + 2].decode("ascii", "ignore")
    return "" if code in ("ZZ", "") else code


def _parse(rows) -> dict:
    v4, v6 = [], []
    for row in rows:
        if len(row) < 3 or len(row[2]) != 2:
            continue
        try:
            start, end = ipaddress.ip_address(row[0]), ipaddress.ip_address(row[1])
        except ValueError:
            continue
        if start.version == 4:
            v4.append((int(start), int(end), row[2]))
        else:
            v6.append((int(start) >> 64, int(end) >> 64, row[2]))
    v4.sort()
    v6.sort()
    return {"v4": v4, "v6": v6}


def _write(tables: dict) -> None:
    os.makedirs(_dir(), exist_ok=True)
    stamp = str(int(time.time()))
    for key, code in (("v4", "I"), ("v6", "Q")):
        rows = tables[key]
        for name, values in ((f"{key}_start", array(code, (r[0] for r in rows))), (f"{key}_end", array(code, (r[1] for r in rows)))):
            tmp = _path(name + ".bin." + stamp)
            with open(tmp, "wb") as handle:
                handle.write(values.tobytes())
            os.replace(tmp, _path(name + ".bin"))
        tmp = _path(f"{key}_cc.bin.{stamp}")
        with open(tmp, "wb") as handle:
            handle.write("".join(r[2] for r in rows).encode("ascii"))
        os.replace(tmp, _path(f"{key}_cc.bin"))


def update(month: str | None = None) -> dict:
    """Download this month's table (or last month's, when it is not published yet) and replace the local copy."""
    import requests

    today = date.today()
    months = [month] if month else [today.strftime("%Y-%m"), (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")]
    last_error = None
    for name in months:
        try:
            response = requests.get(URL.format(month=name), timeout=60, stream=True)
            response.raise_for_status()
            body = b""
            for chunk in response.iter_content(1 << 16):
                body += chunk
                if len(body) > MAX_DOWNLOAD_BYTES:
                    raise ValueError("The country table is larger than expected.")
            text = io.TextIOWrapper(io.BytesIO(gzip.decompress(body)), encoding="utf-8", newline="")
            tables = _parse(csv.reader(text))
            if len(tables["v4"]) < MIN_V4_ROWS:
                raise ValueError("The country table has too few rows.")
            _write(tables)
            _cache.clear()
            return {"month": name, "ipv4_ranges": len(tables["v4"]), "ipv6_ranges": len(tables["v6"])}
        except Exception as exc:  # try the previous month, then give up quietly
            last_error = exc
    frappe.log_error(f"IP country table update failed: {last_error}", "GeoIP update")
    return {}


def refresh_if_needed() -> None:
    """Daily job: download the table when it is missing or older than a month, if signup lead capture is on."""
    try:
        if not frappe.db.get_single_value("SaaS Platform Settings", "crm_leads_enabled"):
            return
        path = _path("v4_start.bin")
        if os.path.exists(path) and time.time() - os.path.getmtime(path) < REFRESH_AFTER_DAYS * 86400:
            return
        update()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "GeoIP refresh")
