"""SaaS CRM: the vendor's sales pipeline for the platform, built on Reckon CRM.

Reckon CRM extends Frappe CRM (``/crm``) with field visits. This module feeds
the SaaS platform into those same records, so signups and subscriptions are
followed up in CRM like any other customer:

- A new **SaaS Registration** becomes a **CRM Lead** (source "SaaS Signup"),
  with its CRM Organization named after the business.
- When the workspace is provisioned, the lead is converted and a **CRM Deal** is
  opened for the subscription.
- The deal follows the subscription: a paid **Active** subscription moves it to
  the first *Won* stage, **Cancelled** or **Expired** to the first *Lost* stage.
  Stages are picked by their CRM status type, never by name, so renamed or
  reordered pipelines keep working; a manual move to another open stage is kept.
- Field visits (Reckon CRM's Visits tab) can be scheduled on those leads and
  deals; the SaaS CRM page lists the ones due.

Nothing here is required: without the ``crm`` app every hook returns at once,
and a sync problem is logged and never stops a signup, provisioning or a
subscription update. SaaS-linked leads and deals are visible to vendor users
only, so a tenant user holding a CRM role cannot read the vendor's pipeline.
"""

from __future__ import annotations

import frappe
from frappe.utils import cint, flt, getdate, nowdate

from reckon_saas_platform.constants import BILLING_CYCLE_MONTHS
from reckon_saas_platform.saas_security import is_vendor_user

SETTINGS = "SaaS Platform Settings"
LEAD = "CRM Lead"
DEAL = "CRM Deal"
ORGANIZATION = "CRM Organization"
VISIT = "CRM Field Visit"
DEFAULT_SOURCE = "SaaS Signup"

LEAD_REGISTRATION = "reckon_saas_registration"
LEAD_MODULE = "reckon_saas_module"
DEAL_SUBSCRIPTION = "reckon_saas_subscription"
DEAL_MODULE = "reckon_saas_module"
DEAL_COMPANY = "reckon_saas_company"

# Custom fields this module adds to Frappe CRM's own doctypes.
CUSTOM_FIELDS = {
    LEAD: [
        {"fieldname": "reckon_saas_section", "fieldtype": "Section Break", "label": "Reckon SaaS",
         "insert_after": "converted", "collapsible": 1},
        {"fieldname": LEAD_REGISTRATION, "fieldtype": "Link", "label": "SaaS Registration",
         "options": "SaaS Registration", "insert_after": "reckon_saas_section", "read_only": 1,
         "search_index": 1, "no_copy": 1},
        {"fieldname": LEAD_MODULE, "fieldtype": "Link", "label": "SaaS Module", "options": "SaaS Module",
         "insert_after": LEAD_REGISTRATION, "read_only": 1, "in_standard_filter": 1},
    ],
    DEAL: [
        {"fieldname": "reckon_saas_section", "fieldtype": "Section Break", "label": "Reckon SaaS",
         "insert_after": "lead", "collapsible": 1},
        {"fieldname": DEAL_SUBSCRIPTION, "fieldtype": "Link", "label": "SaaS Subscription",
         "options": "SaaS Subscription", "insert_after": "reckon_saas_section", "read_only": 1,
         "search_index": 1, "no_copy": 1},
        {"fieldname": DEAL_MODULE, "fieldtype": "Link", "label": "SaaS Module", "options": "SaaS Module",
         "insert_after": DEAL_SUBSCRIPTION, "read_only": 1, "in_standard_filter": 1},
        {"fieldname": DEAL_COMPANY, "fieldtype": "Link", "label": "Tenant Company", "options": "Company",
         "insert_after": DEAL_MODULE, "read_only": 1, "no_copy": 1},
    ],
}

# Registration statuses that end a lead without a sale.
LOST_REGISTRATION_STATUSES = frozenset({"Rejected", "Cancelled"})
# Subscription statuses that close the deal.
WON_SUBSCRIPTION_STATUSES = frozenset({"Active"})
LOST_SUBSCRIPTION_STATUSES = frozenset({"Cancelled", "Expired"})
OPEN_STATUS_TYPES = ("Open", "Ongoing")


# ---------------------------------------------------------------- availability


def crm_installed() -> bool:
    """Frappe CRM is installed and its lead and deal tables exist."""
    if "crm" not in frappe.get_installed_apps():
        return False
    return bool(frappe.db.exists("DocType", LEAD) and frappe.db.exists("DocType", DEAL))


