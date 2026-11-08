"""Marketing text for each module's page: overview, what is inside, who it is for,
what the subscription includes and leaves out, and the service questions every buyer asks.

Facts here come from each product app's own registration (features, roles) and
description. Prices are never written here; they are read from the live SaaS Plan
records, so a price change needs no edit. Modules not listed fall back to their
registry description, so a new module still gets a complete page.
"""

from __future__ import annotations

COMMON_EXCLUSIONS = (
    "Data migration from spreadsheets or other software (quoted separately)",
    "Custom screens, reports, print formats and workflows beyond the standard module",
    "Training sessions, on-site visits and requirement workshops (paid services)",
    "Third-party charges such as SMS, WhatsApp, email or AI provider usage",
    "Hardware and devices such as printers, scanners and phones",
)
COMMON_INCLUSIONS = (
    "Your own private company workspace, separate from every other customer",
    "Use in English or Bangla where the screens are translated",
    "Roles so each team member sees only what they need",
    "Hosted, backed-up cloud service with software updates",
    "Basic help by email and WhatsApp on how to use the module",
)

MODULE_DETAILS = {
    "distribution": {
        "overview": [
            "ReckonERP Distribution runs the daily work of an FMCG distributor: planning SR and DSR routes, delivering to retailers, collecting what they owe, and keeping stock and cash straight at the end of the day.",
            "It is built for teams that work from vans and phones. Field staff use a Bangla-first mobile app in the browser, while the office sees routes, dues and cash in real time and the books update underneath.",
            "Every company works in its own private workspace on ERPNext, so invoices, stock and payments post to real accounting records rather than a separate spreadsheet.",
        ],
        "highlights": [
            ("DSR and SR routes", "Plan the day's visits and deliveries per route, and see what each representative delivered."),
            ("Retailer dues", "Keep a running balance per retailer and collect against open invoices in the field."),
            ("DSR cash custody", "Know how much cash each DSR carries and record what is handed in."),
            ("Supplier-provided goods", "Handle goods supplied by principals alongside your own stock."),
            ("Bangla-first mobile app", "Field screens work in the phone browser with Bangla labels."),
            ("Accounting underneath", "Invoices, stock and payments post to your company's books."),
        ],
        "use_cases": [
            "FMCG distributors and sub-distributors with SR and DSR teams",
            "Wholesalers who deliver by van and collect dues from retailers",
            "Companies that hold goods for principals as well as their own stock",
        ],
        "inclusions": ["Route planning and delivery tracking", "Retailer dues and collections", "DSR cash custody", "Supplier-provided goods", "Bangla-first mobile app", "Admin, Manager, User and Master Data Manager roles"],
        "exclusions": ["Handheld devices and printers", "Route optimisation by map or GPS tracking hardware", "Integration with your principals' own systems"],
        "faqs": [
            ("Can my field team use it on a phone?", "Yes. The Distribution module includes a Bangla-first mobile app that works in the phone's browser, so there is nothing to install."),
            ("Does it handle accounting and stock?", "It runs on ERPNext, so invoices, payments and stock post to your Company's books."),
            ("Does it track cash carried by each DSR?", "Yes. DSR cash custody records what each DSR collected and what was handed in."),
        ],
    },
    "accounts": {
        "overview": [
            "ReckonERP Accounts gives a small business clean books without the complexity of a full ERP rollout: sales invoices and quotations, purchase bills and orders, stock, cash and bank, and reports in a Tally-style layout.",
            "It is a simpler set of screens over ERPNext's accounting, so the numbers are real double-entry records. Owners and accountants can read the books in the familiar Tally-style views, in English or Bangla.",
            "Roles separate sales, purchase and stock work, so staff only open what their job needs.",
        ],
        "highlights": [
            ("Sales invoices and quotations", "Quote, invoice and track what customers owe."),
            ("Purchase bills and orders", "Record supplier bills and orders and what you owe."),
            ("Stock and warehouses", "Keep stock in step with what you buy and sell."),
            ("Cash, bank and payments", "Record receipts and payments in one place."),
            ("Tally-style books and reports", "Ledgers, day books and summaries in a layout accountants know."),
            ("Team roles", "Separate roles for sales, purchase and stock staff."),
        ],
        "use_cases": [
            "Shops, traders and small companies that need accurate books",
            "Businesses moving from spreadsheets or desktop accounting to the cloud",
            "Owners who want to see profit, dues and cash without learning a large ERP",
        ],
        "inclusions": ["Sales invoices and quotations", "Purchase bills and orders", "Stock and warehouses", "Cash, bank and payments", "Tally-style books and reports", "Team roles for sales, purchase and stock"],
        "exclusions": ["Payroll and HR (see the HRMS module)", "Statutory return filing with the tax authority", "Bank feed integrations"],
        "faqs": [
            ("Is this a full accounting system?", "Yes. It is built on ERPNext's accounting with a simpler set of screens for small businesses."),
            ("Can my accountant see Tally-style reports?", "Yes. The module includes ledgers, books and summaries in a Tally-style layout."),
        ],
    },
    "sales_agent": {
        "overview": [
            "ReckonERP Sales AI Agent finds businesses worth contacting, researches each one from its own website, scores the leads and prepares follow-ups, with a person approving every message before it is sent.",
            "Research keeps its evidence next to each claim, scoring uses fixed rules you can read and explain, and leads sync to your CRM so your team can pick up where the agent stopped.",
            "Channels such as email, SMS and WhatsApp are connected one by one on a single Integrations page, and each business keeps its own keys.",
        ],
        "highlights": [
            ("Lead discovery campaigns", "Run campaigns that find businesses worth contacting."),
            ("Website research with evidence", "Each finding links back to where it came from."),
            ("Rule-based lead scoring", "Scores you can read, explain and adjust."),
            ("CRM sync", "Qualified leads flow to your CRM."),
            ("Email sequences with approval", "Follow-ups are drafted for you and wait for a person to approve."),
            ("AI research and drafting", "AI helps with research and first drafts, never with sending."),
        ],
        "use_cases": [
            "B2B sales teams that need a steady flow of qualified leads",
            "Agencies and suppliers prospecting businesses in a region",
            "Teams that want AI help but a human decision before anything is sent",
        ],
        "inclusions": ["Lead discovery campaigns", "Website research with evidence", "Rule-based lead scoring", "CRM sync", "Email sequences with approval", "AI research and drafting tools"],
        "exclusions": ["AI usage and channel charges (WhatsApp, SMS, voice, email providers) are billed in addition", "Bought contact lists", "Sending without approval"],
        "faqs": [
            ("Which channels can it use?", "Website chat, WhatsApp, Facebook Messenger, Instagram, LinkedIn, Twilio, SMS gateways and email. See the integrations page for the full list."),
            ("Does it need my own AI account?", "The platform operator can provide the AI service for everyone, and a business may bring its own if the operator allows it."),
            ("Will it message people without approval?", "No. Drafts wait for a person's approval before any message is sent."),
        ],
    },
    "hrms": {
        "overview": [
            "ReckonERP HRMS is compact HR and payroll for small businesses: employee records, attendance and shifts, leave, and payroll, in one workspace per company.",
            "It keeps the everyday HR work simple, so a business owner or HR officer can run attendance, leave and the monthly payroll without learning a large HR suite.",
            "Team members get roles that match their work, from HR and payroll managers to employee self-service, and each company's people data stays separate from every other customer.",
        ],
        "highlights": [
            ("Employees", "One record per person with the details HR needs."),
            ("Attendance and shifts", "Record attendance and organise shifts."),
            ("Leave", "Employees request leave and managers approve it."),
            ("Payroll", "Run payroll from attendance and leave."),
            ("Roles for HR work", "HR manager, payroll manager, talent admin and employee self-service roles."),
            ("Private per company", "Every company's HR data is kept apart."),
        ],
        "use_cases": [
            "Small and growing companies that run HR from spreadsheets",
            "Businesses that need monthly payroll tied to real attendance",
            "Owners who want employees to see their own leave and records",
        ],
        "inclusions": ["Employees", "Attendance and shifts", "Leave", "Payroll", "HR manager, payroll manager, talent admin and employee self-service roles"],
        "exclusions": ["Statutory filings and tax returns", "Biometric or attendance hardware", "Recruitment portals beyond the included talent role"],
        "faqs": [
            ("Can employees see their own information?", "Yes. The Employee Self Service role lets each person see their own records, subject to what the company allows."),
            ("Is payroll based on attendance?", "Payroll is built from the attendance and leave you record in the module."),
        ],
    },
    "crm": {
        "overview": [
            "ReckonERP CRM gives sales teams one place for leads, deals and the organizations behind them, so nothing a customer said lives only in someone's head or inbox.",
            "Each company works in its own private CRM, with an admin role for the owner and a user role for the team, and records stay separate from every other customer.",
            "It pairs with the Sales AI Agent: the agent finds and qualifies leads, and the CRM is where your team follows them up.",
        ],
        "highlights": [
            ("Leads", "Capture and track every enquiry."),
            ("Deals", "Move opportunities through your pipeline."),
            ("Organizations", "Keep the companies and contacts behind each deal together."),
            ("Admin and user roles", "Owners manage the CRM; the team works in it."),
            ("Private per company", "Your records are separate from every other customer."),
            ("Works with the Sales AI Agent", "Qualified leads sync straight in."),
        ],
        "use_cases": [
            "Sales teams that track leads in spreadsheets or chat threads",
            "Businesses that want one pipeline for leads, deals and companies",
            "Teams adding the Sales AI Agent to feed their pipeline",
        ],
        "inclusions": ["Leads", "Deals", "Organizations", "Admin and user roles"],
        "exclusions": ["Email and telephony provider charges", "Marketing automation beyond the module", "Custom pipelines and fields (customisation is quoted separately)"],
        "faqs": [
            ("Can I use it with the Sales AI Agent?", "Yes. The agent syncs qualified leads into the CRM, where your team follows them up."),
        ],
    },
}


