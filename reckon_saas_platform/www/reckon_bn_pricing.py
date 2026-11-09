"""Bangla edition of ``reckon_pricing``: same page, its own route name so it has its own cached copy.

Frappe keeps one cached copy per route name, and this route can also be opened by its raw name
(``/reckon_bn_pricing``). The language is therefore fixed here instead of being read from the address,
so whichever address renders it first, the cached copy is always Bangla.
"""

import frappe

from reckon_saas_platform.www import reckon_pricing as _english_page


def get_context(context):
    frappe.local.reckon_forced_lang = "bn"
    return _english_page.get_context(context)
