"""Links from the product site to the company site (Reckon Technologies Ltd.).

Everything that points at the company site lives here, so adding a module or a post is one entry.
All of these are ordinary followed links. Nothing here is copied from the company site; the pages
simply send readers there for services and consulting.
"""

from __future__ import annotations

import re

COMPANY_NAME = "Reckon Technologies Ltd."
COMPANY_URL = "https://www.reckon.tech/"
COMPANY_LINKEDIN = "https://www.linkedin.com/company/reckontech"
COMPANY_FACEBOOK = "https://www.facebook.com/reckontechnologies"
CONTACT_URL = COMPANY_URL + "contact/"
INDUSTRIES_URL = COMPANY_URL + "industries/"

# The footer's "Services" group: (link text, address).
SERVICES = (
    ("Salesforce consulting", COMPANY_URL + "salesforce-consulting-bangladesh/"),
    ("ERPNext implementation", COMPANY_URL + "erpnext-implementation-bangladesh/"),
    ("AI agent development", COMPANY_URL + "ai-agent-development/"),
    ("Offshore Salesforce development", COMPANY_URL + "offshore-salesforce-development/"),
)

_IMPLEMENTATION = {
    "lead": "Reckon Technologies can set this up for your business.",
    "text": "Implementation, data migration and training by Reckon Technologies",
    "url": COMPANY_URL + "service/reckonerp/",
}

# "Need help implementing it?" box on a module page, by module key.
# A module without an entry gets DEFAULT_MODULE_HELP, so a new module needs nothing here to work.
MODULE_HELP = {
    "crm": {
        "lead": "Need Salesforce instead of a built-in CRM?",
        "text": "Talk to our Salesforce consultants",
        "url": COMPANY_URL + "salesforce-consulting-bangladesh/",
    },
    "accounts": _IMPLEMENTATION,
    "distribution": _IMPLEMENTATION,
    "hrms": _IMPLEMENTATION,
    "sales_agent": {
        "lead": "Want an AI agent built around your own processes?",
        "text": "Custom AI agents for your own systems",
        "url": COMPANY_URL + "ai-agent-development/",
    },
}
DEFAULT_MODULE_HELP = {
    "lead": "Need help setting this up?",
    "text": "Talk to Reckon Technologies",
    "url": CONTACT_URL,
}

# "Consultant's view" box at the end of a blog post: app article title -> (company article address, its title).
BLOG_VIEWS = {
    "ERP Software in Bangladesh: A Buyer's Guide": (COMPANY_URL + "erp-selection-consulting-bangladesh/", "How We Help Bangladeshi Companies Select the Right ERP"),
    "How to Choose an ERP Provider in Bangladesh": (COMPANY_URL + "erp-implementation-partner-bangladesh/", "What to Expect From an ERP Implementation Partner in Bangladesh"),
    "ERP Implementation Cost in Bangladesh: What Drives It": (COMPANY_URL + "erp-implementation-budget-planning/", "Planning an ERP Budget: Where Implementation Effort Really Goes"),
    "How AI Agents Are Changing Business Automation": (COMPANY_URL + "ai-agents-business-operations-value/", "Where AI Agents Deliver Real Value in Business Operations"),
    "AI Agent vs AI Chatbot: What Is the Difference?": (COMPANY_URL + "chatbot-or-ai-agent-client-projects/", "Chatbot or AI Agent? How We Decide for Client Projects"),
    "Automate Sales and Marketing with AI Agents": (COMPANY_URL + "ai-assisted-sales-process-salesforce-crm/", "Designing AI-Assisted Sales Processes in Salesforce and CRM"),
    "Distribution Management Software for FMCG Businesses": (COMPANY_URL + "fmcg-distribution-digitisation-lessons/", "Digitising FMCG Distribution: Lessons From Implementation Projects"),
    "HR and Payroll Automation for Bangladeshi Businesses": (COMPANY_URL + "hr-payroll-automation-rollout/", "Rolling Out HR and Payroll Automation Without Disrupting Payday"),
    "How to Implement AI in ERP Systems, Step by Step": (COMPANY_URL + "ai-erp-pilot-plan-90-days/", "An AI-in-ERP Pilot Plan: 30, 60 and 90 Days"),
    "Cloud ERP vs On-Premises ERP: How to Choose": (COMPANY_URL + "cloud-vs-on-premises-erp-infrastructure-questions/", "Cloud or On-Premises ERP: Infrastructure Questions We Ask Every Client"),
    "Spreadsheets vs Accounting Software vs ERP": (COMPANY_URL + "outgrown-spreadsheets-accounting-software/", "Signs Your Business Has Outgrown Spreadsheets and Accounting Software"),
    "FMCG Route Sales: Spreadsheets vs a Distribution ERP": (COMPANY_URL + "route-sales-migration-plan/", "Moving Route Sales Off Spreadsheets: A Practical Migration Plan"),
    "Shared Cloud, Dedicated Cloud or On-Premises ERP?": (COMPANY_URL + "erp-hosting-model-security-compliance-cost/", "Choosing an ERP Hosting Model: Security, Compliance and Cost Trade-offs"),
    "HR and Payroll: Spreadsheets vs an HRMS Module": (COMPANY_URL + "hr-spreadsheets-to-hrms-migration-checklist/", "Migrating HR Records From Spreadsheets to an HRMS: A Checklist"),
    "Standalone CRM vs an ERP-Integrated CRM": (COMPANY_URL + "salesforce-vs-erp-integrated-crm/", "Salesforce or ERP-Integrated CRM? An Architect's Decision Guide"),
    "Open-Source, Proprietary or Custom-Built ERP?": (COMPANY_URL + "erp-platform-erpnext-odoo-salesforce-custom/", "ERPNext, Odoo, Salesforce or Custom Build: How We Recommend a Platform"),
    "Rules, Machine Learning or LLMs: AI Options in ERP": (COMPANY_URL + "choosing-ai-technique-rules-ml-llm/", "Rules, Machine Learning or LLMs: Choosing the Right AI Technique for Your Process"),
    "Hosted AI vs Self-Hosted AI Models for ERP Data": (COMPANY_URL + "ai-data-security-hosted-vs-self-hosted/", "Keeping Business Data Safe With AI: Hosted vs Self-Hosted Models"),
    "Standard vs Customised ERP: What Enterprises Need": (COMPANY_URL + "when-to-customise-erp/", "When to Customise ERP and When to Change the Process"),
}


def _key(title: str) -> str:
    """Titles compare without regard to curly quotes, case or stray spaces."""
    return re.sub(r"\s+", " ", str(title or "").replace("’", "'").replace("‘", "'")).strip().lower()


_VIEWS = {_key(title): view for title, view in BLOG_VIEWS.items()}


def blog_view(title: str) -> dict | None:
    """The matching company article for a post, or None (then the post shows no box)."""
    found = _VIEWS.get(_key(title))
    return {"url": found[0], "title": found[1]} if found else None


def module_help(key: str) -> dict:
    return dict(MODULE_HELP.get(key) or DEFAULT_MODULE_HELP)


def company_org() -> dict:
    """The company as a schema.org Organization, used as publisher, manufacturer and parent."""
    return {
        "@type": "Organization",
        "name": COMPANY_NAME,
        "url": COMPANY_URL,
        "sameAs": [COMPANY_LINKEDIN, COMPANY_FACEBOOK],
    }
