import re

import frappe

RULES = [
    (r"Bangla and English user manuals", "Multi-language user manuals"),
    (r"workspace, in Bangla or English", "workspace, with multi-language support"),
    (r"for every company, in Bangla or English", "for every company, with multi-language support"),
    (r"Screens in English and Bangla today", "Multi-language screens today"),
    (r"English and Bangla screens today", "multi-language screens today"),
    (r"English and Bangla screens", "multi-language screens"),
    (r"Bangla and English screens", "multi-language screens"),
    (r"Bangla and English, and on which channels", "multiple languages, and on which channels"),
    (r"Do they support Bangla and multiple languages", "Do they support multiple languages"),
    (r"Do they support Bangla and English", "Do they support multiple languages"),
    (r"Support in Bangla and English", "Support in multiple languages"),
    (r"in English and Bangla, and dedicated", "in multiple languages, and dedicated"),
    (r"Signup is available in Bangla and English", "Signup is available in multiple languages"),
    (r"Signup in Bangla or English", "Signup in your language"),
    (r"between Bangla and English", "between languages"),
    (r"in Bangla or English", "in your language"),
    (r"in English or Bangla", "in your language"),
    (r"in Bangla and English", "in multiple languages"),
    (r"ask in Bangla or English", "ask in your own language"),
    (r"Ask in Bangla or English", "Ask in your own language"),
    (r"speak it in English or Bangla", "speak it in your language"),
    (r"Bangla and English are both", "Multi-language support is"),
    (r"Is the whole ERP in Bangla\?", "Is the whole ERP multi-language?"),
    (r"Can I use it in Bangla\?", "Can I use it in my language?"),
    (r"Is it available in Bangla\?", "Is it available in my language?"),
    (r"in Bangla, \?", "in their own language?"),
    (r"often in Bangla", "often in their own language"),
    (r"work in Bangla while the other half work in English", "work in one language while the other half work in another"),
    (r"with Bangla labels", "with labels in your language"),
    (r"Bangla labels", "labels in your language"),
    (r"Bangla screens", "multi-language screens"),
    (r"Bangla support", "multi-language support"),
    (r"Bangla-ready", "multi-language ready"),
    (r"Bangla and English", "multi-language support"),
]


def _multi(match):
    before = match.string[max(0, match.start() - 2) : match.start()]
    return "Multi-language" if match.start() == 0 or re.search(r"(^|[>(]|[.?!] |: )$", before) else "multi-language"


def execute():
    """Published articles say "multi-language support" where they said Bangla and English, and Aura AI for the assistant."""
    if not frappe.db.exists("DocType", "SEO Article"):
        return
    for name, body in frappe.get_all("SEO Article", fields=["name", "body"], as_list=True):
        new = body or ""
        for pattern, repl in RULES:
            new = re.sub(pattern, repl, new)
        new = re.sub(r"Bangla-first", _multi, new).replace("AuraAI", "Aura AI").replace("Reckon AI", "Aura AI")
        new = new.replace("/features/reckon-ai-assistant", "/features/aura-ai-assistant").replace("/features/ask-ai", "/features/aura-ai-assistant")
        if new != body:
            frappe.db.set_value("SEO Article", name, "body", new, update_modified=False)
    frappe.clear_cache()
