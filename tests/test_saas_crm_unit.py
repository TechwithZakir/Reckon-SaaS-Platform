"""SaaS CRM: signups and subscriptions become Reckon CRM (Frappe CRM) leads and deals."""

from __future__ import annotations

import json
import unittest
from unittest.mock import Mock

from frappe_stub import REPO_ROOT, _Dict, platform_modules

APP = REPO_ROOT / "reckon_saas_platform"
NAME = "SaaS CRM"

LEAD_STATUSES = [
    _Dict(name="New", type="Open", position=1),
    _Dict(name="Contacted", type="Ongoing", position=2),
    _Dict(name="Qualified", type="Won", position=4),
    _Dict(name="Unqualified", type="Lost", position=5),
]
DEAL_STATUSES = [
    _Dict(name="Qualification", type="Open", position=1),
    _Dict(name="Demo/Making", type="Ongoing", position=2),
    _Dict(name="Won", type="Won", position=6),
    _Dict(name="Lost", type="Lost", position=7),
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class FakeDoc(_Dict):
    """A Frappe document stand-in that records saves and inserts."""

    def __init__(self, **values):
        super().__init__(**values)
        self["saves"] = 0

    def update(self, values):  # noqa: D401 - dict.update with Document semantics
        dict.update(self, values)

    def save(self, **kwargs):
        self["saves"] += 1
        return self

    def insert(self, **kwargs):
        self.setdefault("name", f"{self.get('doctype')}-1")
        return self


def crm_site(frappe, *, apps=("frappe", "erpnext", "crm"), sync=1, records=None, values=None):
    """Point the frappe stub at a site with Frappe CRM installed."""
    records = records if records is not None else {}
    values = values if values is not None else {}
    inserted: list[FakeDoc] = []
    frappe.get_installed_apps = Mock(return_value=list(apps))
    frappe.db.exists = Mock(side_effect=lambda doctype, name=None: doctype == "DocType" or (doctype, name) in records)
    frappe.db.has_column = Mock(return_value=True)
    frappe.db.get_single_value = Mock(
        side_effect=lambda dt, field: {"crm_sync_enabled": sync, "crm_lead_source": "SaaS Signup"}.get(field)
    )

    def get_all(doctype, **kwargs):
        if doctype == "CRM Lead Status":
            return LEAD_STATUSES
        if doctype == "CRM Deal Status":
            return DEAL_STATUSES
        return []

    frappe.get_all = Mock(side_effect=get_all)

    def get_value(doctype, filters, field=None, *args, **kwargs):
        if field == "type":
            statuses = LEAD_STATUSES if doctype == "CRM Lead Status" else DEAL_STATUSES
            return next((s.type for s in statuses if s.name == filters), None)
        return values.get((doctype, json.dumps(filters, sort_keys=True, default=str)))

    frappe.db.get_value = Mock(side_effect=get_value)

    def get_doc(doctype, name=None, **kwargs):
        if isinstance(doctype, dict):
            doc = FakeDoc(**doctype)
            inserted.append(doc)
            return doc
        return records[(doctype, name)]

    frappe.get_doc = Mock(side_effect=get_doc)
    return inserted


def key(doctype, filters):
    return (doctype, json.dumps(filters, sort_keys=True, default=str))


REGISTRATION = _Dict(
    name="REG-00001",
    business_name="Acme Traders",
    owner_name="Rahim Uddin Khan",
    owner_email="rahim@acme.test",
    owner_phone="+8801700000000",
    saas_module="distribution",
    status="Pending Verification",
    company="",
    subscription="",
)


class ModuleLayoutTests(unittest.TestCase):
    def test_module_is_registered_with_its_page(self):
        self.assertIn(NAME, (APP / "modules.txt").read_text(encoding="utf-8").splitlines())
        page = read(APP / "saas_crm" / "page" / "saas_crm" / "saas_crm.json")
        self.assertEqual((page["name"], page["module"], page["standard"]), ("saas-crm", NAME, "Yes"))
        self.assertEqual({r["role"] for r in page["roles"]}, {"Reckon Vendor Superuser", "System Manager"})
        script = (APP / "saas_crm" / "page" / "saas_crm" / "saas_crm.js").read_text(encoding="utf-8")
        self.assertIn('frappe.pages["saas-crm"].on_page_load', script)
        self.assertNotIn("window.open", script)

    def test_builds_on_crm_records_instead_of_its_own_lead_doctypes(self):
        self.assertFalse((APP / "saas_crm" / "doctype").exists())
        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        for needle in (
            "reckon_saas_platform.crm_sync.on_registration_insert",
            "reckon_saas_platform.crm_sync.on_registration_update",
            "reckon_saas_platform.crm_sync.on_subscription_update",
            '"CRM Lead": "reckon_saas_platform.crm_tenant.lead_query"',
            '"reckon_saas_platform.crm_tenant.has_permission"',
            '"reckon_saas_platform.crm_tenant.bind_company"',
        ):
            self.assertIn(needle, hooks)
        # Frappe CRM stays optional: the platform installs without it.
        self.assertNotIn('"crm"', hooks.split("required_apps")[1].splitlines()[0])

    def test_settings_have_the_crm_section(self):
        settings = read(APP / "saas_platform" / "doctype" / "saas_platform_settings" / "saas_platform_settings.json")
        fields = {f["fieldname"]: f for f in settings["fields"]}
        for name in ("section_saas_crm", "crm_sync_enabled", "crm_lead_owner", "crm_lead_source"):
            self.assertIn(name, fields)
            self.assertIn(name, settings["field_order"])
        self.assertEqual(fields["crm_sync_enabled"]["default"], "1")

    def test_workspace_and_rail_list_the_crm_before_the_seo_agent(self):
        workspace = read(APP / "saas_platform" / "workspace" / "reckon_saas_admin" / "reckon_saas_admin.json")
        labels = [s["label"] for s in workspace["shortcuts"]]
        self.assertLess(labels.index("CRM Pipeline"), labels.index("SEO Agent"))
        blocks = json.loads(workspace["content"])
        self.assertEqual([b["data"]["shortcut_name"] for b in blocks if b["type"] == "shortcut"], labels)
        rail = read(APP / "workspace_sidebar" / "saas_platform.json")
        rail_labels = [i["label"] for i in rail["items"]]
        self.assertEqual(rail_labels[rail_labels.index(NAME) + 1], "CRM Pipeline")
        self.assertLess(rail_labels.index(NAME), rail_labels.index("SEO Agent Studio"))


class InstallTests(unittest.TestCase):
    def _workspace(self, apps):
        with platform_modules("install") as (frappe, (install,)):
            frappe.get_installed_apps = Mock(return_value=list(apps))
            return install._workspace_doc()

    def test_crm_links_appear_only_with_the_crm_apps(self):
        bare = self._workspace(["frappe", "erpnext", "reckon_saas_platform"])
        labels = [s["label"] for s in bare["shortcuts"]]
        self.assertIn("CRM Pipeline", labels)  # the page explains what to install
        for label in ("CRM Leads", "CRM Deals", "Field Visits"):
            self.assertNotIn(label, labels)
        names = [b["data"]["shortcut_name"] for b in json.loads(bare["content"]) if b["type"] == "shortcut"]
        self.assertEqual(names, labels)

        crm_only = [s["label"] for s in self._workspace(["frappe", "crm"])["shortcuts"]]
        self.assertIn("CRM Deals", crm_only)
        self.assertNotIn("Field Visits", crm_only)
        full = [s["label"] for s in self._workspace(["frappe", "crm", "reckon_crm"])["shortcuts"]]
        self.assertIn("Field Visits", full)

    def test_custom_fields_wait_for_frappe_crm(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            frappe.get_installed_apps = Mock(return_value=["frappe", "erpnext"])
            self.assertFalse(crm.ensure_crm_custom_fields())
        self.assertEqual(
            {f["fieldname"] for f in crm.CUSTOM_FIELDS["CRM Lead"]} >= {crm.LEAD_REGISTRATION, crm.LEAD_MODULE}, True
        )
        self.assertIn(crm.DEAL_SUBSCRIPTION, {f["fieldname"] for f in crm.CUSTOM_FIELDS["CRM Deal"]})


class StageTests(unittest.TestCase):
    def test_stages_are_picked_by_type_not_name(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            crm_site(frappe)
            self.assertEqual(crm.pick_status("CRM Deal Status", ("Open", "Ongoing")), "Qualification")
            self.assertEqual(crm.pick_status("CRM Deal Status", "Won"), "Won")
            self.assertEqual(crm.pick_status("CRM Lead Status", "Lost"), "Unqualified")
            self.assertIsNone(crm.pick_status("CRM Lead Status", "On Hold"))

    def test_subscription_status_decides_the_deal_stage(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            self.assertEqual(crm.target_deal_status_type("Active"), "Won")
            self.assertEqual(crm.target_deal_status_type("Cancelled"), "Lost")
            self.assertEqual(crm.target_deal_status_type("Expired"), "Lost")
            for status in ("Trial", "Pending", "Due", "Grace", "Suspended"):
                self.assertIsNone(crm.target_deal_status_type(status), status)

    def test_deal_value_is_yearly(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            self.assertEqual(crm.yearly_value(1000, "Monthly"), 12000)
            self.assertEqual(crm.yearly_value(2500, "Quarterly"), 10000)
            self.assertEqual(crm.yearly_value(9000, "Yearly"), 9000)
            self.assertEqual(crm.yearly_value(None, None), 0)


class LeadSyncTests(unittest.TestCase):
    def test_signup_creates_an_open_lead(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            inserted = crm_site(frappe, records={("CRM Lead Source", "SaaS Signup"): True})
            crm.on_registration_insert(REGISTRATION)
        lead = next(d for d in inserted if d["doctype"] == "CRM Lead")
        self.assertEqual((lead["first_name"], lead["last_name"]), ("Rahim", "Uddin Khan"))
        self.assertEqual(lead["status"], "New")
        self.assertEqual(lead["organization"], "Acme Traders")
        self.assertEqual(lead["source"], "SaaS Signup")
        self.assertEqual(lead[crm.LEAD_REGISTRATION], "REG-00001")
        self.assertEqual(lead[crm.LEAD_MODULE], "distribution")
        frappe.log_error.assert_not_called()

    def test_an_existing_lead_with_the_same_email_is_reused(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            existing = FakeDoc(name="CRM-LEAD-1", email=REGISTRATION.owner_email, status="Contacted")
            inserted = crm_site(
                frappe,
                records={("CRM Lead", "CRM-LEAD-1"): existing},
                values={
                    key("CRM Lead", {"email": REGISTRATION.owner_email, crm.LEAD_REGISTRATION: ["is", "not set"]}): "CRM-LEAD-1"
                },
            )
            self.assertEqual(crm.upsert_lead(REGISTRATION), "CRM-LEAD-1")
        self.assertEqual(inserted, [])
        self.assertEqual(existing[crm.LEAD_REGISTRATION], "REG-00001")
        self.assertEqual(existing["status"], "Contacted")  # the team's own stage is kept
        self.assertEqual(existing["saves"], 1)

    def test_nothing_happens_without_crm_or_when_switched_off(self):
        for apps, sync in ((("frappe", "erpnext"), 1), (("frappe", "crm"), 0)):
            with platform_modules("crm_sync") as (frappe, (crm,)):
                inserted = crm_site(frappe, apps=apps, sync=sync)
                crm.on_registration_insert(REGISTRATION)
                self.assertEqual(inserted, [], (apps, sync))

    def test_a_crm_error_never_breaks_signup(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            crm_site(frappe)
            frappe.get_doc = Mock(side_effect=RuntimeError("CRM validation failed"))
            crm.on_registration_insert(REGISTRATION)  # does not raise
            frappe.log_error.assert_called_once()
            self.assertIn("SaaS CRM", frappe.log_error.call_args.args[1])

    def test_rejected_registration_closes_the_lead_as_lost(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            lead = FakeDoc(name="CRM-LEAD-1", status="New", converted=0)
            crm_site(
                frappe,
                records={("CRM Lead", "CRM-LEAD-1"): lead},
                values={key("CRM Lead", {crm.LEAD_REGISTRATION: "REG-00001"}): "CRM-LEAD-1"},
            )
            crm.sync_registration(_Dict(REGISTRATION, status="Rejected"))
        self.assertEqual(lead["status"], "Unqualified")
        self.assertEqual(lead["lost_notes"], "Registration rejected")


class DealSyncTests(unittest.TestCase):
    def _site(self, frappe, crm, deal_status):
        deal = FakeDoc(name="CRM-DEAL-1", status=deal_status, deal_value=0)
        crm_site(
            frappe,
            records={("CRM Deal", "CRM-DEAL-1"): deal},
            values={key("CRM Deal", {crm.DEAL_SUBSCRIPTION: "SUB-00001"}): "CRM-DEAL-1"},
        )
        return deal

    def _subscription(self, status):
        return _Dict(name="SUB-00001", registration="REG-00001", company="Acme Traders", saas_module="distribution",
                     status=status, price=1000, billing_cycle="Monthly", currency="BDT")

    def test_paid_subscription_wins_the_deal(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            deal = self._site(frappe, crm, "Demo/Making")
            crm.sync_subscription(self._subscription("Active"))
        self.assertEqual(deal["status"], "Won")
        self.assertEqual(deal["probability"], 100)
        self.assertEqual((deal["deal_value"], deal["currency"]), (12000, "BDT"))
        self.assertEqual(deal[crm.DEAL_COMPANY], "Acme Traders")

    def test_trial_keeps_the_stage_the_team_chose(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            deal = self._site(frappe, crm, "Demo/Making")
            crm.sync_subscription(self._subscription("Trial"))
        self.assertEqual(deal["status"], "Demo/Making")
        self.assertEqual(deal["deal_value"], 12000)

    def test_cancelled_subscription_loses_the_deal_and_a_restart_reopens_it(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            deal = self._site(frappe, crm, "Won")
            crm.sync_subscription(self._subscription("Cancelled"))
            self.assertEqual((deal["status"], deal["lost_notes"]), ("Lost", "Subscription cancelled"))
            crm.sync_subscription(self._subscription("Trial"))
            self.assertEqual(deal["status"], "Qualification")

    def test_unchanged_deal_is_not_saved_again(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            deal = self._site(frappe, crm, "Won")
            crm.sync_subscription(self._subscription("Active"))
            saves = deal["saves"]
            crm.sync_subscription(self._subscription("Active"))
        self.assertEqual(deal["saves"], saves)


class PermissionTests(unittest.TestCase):
    def test_page_api_is_vendor_only(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            frappe.session.user = "tenant@acme.test"
            frappe.get_roles = Mock(return_value=["Sales Manager"])
            with self.assertRaises(frappe.PermissionError):
                crm.get_overview()
            with self.assertRaises(frappe.PermissionError):
                crm.sync_now()

    def test_overview_without_crm_says_so(self):
        with platform_modules("crm_sync") as (frappe, (crm,)):
            crm_site(frappe, apps=("frappe", "erpnext"))
            overview = crm.get_overview()
        self.assertFalse(overview["crm_installed"])
        self.assertEqual(overview["deals"], [])


if __name__ == "__main__":
    unittest.main()


class CrmFeatureLabelTests(unittest.TestCase):
    """Reckon CRM's ``reckon_saas_modules`` features read well on the public pages."""

    def test_marketing_labels(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            self.assertEqual(marketing.feature_label("gps_visit_check_in"), "GPS check-in and check-out")
            self.assertEqual(marketing.feature_label("crm_leads_and_deals"), "Leads and deals pipeline")

    def test_signup_page_spells_gps(self):
        with platform_modules("www.reckonerp_signup") as (_frappe, (page,)):
            self.assertEqual(page._feature_label("gps_visit_check_in"), "GPS visit check in")
