"""Content, SEO data and URLs for the public marketing site.

The pages under ``www/`` stay thin: they ask this module for a page description
and render it. Everything here is plain Python data except :func:`get_modules`,
which reads the real module registry (the ``reckon_saas_modules`` hooks), so a
module page exists exactly when a product app is installed and on sale.

Addresses are site-relative. Absolute URLs (canonical, Open Graph, sitemap,
JSON-LD) are built from a base URL passed in by the caller, which is the
domain the page is served from; no domain is written down here.
"""

from __future__ import annotations

import json
import re
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

import frappe

SITE_NAME = "ReckonERP"
BRAND_NAME = SITE_NAME
POWERED_BY = "Powered by ReckonERP"
SUPPORT_EMAIL = "hello@reckon.tech"
COMPANY_SITE = "https://www.reckon.tech/"
WHATSAPP_DISPLAY = "+8801325-009955"
WHATSAPP_NUMBER = "8801325009955"
PUBLISHER = "Reckon Technologies Ltd."

HOME = "/"
FEATURES = "/features"
MODULES = "/modules"
INTEGRATIONS = "/integrations"
FAQ = "/faq"
SIGNUP = "/reckonerp-signup"
LOGIN = "/login"
LOGO = "/assets/reckon_saas_platform/images/reckonerp-logo.webp"
LOGO_SIZE = (360, 232)
LOGO_SOCIAL = "/assets/reckon_saas_platform/images/reckonerp-logo-512.png"
ICON = "/assets/reckon_saas_platform/images/reckonerp-icon-64.png"
HERO_IMAGE = "/assets/reckon_saas_platform/images/marketing-hero.webp"
HERO_IMAGE_DARK = "/assets/reckon_saas_platform/images/marketing-hero-dark.webp"
IMAGE_DIR = "/assets/reckon_saas_platform/images"

# Illustrations drawn for this site: (file, alt text, width, height).
ILLUSTRATIONS = {
    "erp": ("illus-erp.svg", "ERP dashboard with a sales chart, stock value and invoices", 480, 320),
    "crm": ("illus-crm.svg", "CRM pipeline with lead cards moving from new to won", 480, 320),
    "automation": (
        "illus-automation.svg",
        "Automation flow from a new lead through an AI step to email, approval and CRM sync",
        480,
        320,
    ),
    "ai": ("illus-ai.svg", "AI assistant drafting a reply that waits for a person to approve", 480, 320),
}
# Which illustration describes a module or feature best.
MODULE_ILLUSTRATION = {"distribution": "erp", "accounts": "erp", "sales_agent": "crm"}
FEATURE_ILLUSTRATION = {
    "self-serve-signup": "automation",
    "separate-company-workspaces": "erp",
    "plans-and-billing": "erp",
    "modular-erp": "erp",
    "bangla-and-english": "ai",
    "roles-and-security": "crm",
    "integrations-and-channels": "automation",
    "ai-assisted-selling": "ai",
    "reckon-ai-assistant": "ai",
    "field-sales-and-visits": "crm",
}

# Crawlers that fetch pages for search and AI answers. All are welcome on the
# public pages; the app itself stays out of reach.
CRAWLERS = (
    "Googlebot",
    "Bingbot",
    "DuckDuckBot",
    "Applebot",
    "Applebot-Extended",
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-SearchBot",
    "Claude-User",
    "anthropic-ai",
    "PerplexityBot",
    "Perplexity-User",
    "Google-Extended",
    "CCBot",
    "Bytespider",
    "meta-externalagent",
    "cohere-ai",
)
PRIVATE_PATHS = (
    "/app",
    "/desk",
    "/api",
    "/login",
    "/me",
    "/update-password",
    "/reckon-saas-admin",
    "/reckonerp-subscription",
)

# --- Icons -------------------------------------------------------------------
# 24x24 outline glyphs, drawn for this site (stroke only, no fills).
GLYPHS = {
    "chat": "M4 5h16v11H9l-5 4z",
    "mail": "M3 6h18v12H3zM3 7l9 7 9-7",
    "phone": "M6 3h4l1.5 5-2 1.5a11 11 0 0 0 5 5l1.5-2 5 1.5v4a2 2 0 0 1-2 2A16 16 0 0 1 4 5a2 2 0 0 1 2-2z",
    "send": "M3 11l18-8-8 18-2-8z",
    "search": "M10.5 4a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13zM16 16l5 5",
    "spark": "M12 2l2.2 6.3L21 10l-6.8 1.7L12 19l-2.2-7.3L3 10l6.8-1.7z",
    "cpu": "M7 7h10v10H7zM10 10h4v4h-4zM9 3v4M15 3v4M9 17v4M15 17v4M3 9h4M3 15h4M17 9h4M17 15h4",
    "form": "M5 3h14v18H5zM8 8h8M8 12h8M8 16h5",
    "shield": "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z",
    "mic": "M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3",
    "sms": "M4 4h16v12H8l-4 4zM8 9h8M8 12h5",
    "wave": "M2 12h3l2-6 4 12 3-9 2 3h6",
    "building": "M4 21V5l8-2v18M12 9h8v12M7 9h2M7 13h2M7 17h2M15 13h2M15 17h2",
    "billing": "M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6",
    "grid": "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
    "globe": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18",
    "user-check": "M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21a7 7 0 0 1 14 0M16 11l2 2 4-4",
    "plug": "M9 3v5M15 3v5M6 8h12v4a6 6 0 0 1-12 0zM12 18v3",
    "lock": "M6 11h12v10H6zM8 11V8a4 4 0 0 1 8 0v3",
    "route": "M5 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM19 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM7 17h6a3 3 0 0 0 0-6h-2a3 3 0 0 1 0-6h6",
    "book": "M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3zM5 17a3 3 0 0 1 3-3h11",
    "target": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 12h.01",
}


def glyph(name: str) -> str:
    return GLYPHS.get(name, GLYPHS["grid"])


# --- Integrations and channels -------------------------------------------------
# Taken from the Sales Agent "Integrations" page and the platform's own signup
# checks. Names appear only to say what connects; the marks are generic glyphs
# or letters drawn for this site, not the owners' logos.
INTEGRATION_GROUPS = (
    ("messaging", "Messaging"),
    ("social", "Social and lead forms"),
    ("voice", "Voice and SMS"),
    ("email", "Email"),
    ("ai", "AI"),
    ("research", "Search and research"),
    ("platform", "Platform"),
)