def reckon_crm_installed() -> bool:
    """Reckon CRM's field visits are available on top of Frappe CRM."""
    return "reckon_crm" in frappe.get_installed_apps() and bool(frappe.db.exists("DocType", VISIT))


def sync_enabled() -> bool:
    if not crm_installed():
        return False
    value = frappe.db.get_single_value(SETTINGS, "crm_sync_enabled")
    # An unsaved Single reads as None: the sync is on by default.
    return value is None or bool(cint(value))


def _fields_ready() -> bool:
    return bool(frappe.db.has_column(LEAD, LEAD_REGISTRATION) and frappe.db.has_column(DEAL, DEAL_SUBSCRIPTION))


def _settings_value(fieldname: str, default=None):
    return frappe.db.get_single_value(SETTINGS, fieldname) or default


# ---------------------------------------------------------------- install


def ensure_crm_custom_fields() -> bool:
    """Add the SaaS link fields to CRM Lead and CRM Deal, and the lead source.

    Runs after every migrate and whenever an app is installed, so installing
    Frappe CRM after this app is enough. A problem is logged, never raised.
    """
    if not crm_installed():
        return False
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

        create_custom_fields(CUSTOM_FIELDS, ignore_validate=True, update=True)
        _ensure_lead_source()
        return True
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SaaS CRM custom fields")
        return False


def _ensure_lead_source() -> str | None:
    source = _settings_value("crm_lead_source", DEFAULT_SOURCE)
    if not frappe.db.exists("DocType", "CRM Lead Source"):
        return None
    if not frappe.db.exists("CRM Lead Source", source):
        frappe.get_doc({"doctype": "CRM Lead Source", "source_name": source}).insert(ignore_permissions=True)
    return source


# ---------------------------------------------------------------- stages


def pick_status(doctype: str, types: tuple[str, ...] | str) -> str | None:
    """The first CRM Lead/Deal Status (by position) whose type is one of ``types``."""
    types = (types,) if isinstance(types, str) else tuple(types)
    rows = frappe.get_all(doctype, fields=["name", "type", "position"], order_by="position asc")
    for wanted in types:
        for row in rows:
            if (row.get("type") or "Open") == wanted:
                return row.get("name")
    return None


def _status_type(doctype: str, status: str | None) -> str | None:
    if not status:
        return None
    return frappe.db.get_value(doctype, status, "type") or "Open"


# ---------------------------------------------------------------- doc events


def _run(label: str, fn, *args) -> None:
    """Run a sync step without ever failing the signup or subscription that triggered it."""
    if frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate:
        return
    if not sync_enabled() or not _fields_ready():
        return
    try:
        fn(*args)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"SaaS CRM: {label}")


def on_registration_insert(doc, method=None) -> None:
    """``SaaS Registration.after_insert``: every signup becomes a lead."""
    _run("lead from registration", upsert_lead, doc)


def on_registration_update(doc, method=None) -> None:
    """``SaaS Registration.on_update``: follow provisioning and rejections."""
    _run("registration status", sync_registration, doc)


def on_subscription_update(doc, method=None) -> None:
    """``SaaS Subscription.on_update``: the deal follows the subscription."""
    _run("deal from subscription", sync_subscription, doc)


# ---------------------------------------------------------------- leads


def _split_name(full_name: str) -> tuple[str, str]:
    parts = (full_name or "").strip().split(None, 1)
    if not parts:
        return "Signup", ""
    return parts[0], parts[1] if len(parts) > 1 else ""


def find_lead(registration) -> str | None:
    name = frappe.db.get_value(LEAD, {LEAD_REGISTRATION: registration.name}, "name")
    if name:
        return name
    # A lead the team created by hand before the signup, not yet tied to one.
    if registration.get("owner_email"):
        return frappe.db.get_value(
            LEAD, {"email": registration.owner_email, LEAD_REGISTRATION: ["is", "not set"]}, "name"
        )
    return None


def ensure_organization(business_name: str | None) -> str | None:
    business_name = (business_name or "").strip()
    if not business_name or not frappe.db.exists("DocType", ORGANIZATION):
        return None
    if not frappe.db.exists(ORGANIZATION, business_name):
        frappe.get_doc({"doctype": ORGANIZATION, "organization_name": business_name}).insert(ignore_permissions=True)
    return business_name