def service_faqs(name: str, plans: list[dict], inclusions: list[str], exclusions: list[str]) -> list[tuple[str, str]]:
    """The questions every buyer asks about price, support and services, answered for ``name``."""
    if plans:
        listing = "; ".join(f"{p['name']}: {p['price_text']}" for p in plans)
        trial = next((p["trial_days"] for p in plans if p["trial_days"]), 0)
        price = (
            f"{name} is sold as a subscription. Current plans: {listing}. "
            "The price, billing period and any trial days are shown again at signup, before you pay."
        )
        trial_answer = (
            f"Some plans start with a free trial (up to {trial} days). The trial length for each plan is shown at signup."
            if trial
            else "Trial days depend on the plan; any trial is shown at signup before you pay."
        )
    else:
        price = f"{name} is sold as a subscription. The plan, price, billing period and any trial days are shown at signup, before you pay."
        trial_answer = "Trial days depend on the plan; any trial is shown at signup before you pay."
    return [
        (f"How much does {name} cost?", price),
        (f"Is there a free trial for {name}?", trial_answer),
        (f"What is included in the {name} subscription?", "Included: " + "; ".join(inclusions) + "."),
        (f"What is not included in {name}?", "Not included: " + "; ".join(exclusions) + ". Ask us for a quote for any of these."),
        (f"What support do I get with {name}?", "Basic help by email and WhatsApp on how to use the module is included with your subscription. Faster response, a named contact or regular check-ins are available as paid support on request."),
        (f"Do you provide training for {name}?", "Yes, as a paid service. We can train your team online or in person, in English or Bangla. Training is quoted separately and is not part of the subscription."),
        ("Can you support us on-site?", "On-site support is available on request and quoted separately, including travel. Most customers start online and ask for a visit only when they need one."),
        ("Do you do requirement analysis before we start?", "Self-service signup needs none. If your process is complex, we offer a paid requirement analysis: we study how you work, map it to the module and tell you what is covered, what needs configuration and what would need customisation."),
        (f"Can {name} be customised for us?", "Yes. Additional customisations such as extra fields, reports, print formats, workflows and integrations are quoted after requirement analysis. For full control we also offer dedicated cloud and on-premises installation."),
        (f"Can you move our existing data into {name}?", "Data migration from spreadsheets or other software is available as an additional service, quoted by the amount and quality of the data."),
        ("Can I add or change modules later?", "Yes. Subscribe to another module from your Subscription page at any time; each module has its own plan and invoice."),
        ("How do I pay?", "After signup you receive an invoice by email (with a PDF), and a link by SMS. Pay by bKash, Nagad, Rocket or bank transfer, enter the transaction reference on your Subscription page, and we unlock your workspace once the payment is verified."),
    ]