INTEGRATIONS_LIST = (
    {"name": "Website chat", "group": "messaging", "glyph": "chat", "color": "#db2777"},
    {"name": "WhatsApp", "group": "messaging", "glyph": "chat", "color": "#16a34a"},
    {"name": "WhatChimp", "group": "messaging", "glyph": "chat", "color": "#25d366"},
    {"name": "Facebook Messenger", "group": "social", "mark": "f", "color": "#1877f2"},
    {"name": "Instagram", "group": "social", "mark": "ig", "color": "#c13584"},
    {"name": "LinkedIn", "group": "social", "mark": "in", "color": "#0a66c2"},
    {"name": "Meta lead ads", "group": "social", "glyph": "form", "color": "#1877f2"},
    {"name": "LinkedIn lead forms", "group": "social", "glyph": "form", "color": "#0a66c2"},
    {"name": "Twilio", "group": "voice", "glyph": "wave", "color": "#e11d48"},
    {"name": "SMS gateways (Bangladesh)", "group": "voice", "glyph": "sms", "color": "#ea580c"},
    {"name": "BulkSMSBD", "group": "voice", "glyph": "sms", "color": "#c2410c"},
    {"name": "SSL Wireless", "group": "voice", "glyph": "sms", "color": "#0e7490"},
    {"name": "Asterisk office phone", "group": "voice", "glyph": "phone", "color": "#475569"},
    {"name": "AI voice assistant", "group": "voice", "glyph": "mic", "color": "#9333ea"},
    {"name": "Email", "group": "email", "glyph": "mail", "color": "#2563eb"},
    {"name": "Brevo", "group": "email", "glyph": "send", "color": "#0b996e"},
    {"name": "Twilio SendGrid", "group": "email", "glyph": "send", "color": "#0284c7"},
    {"name": "Anthropic Claude", "group": "ai", "glyph": "spark", "color": "#c2410c"},
    {"name": "OpenAI", "group": "ai", "glyph": "cpu", "color": "#10a37f"},
    {"name": "Local AI server", "group": "ai", "glyph": "cpu", "color": "#475569"},
    {"name": "Google Places", "group": "research", "glyph": "search", "color": "#ea4335"},
    {"name": "Google Search", "group": "research", "mark": "G", "color": "#4285f4"},
    {"name": "SerpAPI", "group": "research", "glyph": "search", "color": "#0ea5e9"},
    {"name": "Apify", "group": "research", "glyph": "search", "color": "#334155"},
    {"name": "Scrapingdog", "group": "research", "glyph": "search", "color": "#16a34a"},
    {"name": "ScrapingBee", "group": "research", "glyph": "search", "color": "#d97706"},
    {"name": "Brave Search", "group": "research", "glyph": "search", "color": "#fb542b"},
    {"name": "Google reCAPTCHA", "group": "platform", "glyph": "shield", "color": "#4285f4"},
    {"name": "Email verification", "group": "platform", "glyph": "mail", "color": "#2563eb"},
    {"name": "SMS one-time codes", "group": "platform", "glyph": "sms", "color": "#ea580c"},
)

TRADEMARK_NOTE = (
    "Product names are trademarks of their owners and are used only to describe what "
    "ReckonERP can connect to. The marks shown are simple icons drawn for this site; "
    "no affiliation or endorsement is implied."
)