def upsert_lead(registration) -> str | None:
    """Create or refresh the CRM Lead for a registration; returns its name."""
    name = find_lead(registration)
    first, last = _split_name(registration.get("owner_name"))
    values = {
        "first_name": first,
        "last_name": last,
        "email": registration.get("owner_email"),
        "mobile_no": registration.get("owner_phone"),
        "organization": registration.get("business_name"),
        LEAD_REGISTRATION: registration.name,
        LEAD_MODULE: registration.get("saas_module"),
    }
    if name:
        lead = frappe.get_doc(LEAD, name)
        changed = {k: v for k, v in values.items() if v and lead.get(k) != v}
        if changed:
            lead.update(changed)
            lead.save(ignore_permissions=True)
        return name

    status = pick_status("CRM Lead Status", OPEN_STATUS_TYPES)
    if not status:
        frappe.log_error("No open CRM Lead Status exists.", "SaaS CRM: lead from registration")
        return None
    lead = frappe.get_doc(
        {
            "doctype": LEAD,
            **values,
            "status": status,
            "source": _ensure_lead_source(),
            "lead_owner": _settings_value("crm_lead_owner"),
        }
    ).insert(ignore_permissions=True)
    return lead.name


def sync_registration(registration) -> None:
    status = registration.get("status")
    if status == "Active":
        lead = upsert_lead(registration)
        if lead:
            convert_lead(lead, registration)
    elif status in LOST_REGISTRATION_STATUSES:
        lead = find_lead(registration)
        if lead:
            _close_lead(lead, f"Registration {status.lower()}")


def _close_lead(lead_name: str, note: str) -> None:
    lead = frappe.get_doc(LEAD, lead_name)
    if cint(lead.get("converted")) or _status_type("CRM Lead Status", lead.status) == "Lost":
        return
    status = pick_status("CRM Lead Status", "Lost")
    if status:
        lead.status = status
        lead.lost_notes = note
        lead.save(ignore_permissions=True)


def convert_lead(lead_name: str, registration) -> str | None:
    """Mark the lead converted and open (or reuse) its deal."""
    deal = frappe.db.get_value(DEAL, {"lead": lead_name}, "name")
    if not deal and registration.get("subscription"):
        deal = frappe.db.get_value(DEAL, {DEAL_SUBSCRIPTION: registration.subscription}, "name")
    if not deal:
        deal = _create_deal(lead_name, registration)
    lead = frappe.get_doc(LEAD, lead_name)
    if not cint(lead.get("converted")):
        lead.converted = 1
        won = pick_status("CRM Lead Status", "Won")
        if won:
            lead.status = won
        lead.save(ignore_permissions=True)
    if deal and registration.get("company"):
        frappe.db.set_value(DEAL, deal, DEAL_COMPANY, registration.company, update_modified=False)
    return deal


def _create_deal(lead_name: str, registration, subscription=None) -> str | None:
    status = pick_status("CRM Deal Status", OPEN_STATUS_TYPES)
    if not status:
        frappe.log_error("No open CRM Deal Status exists.", "SaaS CRM: deal")
        return None
    lead = frappe.get_doc(LEAD, lead_name) if lead_name else None
    values = {
        "doctype": DEAL,
        "status": status,
        "lead": lead_name,
        "organization": ensure_organization(registration.get("business_name") if registration else None),
        "email": registration.get("owner_email") if registration else None,
        "mobile_no": registration.get("owner_phone") if registration else None,
        "source": lead.get("source") if lead else None,
        "deal_owner": (lead.get("lead_owner") if lead else None) or _settings_value("crm_lead_owner"),
        DEAL_MODULE: (registration.get("saas_module") if registration else None)
        or (subscription.get("saas_module") if subscription else None),
        DEAL_COMPANY: (registration.get("company") if registration else None)
        or (subscription.get("company") if subscription else None),
    }
    sub_name = (subscription.name if subscription else None) or (registration.get("subscription") if registration else None)
    if sub_name:
        values[DEAL_SUBSCRIPTION] = sub_name
    if subscription:
        values.update(_deal_value(subscription))
    return frappe.get_doc({k: v for k, v in values.items() if v not in (None, "")}).insert(ignore_permissions=True).name


# ---------------------------------------------------------------- deals


def yearly_value(price, billing_cycle: str | None) -> float:
    """The subscription's value over a year, as CRM deal value."""
    months = BILLING_CYCLE_MONTHS.get(billing_cycle or "Monthly", 1)
    return round(flt(price) * 12 / months, 2)


def _deal_value(subscription) -> dict:
    values = {"deal_value": yearly_value(subscription.get("price"), subscription.get("billing_cycle"))}
    if subscription.get("currency"):
        values["currency"] = subscription.currency
    return values


