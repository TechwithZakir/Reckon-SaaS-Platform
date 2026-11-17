import re

import frappe

from reckon_saas_platform.patches.multi_language_wording import RULES, _multi

FIELDS = (
    ("SaaS Plan Feature", ("feature", "value")),
    ("SaaS Plan", ("features", "description")),
    ("SaaS Module", ("description", "features", "tagline")),
)


def _reword(text):
    for pattern, repl in RULES:
        text = re.sub(pattern, repl, text)
    return re.sub(r"\bBangla-first\b", _multi, text)


def execute():
    """Plan rows and module descriptions kept in the database say "multi-language" like the rest of the site."""
    for doctype, fields in FIELDS:
        if not frappe.db.exists("DocType", doctype):
            continue
        meta = frappe.get_meta(doctype)
        names = [f for f in fields if meta.has_field(f)]
        if not names:
            continue
        for row in frappe.get_all(doctype, fields=["name", *names]):
            changes = {f: _reword(row[f]) for f in names if row.get(f) and _reword(row[f]) != row[f]}
            if changes:
                frappe.db.set_value(doctype, row["name"], changes, update_modified=False)
    frappe.clear_cache()