# --- Product features (one page each) ------------------------------------------
FEATURE_LIST = (
    {
        "slug": "self-serve-signup",
        "title": "Self-serve signup",
        "icon": "user-check",
        "summary": "Create a verified company workspace on your own, in minutes.",
        "description": "Sign up for ReckonERP with an emailed link and an SMS code, pick a "
        "plan, and get a provisioned company workspace without waiting for a setup call.",
        "intro": "A business owner picks a module and a plan, proves the email address and "
        "phone number are real, and the platform creates the Company, the owner account and "
        "the first data for that module.",
        "points": [
            "Pick a module and a plan, then enter your company details",
            "Email link and SMS one-time code confirm who you are before anything is created",
            "Captcha and per-address rate limits keep bots out of the signup form",
            "A provisioning job builds the workspace and can be retried if it fails",
        ],
        "faqs": [
            (
                "Do I need a credit card to start?",
                "Signup collects company details and verifies your email and phone. Payment "
                "follows the plan you choose; plans that include a trial start with it.",
            ),
            (
                "How long does setup take?",
                "Verification takes a couple of minutes. Provisioning then runs in the "
                "background and the workspace opens as soon as it is ready.",
            ),
        ],
    },
    {
        "slug": "separate-company-workspaces",
        "title": "Separate company workspaces",
        "icon": "building",
        "summary": "Every customer works inside its own Company, apart from all others.",
        "description": "Each ReckonERP customer gets an isolated Company on ERPNext, with "
        "permission rules that keep one tenant's records out of another tenant's view.",
        "intro": "ReckonERP is multi-tenant by design. Records are owned by the customer's "
        "Company, and permission checks filter every list and report to that Company.",
        "points": [
            "One Company per customer, created at signup",
            "Permission rules limit accounting, stock and sales records to the owner Company",
            "Vendor-only data such as plans, payments and registrations stays out of tenant reach",
            "Team members are assigned to a Company and roles by the owner",
        ],
        "faqs": [
            (
                "Can another customer see my data?",
                "No. Lists, reports and documents are filtered to your Company, and platform "
                "records such as plans and payments are visible to the vendor only.",
            ),
        ],
    },
    {
        "slug": "plans-and-billing",
        "title": "Plans, trials and billing",
        "icon": "billing",
        "summary": "Plans per module, trial days, billing cycles and verified payments.",
        "description": "ReckonERP plans belong to a module and carry a price, a billing cycle "
        "and optional trial days. Payments are verified and access follows the subscription.",
        "intro": "Each plan is bought for one module. A subscription moves through trial, "
        "active, grace and expired states by date, and the subscription page shows where "
        "you stand.",
        "points": [
            "Plans per module with price, currency, billing cycle and trial days",
            "Payment verification before a subscription becomes active",
            "A grace period after the paid period ends before access closes",
            "Status is decided from dates, so access never waits for a background job",
        ],
        "faqs": [
            (
                "Can I run two modules?",
                "Yes. A company keeps access while any of its module subscriptions is active, "
                "and each module is billed on its own plan.",
            ),
            (
                "What happens when a subscription ends?",
                "After the grace period the workspace stops opening and sends you to the "
                "subscription page, where you can renew.",
            ),
        ],
    },
    {
        "slug": "modular-erp",
        "title": "Modular ERP",
        "icon": "grid",
        "summary": "Start with the module you need and add others on the same platform.",
        "description": "ReckonERP is built from modules on ERPNext. Each product app registers "
        "itself with the platform, and customers subscribe only to the modules they use.",
        "intro": "Product apps such as Distribution, Accounts and the Sales AI Agent plug into "
        "one platform. Each has its own plans, roles and starting data, and the desk shows "
        "only the pages that belong to the modules you subscribe to.",
        "points": [
            "Every module registers its plans, roles and starting data with the platform",
            "A vendor can switch a module off for new signups at any time",
            "Desk pages and reports are limited to the modules a company subscribed to",
            "New modules appear on this site as soon as their app is installed",
        ],
        "faqs": [
            (
                "Which modules are available?",
                "The modules page lists every module that is installed and on sale right now.",
            ),
        ],
    },
    {
        "slug": "bangla-and-english",
        "title": "Bangla and English",
        "icon": "globe",
        "summary": "Signup in Bangla or English, with Bangla-first workflows for field teams.",
        "description": "ReckonERP signup works in Bangla and English, and the Distribution "
        "module is designed Bangla-first for field sales and delivery staff.",
        "intro": "Many users in Bangladesh work faster in Bangla. The signup flow offers both "
        "languages, and field-facing modules such as Distribution are written with Bangla "
        "labels in mind.",
        "points": [
            "Switch the signup page between Bangla and English",
            "Bangla-first mobile screens for field staff in the Distribution module",
            "Bangladeshi SMS gateways for one-time codes and notifications",
            "Currency and plans shown in BDT where the plan is priced in BDT",
        ],
        "faqs": [
            (
                "Is the whole ERP in Bangla?",
                "Signup and the Distribution field workflows are Bangla-ready. Other desk "
                "screens follow ERPNext's translations.",
            ),
        ],
    },
    {
        "slug": "roles-and-security",
        "title": "Roles and security",
        "icon": "lock",
        "summary": "Role-based access, verified owners and guarded sign-in.",
        "description": "ReckonERP gives each module its own roles, checks owners at signup "
        "and rate-limits public forms, so a company controls who sees and changes what.",
        "intro": "The owner assigns module roles to the team. Public forms are protected with "
        "captcha and rate limits, and passwords are checked against the site's password "
        "policy.",
        "points": [
            "Module roles such as Admin, Manager and User control what each person can open",
            "Passwords are checked against the site's password policy at signup",
            "Rate limits count failed and repeated attempts per address",
            "Vendor administration is separate from every customer workspace",
        ],
        "faqs": [
            (
                "Who can administer the platform?",
                "Only users with the vendor superuser role. Customers cannot open platform "
                "plans, payments or other tenants.",
            ),
        ],
    },
    {
        "slug": "integrations-and-channels",
        "title": "Integrations and channels",
        "icon": "plug",
        "summary": "WhatsApp, social, SMS, voice and email channels in one place.",
        "description": "ReckonERP connects messaging, social, SMS, voice and email channels, "
        "plus AI and research services, so customer conversations and campaigns share one "
        "system.",
        "intro": "The Sales AI Agent module lists each channel on a single Integrations page: "
        "connect it, see whether it is on, and keep keys per business. Platform checks such "
        "as SMS codes and captcha use their own integrations.",
        "points": [
            "Messaging: website chat and WhatsApp",
            "Social: Facebook Messenger, Instagram, LinkedIn and lead forms",
            "Voice and SMS: Twilio, Bangladeshi gateways and an Asterisk office phone",
            "Email through your mailbox, Brevo or SendGrid, with delivery events",
        ],
        "faqs": [
            (
                "Do I have to use every channel?",
                "No. Each channel is off until you connect it, and each business keeps its own "
                "keys.",
            ),
        ],
    },
    {
        "slug": "reckon-ai-assistant",
        "title": "Reckon AI assistant",
        "icon": "spark",
        "summary": "Ask questions about your own records and approve the actions it suggests.",
        "description": "Reckon AI answers questions from your own ERP records, raises insights, "
        "alerts and forecasts, and changes data only after you review and approve.",
        "intro": "Reckon AI sits inside the ERP. It works from the records the signed-in person "
        "is allowed to see, explains what needs attention, and proposes actions that the "
        "person reviews before anything is applied.",
        "points": [
            "Answers questions from your own records, limited to what you may open",
            "Insights, alerts, forecasting and anomaly detection for the numbers you track",
            "A catalogue of suggested actions that learns from your feedback",
            "Preview first: you review the values and approve, permissions are checked again "
            "and every confirmed action is logged",
        ],
        "faqs": [
            (
                "Can Reckon AI change my data on its own?",
                "No. It shows a preview of the target and values. Nothing is applied until you "
                "approve, and the server checks your permissions again at that moment.",
            ),
            (
                "Can it see other people's records?",
                "It works inside the permissions of the person asking, so it cannot read what "
                "that person cannot open.",
            ),
            (
                "Is Reckon AI included in the subscription?",
                "AI and integration tools are additional. Ask us for pricing for your usage.",
            ),
        ],
    },
    {
        "slug": "field-sales-and-visits",
        "title": "Field sales visits",
        "icon": "route",
        "summary": "Schedule customer visits, check in with GPS and keep a history of every visit.",
        "description": "Plan field visits against leads, deals and customers, check in and out "
        "with GPS, see visits on a map and keep outcomes and follow-ups.",
        "intro": "Reckon CRM adds field sales to your customer records: managers schedule visits, "
        "reps check in on site, and every completed visit keeps its outcome and next step.",
        "points": [
            "Schedule visits for several team members against a lead, deal or organisation",
            "Interactive map with the customer's location and a geofence",
            "GPS check-in and check-out at the time of the visit",
            "Completed visits keep their outcome, notes, duration and follow-up date",
        ],
        "faqs": [
            (
                "Is field sales part of self-serve signup?",
                "Reckon CRM is offered on request, on a dedicated cloud or on-premises. Message "
                "us and we will set it up with you.",
            ),
        ],
    },
    {
        "slug": "ai-assisted-selling",
        "title": "AI-assisted selling",
        "icon": "spark",
        "summary": "Find, research and qualify customers, with a person approving every message.",
        "description": "The Sales AI Agent finds B2B customers, researches their websites with "
        "evidence, scores leads and syncs them to CRM, and nothing is sent without human "
        "approval.",
        "intro": "The Sales AI Agent module runs discovery campaigns, researches each lead from "
        "its own website, scores it with fixed rules and drafts follow-ups that a person "
        "approves before they go out.",
        "points": [
            "Discovery campaigns that find businesses to contact",
            "Website research that keeps its evidence next to each claim",
            "Deterministic lead scoring you can read and explain",
            "CRM sync and email sequences that wait for approval",
        ],
        "faqs": [
            (
                "Will the AI message customers on its own?",
                "No. Drafts wait for a person's approval before any message is sent.",
            ),
        ],
    },
)

# --- Module copy: marketing text layered on the registry's own fields -----------
MODULE_COPY = {
    "distribution": {
        "seo_title": "FMCG distribution software for route sales and collections",
        "headline": "FMCG distribution software for route sales, collections and stock",
        "tagline": "Routes, deliveries, collections and stock for FMCG distributors.",
        "audience": "FMCG distributors, wholesalers and van-sales teams",
        "benefits": [
            "Plan SR and DSR routes and see what each team delivered",
            "Track retailer dues and collect against them in the field",
            "Know the cash each DSR is carrying, to the taka",
            "Handle goods supplied by principals alongside your own stock",
        ],
        "faqs": [
            (
                "Can my field team use it on a phone?",
                "Yes. The Distribution module includes a Bangla-first mobile app that works "
                "in the browser.",
            ),
            (
                "Does it handle accounting?",
                "It runs on ERPNext, so invoices, payments and stock post to the books of "
                "your Company.",
            ),
        ],
    },
    "accounts": {
        "seo_title": "Accounting and inventory software for small business",
        "headline": "Accounting and inventory software for growing small businesses",
        "tagline": "Invoices, bills, stock and Tally-style books for a small business.",
        "audience": "Shops, traders and small companies that need clean books",
        "benefits": [
            "Raise sales invoices and quotations, and record purchase bills and orders",
            "Keep stock and warehouses in step with what you buy and sell",
            "Record cash, bank and payments in one place",
            "Read the books in a Tally-style view, in Bangla or English",
        ],
        "faqs": [
            (
                "Is this a full accounting system?",
                "Yes. It is built on ERPNext's accounting with a simpler set of screens for "
                "small businesses.",
            ),
        ],
    },
    "sales_agent": {
        "seo_title": "AI sales agent for B2B lead generation and follow-up",
        "headline": "AI sales agent for finding and following up B2B customers",
        "tagline": "Find, research and follow up B2B customers, with approval before any send.",
        "audience": "B2B sales teams, with strong coverage of Bangladesh",
        "benefits": [
            "Run discovery campaigns to find businesses worth contacting",
            "Research each lead from its website and keep the evidence",
            "Score leads with fixed rules, then sync them to your CRM",
            "Send email, SMS and WhatsApp follow-ups only after a person approves",
        ],
        "faqs": [
            (
                "Which channels can it use?",
                "Website chat, WhatsApp, Facebook Messenger, Instagram, LinkedIn, Twilio, "
                "SMS gateways and email. See the integrations page for the full list.",
            ),
            (
                "Does it need my own AI account?",
                "The platform operator can provide the AI service for everyone, and a "
                "business may bring its own if the operator allows it.",
            ),
        ],
    },
}