def find_deal(subscription) -> str | None:
    deal = frappe.db.get_value(DEAL, {DEAL_SUBSCRIPTION: subscription.name}, "name")
    if deal or not subscription.get("registration"):
        return deal
    lead = frappe.db.get_value(LEAD, {LEAD_REGISTRATION: subscription.registration}, "name")
    return frappe.db.get_value(DEAL, {"lead": lead}, "name") if lead else None


def target_deal_status_type(subscription_status: str | None) -> str | None:
    """Which CRM status type a subscription status moves the deal to (None: leave it)."""
    if subscription_status in WON_SUBSCRIPTION_STATUSES:
        return "Won"
    if subscription_status in LOST_SUBSCRIPTION_STATUSES:
        return "Lost"
    return None


def sync_subscription(subscription) -> str | None:
    deal_name = find_deal(subscription)
    if not deal_name:
        registration = (
            frappe.get_doc("SaaS Registration", subscription.registration) if subscription.get("registration") else None
        )
        lead = upsert_lead(registration) if registration else None
        deal_name = _create_deal(lead, registration, subscription)
        if lead:
            frappe.db.set_value(LEAD, lead, "converted", 1, update_modified=False)
        if not deal_name:
            return None

    deal = frappe.get_doc(DEAL, deal_name)
    updates = {DEAL_SUBSCRIPTION: subscription.name, **_deal_value(subscription)}
    if subscription.get("company"):
        updates[DEAL_COMPANY] = subscription.company
    if subscription.get("saas_module"):
        updates[DEAL_MODULE] = subscription.saas_module

    wanted = target_deal_status_type(subscription.get("status"))
    current = _status_type("CRM Deal Status", deal.status)
    if wanted and current != wanted:
        status = pick_status("CRM Deal Status", wanted)
        if status:
            updates["status"] = status
            if wanted == "Won":
                updates["closed_date"] = nowdate()
                updates["probability"] = 100
            else:
                updates["lost_notes"] = f"Subscription {subscription.status.lower()}"
    elif not wanted and current in ("Won", "Lost") and subscription.get("status") in ("Trial", "Pending"):
        # A cancelled customer who starts again reopens the deal.
        reopened = pick_status("CRM Deal Status", OPEN_STATUS_TYPES)
        if reopened:
            updates["status"] = reopened

    changed = {k: v for k, v in updates.items() if deal.get(k) != v}
    if changed:
        deal.update(changed)
        deal.save(ignore_permissions=True)
    return deal_name


# ---------------------------------------------------------------- permissions


def _saas_linked_condition(doctype: str, fieldname: str) -> str:
    return f"ifnull(`tab{doctype}`.`{fieldname}`, '') = ''"


def get_lead_query(user: str | None = None) -> str:
    """Non-vendor users never list the leads that came from SaaS signups."""
    if is_vendor_user(user) or not frappe.db.has_column(LEAD, LEAD_REGISTRATION):
        return ""
    return _saas_linked_condition(LEAD, LEAD_REGISTRATION)


def get_deal_query(user: str | None = None) -> str:
    if is_vendor_user(user) or not frappe.db.has_column(DEAL, DEAL_SUBSCRIPTION):
        return ""
    return f"({_saas_linked_condition(DEAL, DEAL_SUBSCRIPTION)} and {_saas_linked_condition(DEAL, DEAL_MODULE)})"


def has_lead_permission(doc, user: str | None = None, permission_type: str | None = None):
    if doc.get(LEAD_REGISTRATION) and not is_vendor_user(user):
        return False
    return None  # CRM's own role permissions decide everything else.


def has_deal_permission(doc, user: str | None = None, permission_type: str | None = None):
    if (doc.get(DEAL_SUBSCRIPTION) or doc.get(DEAL_MODULE)) and not is_vendor_user(user):
        return False
    return None


# ---------------------------------------------------------------- vendor API


def _require_vendor() -> None:
    if not is_vendor_user():
        frappe.throw("Only Reckon vendor users can open the SaaS CRM.", frappe.PermissionError)


