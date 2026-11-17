import json
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from frappe_stub import REPO_ROOT, _Dict, platform_modules

PKG = REPO_ROOT / "reckon_saas_platform"


def event(kind, value="", path="/", lang="en", minutes=0):
    at = datetime(2026, 11, 17, 10, minutes, tzinfo=timezone.utc)
    return {"t": int(at.timestamp() * 1000), "e": kind, "v": value, "p": path, "l": lang}


class TrailTests(unittest.TestCase):
    def test_the_trail_is_cleaned_and_described(self):
        with platform_modules("signup_leads") as (_f, (leads,)):
            raw = json.dumps([
                event("view", "Pricing", "/pricing"), event("cur", "USD", "/pricing"), event("lang", "bn", "/pricing"),
                event("view", "Distribution", "/bn/modules/distribution", "bn"), event("module", "distribution", "/reckonerp-signup"),
                {"t": 1, "e": "evil", "v": "<script>"}, {"e": "view"}, "junk",
            ])
            events = leads.parse_trail(raw)
            self.assertEqual([e["e"] for e in events], ["view", "cur", "lang", "view", "module"])  # unknown kinds are dropped
            self.assertIn("Viewed /pricing (Pricing) in English", leads.describe(events[0]))
            self.assertEqual(leads.describe(events[1]), "Chose currency USD")
            self.assertEqual(leads.describe(events[2]), "Switched language to Bangla")
            summary = dict(leads.trail_summary(events))
            self.assertEqual(summary["Languages used"], "English, Bangla")
            self.assertEqual(summary["Currencies chosen"], "USD")
            self.assertEqual(summary["Modules looked at"], "distribution")
            self.assertEqual(summary["Pages viewed"], "2")
            self.assertEqual(leads.parse_trail("not json"), [])
            self.assertEqual(len(leads.parse_trail(json.dumps([event("view")] * 400))), leads.MAX_EVENTS)

    def test_the_log_is_escaped_html(self):
        with platform_modules("signup_leads") as (frappe, (leads,)):
            frappe.utils.escape_html = lambda s: str(s).replace("<", "&lt;").replace(">", "&gt;")
            html = leads._visit_log_html([("Page", "<b>x</b>")], [])
            self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)


class CaptureTests(unittest.TestCase):
    def run_capture(self, existing=None, signed_up=False, enabled=True, today_log=False, **kw):
        with platform_modules("signup_leads") as (frappe, (leads,)):
            made, comments = [], []
            lead_doc = _Dict(name="CRM-LEAD-1", status="New", get=lambda k, d=None: {"status": "New"}.get(k, d), set=Mock(), save=Mock(),
                             add_comment=lambda kind, text: comments.append(text))
            frappe.get_doc = Mock(side_effect=lambda *a: lead_doc if len(a) == 2 else _Dict(**a[0], insert=lambda **k: made.append(a[0]), add_comment=lambda kind, text: comments.append(text), name="CRM-LEAD-NEW"))
            frappe.db.exists = Mock(side_effect=lambda dt, *a: signed_up if dt == "SaaS Registration" else (today_log if dt == "Comment" else True))
            frappe.db.get_value = Mock(return_value=existing)
            frappe.utils.nowdate = lambda: "2026-11-17"
            frappe.utils.convert_utc_to_system_timezone = lambda d: d
            frappe.utils.escape_html = lambda s: str(s)
            frappe.get_request_header = lambda name: None
            frappe.set_user = Mock()
            frappe.session = _Dict(user="Guest")
            with patch.object(leads, "enabled", return_value=enabled), patch.object(leads, "seller_company", return_value="Reckon Technologies Ltd."), \
                    patch.object(leads, "_ensure_source", return_value="ReckonERP Signup (not completed)"), patch.object(leads, "visit_details", return_value=[("IP address", "203.0.113.5")]):
                result = leads.capture(**{"owner_email": "buyer@example.com", "owner_name": "Buyer", "business_name": "Acme", "module": "distribution", **kw})
            return result, made, comments

    def test_a_new_visitor_becomes_a_lead_of_the_seller_company_with_a_log(self):
        result, made, comments = self.run_capture()
        self.assertEqual(result["saved"], True)
        lead = made[0]
        self.assertEqual((lead["doctype"], lead["company"], lead["email"], lead["organization"], lead["status"]), ("CRM Lead", "Reckon Technologies Ltd.", "buyer@example.com", "Acme", "New"))
        self.assertIn("Visit log", comments[0])
        self.assertIn("203.0.113.5", comments[0])

    def test_the_same_person_next_day_adds_to_the_log_and_makes_no_second_lead(self):
        result, made, comments = self.run_capture(existing="CRM-LEAD-1")
        self.assertEqual((result["saved"], result.get("returning")), (True, True))
        self.assertEqual(made, [])
        self.assertIn("came back", comments[0])

    def test_two_visits_on_one_day_log_once_unless_there_is_new_activity(self):
        _r, _m, comments = self.run_capture(existing="CRM-LEAD-1", today_log=True)
        self.assertEqual(comments, [])
        _r, _m, comments = self.run_capture(existing="CRM-LEAD-1", today_log=True, trail=json.dumps([event("view", "Pricing", "/pricing")]))
        self.assertEqual(len(comments), 1)
        self.assertIn("Viewed /pricing", comments[0])

    def test_it_saves_nothing_for_bots_unusable_details_signed_up_people_or_when_off(self):
        self.assertFalse(self.run_capture(website="http://spam")[0]["saved"])
        self.assertFalse(self.run_capture(owner_email="nope", owner_phone="")[0]["saved"])
        self.assertFalse(self.run_capture(signed_up=True)[0]["saved"])
        self.assertFalse(self.run_capture(enabled=False)[0]["saved"])


class WiringTests(unittest.TestCase):
    def test_settings_hook_page_and_policy_are_wired(self):
        meta = json.loads((PKG / "saas_platform" / "doctype" / "saas_platform_settings" / "saas_platform_settings.json").read_text(encoding="utf-8"))
        names = {f["fieldname"] for f in meta["fields"]}
        self.assertTrue({"crm_leads_enabled", "crm_leads_company", "crm_lead_source", "crm_capture_visit_details"} <= names)
        self.assertTrue({"crm_leads_enabled", "crm_leads_company"} <= set(meta["field_order"]))
        enabled = next(f for f in meta["fields"] if f["fieldname"] == "crm_leads_enabled")
        self.assertEqual(enabled["default"], "0")  # off until the owner turns it on
        self.assertIn("signup_leads.mark_signup_submitted", (PKG / "hooks.py").read_text(encoding="utf-8"))
        page = (PKG / "www" / "reckonerp_signup.html").read_text(encoding="utf-8")
        for marker in ("signup_leads.capture", "data-lead-note", "reckonTrail", "doNotTrack", 'name="website"', 'append("csrf_token", csrfToken())', "X-Frappe-CSRF-Token"):
            self.assertIn(marker, page, marker)
        chrome = (PKG / "templates" / "marketing" / "chrome_js.html").read_text(encoding="utf-8")
        for marker in ("reckon_trail", "data-cur-set", "data-cycle-set", "doNotTrack"):
            self.assertIn(marker, chrome, marker)
        legal = (PKG / "legal_pages.py").read_text(encoding="utf-8")
        self.assertIn("do not submit it, we may keep what you entered", legal)
        self.assertIn("We do not send your IP address to any other service", legal)


if __name__ == "__main__":
    unittest.main()