# Plain-language labels for the registry's ``subscription_features`` keys.
FEATURE_LABELS = {
    "dsr_routes": "DSR route planning and delivery tracking",
    "retailer_receivable": "Retailer dues and collections",
    "dsr_cash_custody": "DSR cash custody",
    "supplier_provided_goods": "Supplier-provided goods",
    "bangla_pwa": "Bangla-first mobile app",
    "sales_invoices_and_quotations": "Sales invoices and quotations",
    "purchase_bills_and_orders": "Purchase bills and orders",
    "stock_and_warehouses": "Stock and warehouses",
    "cash_bank_and_payments": "Cash, bank and payments",
    "tally_style_books_and_reports": "Tally-style books and reports",
    "team_roles_for_sales_purchase_stock": "Team roles for sales, purchase and stock",
    "lead_discovery_campaigns": "Lead discovery campaigns",
    "website_research_with_evidence": "Website research with evidence",
    "deterministic_lead_scoring": "Rule-based lead scoring",
    "frappe_crm_sync": "CRM sync",
    "email_sequences_with_approval": "Email sequences with approval",
    "claude_ai_research_and_drafting": "AI research and drafting",
}

ACRONYMS = frozenset({"sr", "dsr", "pwa", "erp", "crm", "hr", "pos", "sms", "vat", "gl", "ai"})

SHOWCASE = (
    ("erp", "ERP", "Sales, stock, collections and books for your company, in one place."),
    ("crm", "CRM", "Leads and customers move through a pipeline your whole team can see."),
    ("automation", "Automation", "Triggers hand work to steps that draft, route and sync for you."),
    ("ai", "AI assistance", "AI drafts and researches; a person approves before anything is sent."),
)

AI_POINTS = (
    "Reckon AI reads and summarises invoices, orders, stock and customer records so people find answers faster",
    "Researches leads from their own websites and keeps the evidence next to every claim",
    "Drafts replies and follow-ups; a person approves before anything is sent",
    "Scores leads with fixed rules you can read, then syncs them to your CRM",
)
FAMILY_APPS = (
    {
        "name": "Reckon AI assistant",
        "text": "Ask questions about your own records, get insights and alerts, and approve "
        "suggested actions.",
        "url": "/features/reckon-ai-assistant",
    },
    {
        "name": "Reckon CRM",
        "text": "Field sales on your CRM: visit scheduling, GPS check-in and check-out, customer "
        "maps and visit history.",
        "url": "/features/field-sales-and-visits",
    },
    {
        "name": "Reckon Constructions",
        "text": "Construction projects from estimate to bill: BOQ revisions, measurements, rate "
        "analysis, procurement, site execution, variations and progress certificates.",
    },
    {
        "name": "Reckon Real Estate",
        "text": "Property development and sales: projects, buildings and units, bookings, "
        "installment plans, land and joint-venture agreements, handovers, collections, "
        "contractor bills and budgets.",
    },
    {
        "name": "Reckon HRMS",
        "text": "Simple HR for small teams: employees, attendance, salary and bulk salary payment, "
        "payslip PDFs and HR reports.",
    },
    {
        "name": "Reckon HR Policy",
        "text": "Configurable attendance consequences and payroll additions that follow your own "
        "company policy.",
    },
    {
        "name": "Restaurant and central kitchen",
        "text": "Branches that share a central store and kitchen: requisition, stock movement, "
        "production, delivery and branch-wise sales.",
    },
)
FAMILY_NOTE = (
    "These products are offered on request, on a dedicated cloud or on-premises, and are not on "
    "self-serve signup yet. Customisation and implementation are quoted separately."
)

AI_NOTE = "AI and integration tools are billed separately from the module subscription."

DEPLOYMENTS = (
    {
        "title": "Shared cloud",
        "text": "Sign up online from anywhere and start in your own private company workspace. Fastest way to begin.",
    },
    {
        "title": "Dedicated cloud",
        "text": "Your own cloud server for isolation and your own release schedule. "
        "Customisation and set-up are quoted separately.",
    },
    {
        "title": "On-premises",
        "text": "Installed on your own infrastructure with customisation and support. "
        "Quoted to your requirements.",
    },
)

HOME_FAQS = (
    (
        "What is ReckonERP?",
        "ReckonERP is a cloud ERP for growing businesses, built on ERPNext, with Reckon AI "
        "built in. You pick the modules you need, such as Distribution, Accounts or the "
        "Sales AI Agent, and each company works in its own private workspace.",
    ),
    (
        "How do I start?",
        "Choose Sign up, pick a module and a plan, and verify your email and phone number. "
        "Your workspace is created once verification is done.",
    ),
    (
        "How is ReckonERP deployed?",
        "Three ways: the shared cloud, where you sign up and start at once; a dedicated cloud "
        "installation for your company alone; or on-premises on your own infrastructure. "
        "Dedicated and on-premises installations are customised to your needs and quoted "
        "separately.",
    ),
    (
        "How does pricing work?",
        "Each module has its own subscription plan, with its price, billing cycle and any "
        "trial days shown when you sign up. Implementation, customisation, AI and "
        "integration tools are additional.",
    ),
    (
        "What does implementation cost?",
        "Self-serve signup needs no implementation. Guided set-up, data migration, training "
        "and custom work are additional and quoted after we understand your business. Message "
        "us on WhatsApp or email for an estimate.",
    ),
    (
        "Do AI and integration tools cost extra?",
        "Yes. AI features and channel integrations such as WhatsApp, SMS, voice and email "
        "services are charged in addition to the module subscription, because they depend on "
        "usage and on third-party providers.",
    ),
    (
        "Can you customise it, or install it on our own servers?",
        "Yes. We support customisation, dedicated cloud installation and on-premises "
        "installation. Tell us about your requirements and we will quote.",
    ),
    (
        "What about licences?",
        "ReckonERP is a subscription service: your subscription lets your company use the "
        "modules you subscribed to. The platform is built on open-source ERP technology. "
        "Licence terms for dedicated and on-premises installations are agreed in the quote.",
    ),
    (
        "How do I get help?",
        "Email us, or chat on WhatsApp using the chat button on this page. Existing customers "
        "can also write to the same address from their workspace.",
    ),
    (
        "Is my data separate from other companies?",
        "Yes. Every customer has its own Company and permission rules keep each tenant's "
        "records apart.",
    ),
    (
        "Can I move my existing data in?",
        "Data migration from spreadsheets or other software is available as an additional "
        "service. Ask us for an estimate.",
    ),
    (
        "Which channels and services can I connect?",
        "WhatsApp, Facebook Messenger, Instagram, LinkedIn, Twilio, SMS gateways, email "
        "services such as Brevo and SendGrid, Google services and AI providers. The "
        "integrations page lists them all.",
    ),
    (
        "Can I use ReckonERP outside Bangladesh?",
        "Yes. Workspaces run in the cloud and open from any country in English. Plans can be "
        "priced in BDT, USD, EUR or INR. Bangla screens and Bangladeshi SMS gateways are extra "
        "strengths for Bangladesh. Dedicated cloud and on-premises installations are available "
        "for companies anywhere on request.",
    ),
    (
        "Can I use it in Bangla?",
        "Signup is available in Bangla and English, and the Distribution module is "
        "designed Bangla-first for field teams.",
    ),
)