@frappe.whitelist()
def sync_now(limit: int = 500) -> dict:
    """Bring registrations and subscriptions that predate the sync into CRM."""
    _require_vendor()
    if not crm_installed():
        frappe.throw("Install Frappe CRM and Reckon CRM to use the SaaS CRM.")
    if not _fields_ready():
        ensure_crm_custom_fields()
    limit = max(1, min(cint(limit) or 500, 2000))
    counts = {"leads": 0, "deals": 0, "errors": 0}
    linked = set(frappe.get_all(LEAD, filters={LEAD_REGISTRATION: ["is", "set"]}, pluck=LEAD_REGISTRATION))
    for name in frappe.get_all("SaaS Registration", order_by="creation asc", pluck="name", limit=limit):
        registration = frappe.get_doc("SaaS Registration", name)
        try:
            if name not in linked:
                upsert_lead(registration)
                counts["leads"] += 1
            sync_registration(registration)
        except Exception:
            counts["errors"] += 1
            frappe.log_error(frappe.get_traceback(), "SaaS CRM: sync now")
    for name in frappe.get_all("SaaS Subscription", order_by="creation asc", pluck="name", limit=limit):
        try:
            if sync_subscription(frappe.get_doc("SaaS Subscription", name)):
                counts["deals"] += 1
        except Exception:
            counts["errors"] += 1
            frappe.log_error(frappe.get_traceback(), "SaaS CRM: sync now")
    return counts


def _grouped(doctype: str, status_doctype: str, link_field: str, value_field: str | None = None) -> list[dict]:
    fields = ["status", "count(name) as count"]
    if value_field:
        fields.append(f"sum({value_field}) as value")
    rows = frappe.get_all(doctype, filters={link_field: ["is", "set"]}, fields=fields, group_by="status")
    statuses = {
        row.name: row
        for row in frappe.get_all(status_doctype, fields=["name", "type", "position", "color"], order_by="position asc")
    }
    out = []
    for row in rows:
        meta = statuses.get(row.status) or frappe._dict()
        out.append(
            {
                "status": row.status,
                "type": meta.get("type") or "Open",
                "color": meta.get("color") or "gray",
                "position": cint(meta.get("position")),
                "count": cint(row.count),
                "value": flt(row.get("value")),
            }
        )
    return sorted(out, key=lambda r: (r["position"], r["status"] or ""))


def _due_visits(deals: list[str], leads: list[str]) -> list[dict]:
    if not reckon_crm_installed() or not (deals or leads):
        return []
    today = getdate(nowdate())
    rows = []
    for doctype, names in ((DEAL, deals), (LEAD, leads)):
        if not names:
            continue
        rows += frappe.get_all(
            VISIT,
            filters={"reference_doctype": doctype, "reference_name": ["in", names], "status": "Planned",
                     "planned_date": ["<=", today]},
            fields=["name", "reference_doctype", "reference_name", "planned_date", "assigned_to", "visit_type"],
            order_by="planned_date asc",
            limit=20,
        )
    return sorted(rows, key=lambda r: str(r.get("planned_date")))[:20]


@frappe.whitelist()
def get_overview() -> dict:
    """Everything the SaaS CRM page shows, for vendor users."""
    _require_vendor()
    overview = {
        "crm_installed": crm_installed(),
        "reckon_crm_installed": reckon_crm_installed(),
        "sync_enabled": False,
        "leads": [],
        "deals": [],
        "recent": [],
        "visits": [],
        "unsynced": 0,
    }
    if not overview["crm_installed"]:
        return overview
    overview["sync_enabled"] = sync_enabled()
    if not _fields_ready():
        overview["unsynced"] = frappe.db.count("SaaS Registration")
        return overview
    overview["leads"] = _grouped(LEAD, "CRM Lead Status", LEAD_REGISTRATION)
    overview["deals"] = _grouped(DEAL, "CRM Deal Status", DEAL_SUBSCRIPTION, "deal_value")
    linked = set(frappe.get_all(LEAD, filters={LEAD_REGISTRATION: ["is", "set"]}, pluck=LEAD_REGISTRATION))
    overview["unsynced"] = max(0, frappe.db.count("SaaS Registration") - len(linked))
    overview["recent"] = frappe.get_all(
        DEAL,
        filters={DEAL_SUBSCRIPTION: ["is", "set"]},
        fields=["name", "organization", "status", "deal_value", "currency", DEAL_MODULE, "modified"],
        order_by="modified desc",
        limit=10,
    )
    open_deals = frappe.get_all(DEAL, filters={DEAL_SUBSCRIPTION: ["is", "set"]}, pluck="name", limit=500)
    open_leads = frappe.get_all(
        LEAD, filters={LEAD_REGISTRATION: ["is", "set"], "converted": 0}, pluck="name", limit=500
    )
    overview["visits"] = _due_visits(open_deals, open_leads)
    return overview