# --- Helpers -------------------------------------------------------------------
def humanise(key: str) -> str:
    """``dsr_cash_custody`` -> ``DSR cash custody`` for keys with no written label."""
    words = key.strip().replace("_", " ").split()
    if not words:
        return ""
    words = [w.upper() if w.lower() in ACRONYMS else w.lower() for w in words]
    if words[0].islower():
        words[0] = words[0].capitalize()
    return " ".join(words)


def feature_label(key: str) -> str:
    return FEATURE_LABELS.get(key) or humanise(key)


def illustration(name: str | None) -> dict | None:
    """An illustration as template data, or ``None`` when the name is unknown."""
    if name not in ILLUSTRATIONS:
        return None
    file, alt, width, height = ILLUSTRATIONS[name]
    return {"src": f"{IMAGE_DIR}/{file}", "alt": alt, "width": width, "height": height}


def feature_url(slug: str) -> str:
    return f"{FEATURES}/{quote(slug)}"


def module_url(key: str) -> str:
    return f"{MODULES}/{quote(key)}"


def signup_url(module_key: str | None = None) -> str:
    return f"{SIGNUP}?module={quote(module_key)}" if module_key else SIGNUP


def get_feature(slug: str) -> dict | None:
    return next((f for f in FEATURE_LIST if f["slug"] == slug), None)


def get_modules() -> list[dict]:
    """Modules installed on this site and on sale.

    The registry (``reckon_saas_modules`` hooks) says which apps are installed.
    Each module's **SaaS Module** record, which the vendor can edit, supplies the
    name, description and feature list when it has them, and switches the module
    off for sale.
    """
    from reckon_saas_platform.module_registry import MODULE_DOCTYPE, get_saas_modules

    records: dict[str, dict] = {}
    if frappe.db.exists("DocType", MODULE_DOCTYPE):
        for row in frappe.get_all(
            MODULE_DOCTYPE,
            fields=["name", "module_name", "description", "features", "enabled", "modified"],
            ignore_permissions=True,
        ):
            records[row.get("name")] = row

    modules = []
    seen = set()
    for definition in get_saas_modules():
        key = definition.get("key")
        record = records.get(key)
        if not key or key in seen or (record is not None and not record.get("enabled")):
            continue
        seen.add(key)
        record = record or {}
        copy = MODULE_COPY.get(key, {})
        label = record.get("module_name") or definition.get("label") or humanise(key)
        description = record.get("description") or definition.get("description") or ""
        feature_keys = [
            line.strip() for line in (record.get("features") or "").splitlines() if line.strip()
        ] or list(definition.get("subscription_features") or [])
        modules.append(
            {
                "key": key,
                "name": label,
                "description": description,
                "tagline": copy.get("tagline") or description,
                "seo_title": copy.get("seo_title") or "",
                "headline": copy.get("headline") or "",
                "audience": copy.get("audience") or "",
                "benefits": list(copy.get("benefits") or []),
                "features": [feature_label(k) for k in feature_keys],
                "faqs": list(copy.get("faqs") or []),
                "url": module_url(key),
                "modified": str(record.get("modified") or "")[:10],
                "image": illustration(MODULE_ILLUSTRATION.get(key, "erp")),
            }
        )
    return modules


def get_integrations() -> list[dict]:
    """The built-in channel list plus anything product apps publish.

    An app may add a ``reckon_saas_integrations`` hook returning dicts with
    ``name`` and optionally ``group``, ``glyph`` or ``mark``, and ``color``.
    """
    items = [dict(item) for item in INTEGRATIONS_LIST]
    names = {item["name"].lower() for item in items}
    groups = {key for key, _label in INTEGRATION_GROUPS}
    for app in frappe.get_installed_apps():
        for entry in frappe.get_hooks("reckon_saas_integrations", app_name=app) or []:
            if isinstance(entry, str):
                entry = frappe.get_attr(entry)()
            for raw in entry if isinstance(entry, (list, tuple)) else [entry]:
                name = str((raw or {}).get("name") or "").strip()
                if not name or name.lower() in names:
                    continue
                color = str(raw.get("color") or "")
                item = {
                    "name": name,
                    "group": raw.get("group") if raw.get("group") in groups else "platform",
                    "color": color if re.fullmatch(r"#[0-9a-fA-F]{6}", color) else "#475569",
                }
                mark = str(raw.get("mark") or "")[:2]
                if mark:
                    item["mark"] = mark
                else:
                    item["glyph"] = raw.get("glyph") if raw.get("glyph") in GLYPHS else "plug"
                names.add(name.lower())
                items.append(item)
    return items


def get_module(modules: list[dict], key: str | None) -> dict | None:
    return next((m for m in modules if m["key"] == key), None)


# --- JSON-LD -------------------------------------------------------------------
def dumps_ld(data: dict) -> str:
    """JSON for a ``<script type="application/ld+json">`` block (safe against ``</script>``)."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def organization_ld(base: str, same_as=None) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": SITE_NAME,
        "legalName": PUBLISHER,
        "url": f"{base}/",
        "logo": f"{base}{LOGO_SOCIAL}",
        "email": SUPPORT_EMAIL,
        "areaServed": "Worldwide",
        "knowsLanguage": ["en", "bn"],
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer support",
            "email": SUPPORT_EMAIL,
        },
    }
    if same_as:
        data["sameAs"] = list(same_as)
    return data


def software_ld(base: str, name: str, description: str, path: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": name,
        "description": description,
        "url": f"{base}{path}",
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "inLanguage": ["en", "bn"],
        "publisher": {"@type": "Organization", "name": SITE_NAME},
    }


def faq_ld(faqs) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in faqs
        ],
    }


def breadcrumb_ld(base: str, trail: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": f"{base}{path}"}
            for i, (name, path) in enumerate(trail, start=1)
        ],
    }


# --- Page descriptions -----------------------------------------------------------
OVERRIDES_CACHE_KEY = "reckon_saas_seo_overrides"
FORBIDDEN_WORDS = re.compile(r"\b(best|number one|no\.? ?1|#1|guaranteed?|cheapest|frappe)\b", re.I)


def seo_overrides() -> dict:
    """Approved SEO Suggestions: ``{"pages": {path: {title, description}}, "faqs": [(q, a)]}``.

    Read again with the same length and wording checks the agent uses, cached for
    ten minutes and cleared whenever a suggestion is saved.
    """
    cached = frappe.cache.get_value(OVERRIDES_CACHE_KEY)
    if cached is not None:
        return cached
    result: dict = {"pages": {}, "faqs": []}
    try:
        if frappe.db.exists("DocType", "SEO Suggestion"):
            rows = frappe.get_all(
                "SEO Suggestion",
                filters={"status": "Approved"},
                fields=["kind", "page_path", "proposed_title", "proposed_description", "question", "answer"],
                order_by="modified asc",
                ignore_permissions=True,
            )
            for row in rows:
                if row.get("kind") == "Title and Description":
                    title, desc = (row.get("proposed_title") or "").strip(), (row.get("proposed_description") or "").strip()
                    if 20 <= len(title) <= 70 and 70 <= len(desc) <= 160 and not FORBIDDEN_WORDS.search(title + " " + desc):
                        result["pages"][row.get("page_path")] = {"title": title, "description": desc}
                elif row.get("kind") == "FAQ":
                    q, a = (row.get("question") or "").strip(), (row.get("answer") or "").strip()
                    if q.endswith("?") and 40 <= len(a) <= 600 and not FORBIDDEN_WORDS.search(q + " " + a):
                        result["faqs"].append((q, a))
    except Exception:
        result = {"pages": {}, "faqs": []}
    frappe.cache.set_value(OVERRIDES_CACHE_KEY, result, expires_in_sec=600)
    return result


def make_page(
    base: str,
    *,
    path: str,
    title: str,
    description: str,
    h1: str,
    trail: list[tuple[str, str]] | None = None,
    faqs=None,
    software: tuple[str, str] | None = None,
    same_as=None,
    extra_ld=None,
    noindex: bool = False,
    **extra,
) -> dict:
    """Everything a template needs: head tags, JSON-LD and breadcrumbs."""
    trail = trail or [("Home", HOME)]
    approved = seo_overrides()["pages"].get(path)
    if approved:
        title, description = approved["title"], approved["description"]
    ld = []
    if path == HOME:
        ld.append(organization_ld(base, same_as))
    if software:
        ld.append(software_ld(base, software[0], software[1], path))
    if faqs:
        ld.append(faq_ld(faqs))
    ld += list(extra_ld or [])
    if len(trail) > 1:
        ld.append(breadcrumb_ld(base, trail))
    return {
        "path": path,
        "title": title,
        "description": description,
        "h1": h1,
        "canonical": f"{base}{path}",
        "og_image": f"{base}{LOGO_SOCIAL}",
        "site_name": SITE_NAME,
        "trail": trail,
        "noindex": noindex,
        "faqs": list(faqs or []),
        "jsonld": [dumps_ld(item) for item in ld],
        **extra,
    }


def home_page(base: str, modules: list[dict], integrations=None, profiles=None, articles=None) -> dict:
    from reckon_saas_platform import blog

    latest = (blog.get_articles() if articles is None else articles)[:3]
    description = (
        "ReckonERP is a cloud ERP with built-in AI. Invoices, orders, stock and people in one "
        "workspace, in English and Bangla. Start online today."
    )
    return make_page(
        base,
        path=HOME,
        title="ReckonERP: cloud ERP with built-in AI for growing businesses",
        description=description,
        h1="Your ERP, now with an AI that reads every ledger.",
        faqs=HOME_FAQS,
        software=(SITE_NAME, description),
        same_as=profiles,
        latest_articles=latest,
        features=FEATURE_LIST,
        modules=modules,
        integrations=list(integrations or INTEGRATIONS_LIST),
    )


def features_page(base: str) -> dict:
    return make_page(
        base,
        path=FEATURES,
        title="Features: what ReckonERP does for your company",
        description="Every ReckonERP feature on its own page: self-serve signup, separate "
        "company workspaces, plans and billing, modules, Bangla support, security and "
        "integrations.",
        h1="Everything the ReckonERP platform does",
        trail=[("Home", HOME), ("Features", FEATURES)],
        features=FEATURE_LIST,
    )


def feature_page(base: str, feature: dict) -> dict:
    return make_page(
        base,
        path=feature_url(feature["slug"]),
        title=f"{feature['title']} | ReckonERP features",
        description=feature["description"],
        h1=feature["title"],
        trail=[("Home", HOME), ("Features", FEATURES), (feature["title"], feature_url(feature["slug"]))],
        faqs=feature["faqs"],
        feature=feature,
        image=illustration(FEATURE_ILLUSTRATION.get(feature["slug"])),
        features=[f for f in FEATURE_LIST if f["slug"] != feature["slug"]],
    )


def modules_page(base: str, modules: list[dict]) -> dict:
    return make_page(
        base,
        path=MODULES,
        title="ERP modules: Distribution, Accounts and Sales AI Agent",
        description="Browse the ReckonERP modules you can subscribe to. Each one has its own "
        "plans, roles and starting data, and runs in your company's private workspace.",
        h1="Choose the modules your business needs",
        trail=[("Home", HOME), ("Modules", MODULES)],
        modules=modules,
        family=FAMILY_APPS,
        family_note=FAMILY_NOTE,
    )


def _articles_for(module_key: str) -> list[dict]:
    from reckon_saas_platform import blog

    return [a for a in blog.get_articles() if a["module"] == module_key]


def module_page(base: str, module: dict, modules: list[dict]) -> dict:
    description = (module["tagline"] + " " + module["description"]).strip()
    if len(description) > 158:
        description = module["tagline"] if len(module["tagline"]) > 70 else description[:155].rstrip() + "..."
    return make_page(
        base,
        path=module["url"],
        title=f"{module['seo_title'] or module['name'] + ' module'} | ReckonERP",
        description=description,
        h1=module["headline"] or module["name"],
        trail=[("Home", HOME), ("Modules", MODULES), (module["name"], module["url"])],
        faqs=module["faqs"],
        software=(f"{SITE_NAME} {module['name']}", description),
        module=module,
        module_articles=[a for a in _articles_for(module["key"])][:3],
        modules=[m for m in modules if m["key"] != module["key"]],
        signup_url=signup_url(module["key"]),
    )


def faq_groups(modules: list[dict]) -> list[dict]:
    """Every question the site answers, grouped, with repeated questions shown once."""
    seen: set[str] = set()
    groups = []

    def add(title, faqs):
        rows = []
        for question, answer in faqs:
            if question not in seen:
                seen.add(question)
                rows.append((question, answer))
        if rows:
            groups.append({"title": title, "faqs": rows})

    add("About ReckonERP", HOME_FAQS)
    add("More answers", seo_overrides()["faqs"])
    for module in modules:
        add(module["name"], module["faqs"])
    for feature in FEATURE_LIST:
        add(feature["title"], feature["faqs"])
    return groups


def faq_page(base: str, modules: list[dict]) -> dict:
    groups = faq_groups(modules)
    everything = [row for group in groups for row in group["faqs"]]
    return make_page(
        base,
        path=FAQ,
        title="ReckonERP FAQ: pricing, deployment, AI, licences and support",
        description="Answers about ReckonERP pricing, implementation cost, dedicated cloud and "
        "on-premises deployment, licences, AI and integration charges, and support.",
        h1="Frequently asked questions about ReckonERP",
        trail=[("Home", HOME), ("FAQ", FAQ)],
        faqs=everything,
        groups=groups,
    )


def integrations_page(base: str, integrations=None) -> dict:
    integrations = list(integrations or INTEGRATIONS_LIST)
    return make_page(
        base,
        path=INTEGRATIONS,
        title="Integrations: WhatsApp, email, SMS, voice and AI",
        description="ReckonERP connects WhatsApp, Facebook Messenger, Instagram, LinkedIn, "
        "Twilio, SMS gateways, Brevo, SendGrid, Google services and AI providers.",
        h1="Channels and services you can connect",
        trail=[("Home", HOME), ("Integrations", INTEGRATIONS)],
        integrations=integrations,
        groups=[
            {"key": key, "label": label, "items": [i for i in integrations if i["group"] == key]}
            for key, label in INTEGRATION_GROUPS
        ],
        trademark_note=TRADEMARK_NOTE,
    )


# --- Machine-readable files --------------------------------------------------------
def public_paths(modules: list[dict], articles=None) -> list[str]:
    """Every indexable page, in sitemap order. The blog appears once it has a published post."""
    from reckon_saas_platform import blog

    articles = blog.get_articles() if articles is None else articles
    paths = [HOME, FEATURES]
    paths += [feature_url(f["slug"]) for f in FEATURE_LIST]
    paths += [MODULES] + [m["url"] for m in modules]
    paths += [INTEGRATIONS, FAQ]
    if articles:
        paths += [blog.BLOG] + [a["url"] for a in articles]
    paths += [SIGNUP]
    return paths


def sitemap_xml(base: str, modules: list[dict]) -> str:
    """Built on every request from the live module registry, so new modules appear by themselves."""
    from reckon_saas_platform import blog

    articles = blog.get_articles()
    modified = {m["url"]: m.get("modified") for m in modules}
    modified.update({a["url"]: a["modified"] for a in articles})
    if articles:
        modified[blog.BLOG] = articles[0]["modified"]
    rows = []
    for path in public_paths(modules, articles):
        lastmod = modified.get(path)
        stamp = f"<lastmod>{xml_escape(lastmod)}</lastmod>" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", lastmod or "") else ""
        rows.append(f"<url><loc>{xml_escape(base + path)}</loc>{stamp}</url>")
    urls = "".join(rows)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n'
    )


def robots_txt(base: str) -> str:
    agents = "\n".join(f"User-agent: {agent}" for agent in ("*", *CRAWLERS))
    disallow = "\n".join(f"Disallow: {path}" for path in PRIVATE_PATHS)
    return f"{agents}\nAllow: /\n{disallow}\n\nSitemap: {base}/sitemap.xml\n"


def _blog_lines(base: str) -> list[str]:
    from reckon_saas_platform import blog

    posts = blog.get_articles(30)
    if not posts:
        return []
    return ["## Blog", "", *[f"- [{p['title']}]({base}{p['url']}): {p['summary']}" for p in posts], ""]


def llms_txt(base: str, modules: list[dict], integrations=None) -> str:
    integrations = list(integrations or INTEGRATIONS_LIST)
    lines = [
        f"# {SITE_NAME}",
        "",
        "> ReckonERP is a multi-tenant cloud ERP for growing businesses worldwide, with deep support for Bangladesh, built on "
        "ERPNext. Companies sign up online, subscribe to the modules they need and work in "
        "their own private workspace, in Bangla or English.",
        "",
        "## Modules",
        "",
    ]
    for module in modules:
        lines.append(f"- [{module['name']}]({base}{module['url']}): {module['tagline']}")
    lines += ["", "## More from Reckon (on request)", ""]
    for app in FAMILY_APPS:
        lines.append(f"- {app['name']}: {app['text']}")
    lines += ["", "## Features", ""]
    for feature in FEATURE_LIST:
        lines.append(f"- [{feature['title']}]({base}{feature_url(feature['slug'])}): {feature['summary']}")
    lines += [
        "",
        "## Integrations",
        "",
        f"- [Integrations]({base}{INTEGRATIONS}): "
        + ", ".join(item["name"] for item in integrations)
        + ".",
        "",
        *_blog_lines(base),
        "## Answers",
        "",
        f"- [FAQ]({base}{FAQ}): pricing, deployment, implementation cost, licences, AI and "
        "integration charges, support",
        f"- [Full text for AI assistants]({base}/llms-full.txt)",
        "",
        "## Start",
        "",
        f"- [Sign up]({base}{SIGNUP}): create a company workspace",
        f"- [Log in]({base}{LOGIN}): existing customers",
        f"- Support: {SUPPORT_EMAIL}",
        "",
    ]
    return "\n".join(lines)


def llms_full_txt(base: str, modules: list[dict], integrations=None) -> str:
    """The whole public site as one Markdown document, for AI assistants and crawlers."""
    integrations = list(integrations or INTEGRATIONS_LIST)
    out = [
        f"# {SITE_NAME}: full site text",
        "",
        "> ReckonERP is a multi-tenant cloud ERP with built-in AI for growing businesses worldwide, with deep support for Bangladesh, "
        "built on ERPNext. Companies sign up online, subscribe to the modules they need and work "
        "in their own private workspace, in Bangla or English.",
        "",
        f"Website: {base}/",
        f"Contact: {SUPPORT_EMAIL}, WhatsApp {WHATSAPP_DISPLAY}, {COMPANY_SITE}",
        "",
        "## Modules",
        "",
    ]
    for module in modules:
        out += [f"### {module['name']}", f"URL: {base}{module['url']}", "", module["tagline"], ""]
        if module["description"] and module["description"] != module["tagline"]:
            out += [module["description"], ""]
        if module["audience"]:
            out += [f"Built for: {module['audience']}", ""]
        out += [f"- {item}" for item in module["benefits"] + module["features"]] + [""]
    out += ["## More from Reckon (on request)", ""]
    out += [f"- {app['name']}: {app['text']}" for app in FAMILY_APPS] + ["", FAMILY_NOTE, "", "## Features", ""]
    for feature in FEATURE_LIST:
        out += [f"### {feature['title']}", f"URL: {base}{feature_url(feature['slug'])}", "", feature["intro"], ""]
        out += [f"- {point}" for point in feature["points"]] + [""]
    out += ["## Deployment options", ""]
    out += [f"- {item['title']}: {item['text']}" for item in DEPLOYMENTS] + ["", AI_NOTE, ""]
    out += ["## Integrations and channels", "", ", ".join(item["name"] for item in integrations) + ".", ""]
    out += _blog_lines(base)
    out += ["## Frequently asked questions", ""]
    for group in faq_groups(modules):
        out += [f"### {group['title']}", ""]
        for question, answer in group["faqs"]:
            out += [f"**{question}**", answer, ""]
    out += [TRADEMARK_NOTE, ""]
    return "\n".join(out)


def _registered_domain(host: str) -> str:
    """``app.example.com`` -> ``example.com`` (last two labels; enough to tell sibling hosts apart)."""
    return ".".join(host.split(":")[0].split(".")[-2:])


def _public_host_ok(host: str) -> bool:
    """A host may build absolute URLs when it is, or sits beside, one of this site's own hosts.

    Sibling hosts count (the site may have been renamed from distribution.example.com
    to app.example.com), but an unrelated domain never does.
    """
    known = {str(frappe.local.site or "").lower()} if getattr(frappe.local, "site", None) else set()
    configured = str(frappe.conf.get("host_name") or "")
    if configured:
        known.add(re.sub(r"^https?://", "", configured).split("/")[0].lower())
    known.update(str(h).lower() for h in (frappe.conf.get("reckon_saas_public_hosts") or []))
    return _registered_domain(host) in {_registered_domain(h) for h in known if h}


def site_base() -> str:
    """The domain this page is served from, with no trailing slash and none written in code.

    ``Public Website URL`` in SaaS Platform Settings wins. Otherwise the request's
    own host is used when it is one of this site's known hosts; the site's
    configured address is the last resort.
    """
    try:
        configured = str(frappe.get_cached_doc("SaaS Platform Settings").get("public_website_url") or "").strip()
    except Exception:
        configured = ""
    if re.fullmatch(r"https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?/?", configured):
        return configured.rstrip("/")

    request = getattr(frappe.local, "request", None)
    host = str(getattr(request, "host", "") or "").strip().lower()
    if request is not None and re.fullmatch(r"[a-z0-9.-]+(:[0-9]{1,5})?", host) and _public_host_ok(host):
        headers = getattr(request, "headers", None) or {}
        scheme = headers.get("X-Forwarded-Proto") or getattr(request, "scheme", "") or "https"
        return f"{'http' if scheme == 'http' else 'https'}://{host}"
    return frappe.utils.get_url().rstrip("/")


TRACKING_PATTERNS = {
    "gtm": ("google_tag_manager_id", r"GTM-[A-Z0-9]{4,12}"),
    "ga4": ("google_analytics_id", r"G-[A-Z0-9]{6,14}"),
    "pixel": ("meta_pixel_id", r"[0-9]{8,20}"),
    "verify_google": ("google_site_verification", r"[A-Za-z0-9_-]{10,100}"),
    "verify_bing": ("bing_site_verification", r"[A-Za-z0-9_-]{10,100}"),
    "verify_meta": ("meta_domain_verification", r"[A-Za-z0-9_-]{10,100}"),
}


def get_tracking() -> dict:
    """Analytics, pixel and site-verification IDs from SaaS Platform Settings.

    Each value must look like the real thing before it reaches a page, so a stray
    character in Settings can never inject markup. Empty means "not configured".
    """
    try:
        settings = frappe.get_cached_doc("SaaS Platform Settings")
    except Exception:
        settings = None
    result = {key: "" for key in TRACKING_PATTERNS}
    if settings is not None:
        for key, (field, pattern) in TRACKING_PATTERNS.items():
            value = str(settings.get(field) or "").strip()
            if re.fullmatch(pattern, value):
                result[key] = value
    # An unsaved Single reads blank, which must still mean "ask first".
    result["consent"] = (settings.get("tracking_consent") if settings is not None else None) != "Load immediately"
    result["enabled"] = bool(result["gtm"] or result["ga4"] or result["pixel"])
    return result


def get_profiles() -> list[str]:
    """Official profile links (LinkedIn, Facebook, ...) from SaaS Platform Settings, https only."""
    try:
        text = frappe.get_cached_doc("SaaS Platform Settings").get("social_profiles") or ""
    except Exception:
        return []
    links = [line.strip() for line in str(text).splitlines()]
    return [link for link in links if re.fullmatch(r"https://[^\s\"'<>]{4,200}", link)][:12]


def shared_context(context, modules: list[dict]) -> None:
    """Header, footer and chat data used by every public page, signup included."""
    context.tracking = get_tracking()
    context.nav_features = FEATURE_LIST
    context.nav_modules = modules
    context.support_email = SUPPORT_EMAIL
    context.publisher = PUBLISHER
    context.powered_by = POWERED_BY
    context.year = frappe.utils.nowdate()[:4]
    context.logo = LOGO
    context.logo_width, context.logo_height = LOGO_SIZE
    context.company_site = COMPANY_SITE
    context.whatsapp_number = WHATSAPP_NUMBER
    context.whatsapp_display = WHATSAPP_DISPLAY


def apply_context(context, page: dict, modules: list[dict]) -> None:
    """Put a page description and the shared header/footer data on a web context."""
    shared_context(context, modules)
    context.page = page
    context.glyphs = GLYPHS
    context.icon = ICON
    context.hero_image = HERO_IMAGE
    context.hero_image_dark = HERO_IMAGE_DARK
    context.showcase = [
        {"title": title, "text": text, "image": illustration(name)} for name, title, text in SHOWCASE
    ]
    context.trademark_note = TRADEMARK_NOTE
    context.ai_points = AI_POINTS
    context.ai_note = AI_NOTE
    context.deployments = DEPLOYMENTS
    context.title = page["title"]
    context.no_breadcrumbs = 1
    context.no_sidebar = 1


def requested_path_stem() -> str:
    """``/abc123.txt`` -> ``abc123`` (the single path segment of the current request)."""
    request = getattr(frappe.local, "request", None)
    path = (getattr(request, "path", "") or "").strip("/")
    return path.rsplit("/", 1)[-1].rsplit(".", 1)[0] if path else ""


def requested(name: str) -> str:
    """A route parameter such as ``/features/<slug>``, from the rule match or the URL itself."""
    value = frappe.form_dict.get(name)
    if not value:
        request = getattr(frappe.local, "request", None)
        path = (getattr(request, "path", "") or "").strip("/")
        parts = path.split("/")
        value = parts[1] if len(parts) > 1 else ""
    return str(value or "").strip().lower()


HOME_HOOK = "reckon_saas_platform.marketing.website_user_home_page"


def website_user_home_page(user: str):
    """``get_website_user_home_page`` hook: where Frappe sends a signed-in user after login.

    Without it Frappe falls back to the site's ``home_page`` (the marketing page).
    Module apps chain to every other registered hook, so this one may be called
    from inside theirs; the flag stops the loop.
    """
    if getattr(frappe.flags, "reckon_saas_home_chain", False):
        return None
    frappe.flags.reckon_saas_home_chain = True
    try:
        return landing_for_user(user)
    finally:
        frappe.flags.reckon_saas_home_chain = False


def redirect_signed_in_home(response, request) -> None:
    """``after_request`` hook: signed-in people never stay on ``/`` or ``/index``.

    Sends a 302 that browsers do not cache, so signing out shows the marketing
    page again.
    """
    try:
        path = (getattr(request, "path", "") or "").rstrip("/") or "/"
        if response is None or path not in ("/", "/index") or getattr(request, "method", "GET") != "GET":
            return
        destination = landing_for_user(frappe.session.user)
        if not destination or destination.strip("/") in ("", "index"):
            return
        response.status_code = 302
        response.headers["Location"] = destination
        response.headers["Cache-Control"] = "no-store"
        response.set_data(b"")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Signed-in home redirect")


def _as_route(route: str) -> str:
    route = str(route).strip()
    return route if route.startswith(("/", "http://", "https://")) else f"/{route}"


def landing_for_user(user: str | None) -> str | None:
    """Where a signed-in person belongs instead of the marketing home page.

    ``None`` for guests, who see the marketing site. Administrator goes to Desk.
    Module apps decide their own users' landing page through the
    ``get_website_user_home_page`` hook. Other vendor users go to the module's
    workspace, and tenant users to the page the platform has always chosen for
    them (``saas.get_user_home_page``: their module, or the subscription page
    when access is not active). Anyone else goes to Desk.
    """
    if not user or user == "Guest":
        return None
    if user == "Administrator":
        return "/desk"
    for hook in frappe.get_hooks("get_website_user_home_page") or []:
        if hook == HOME_HOOK:
            continue
        route = frappe.get_attr(hook)(user)
        if route:
            return _as_route(route)

    from reckon_saas_platform.module_registry import get_landing_workspace
    from reckon_saas_platform.saas import get_user_home_page
    from reckon_saas_platform.saas_security import is_vendor_user
    from reckon_saas_platform.tenant_security import get_user_companies

    if get_user_companies(user):
        return _as_route(get_user_home_page(user))
    if is_vendor_user(user):
        # Vendor superusers (not Administrator) work in the module's workspace too.
        return _as_route(get_landing_workspace())
    return "/desk"
