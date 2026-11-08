"""Industry pages: what ReckonERP covers for a sector today, and what is set up for you.

Each page says plainly which parts are standard modules and which are customisation after a requirement
analysis, quoted separately. Nothing here claims a certification, a customer or a result.
"""

from __future__ import annotations

STANDARD = (
    "Accounts, stock, purchasing, sales, HR and payroll come from the standard modules and work "
    "from day one."
)

INDUSTRIES = (
    {
        "slug": "garments",
        "name": "Garments and RMG",
        "title": "Garments ERP software in Bangladesh",
        "description": "Cloud ERP for garment makers in Bangladesh: accounts, stock, purchasing, HR and payroll, with buyer-order and production workflows set up on request.",
        "intro": "Garment factories juggle buyer orders, fabric and trims, many workers and tight cash. ReckonERP gives the finance, stock and people side a single system and shapes the order and production steps to how your factory runs.",
        "modules": ["accounts", "hrms"],
        "standard": [
            "Accounts, bank and cash, with bills and payments kept against each supplier",
            "Stock and warehouses for fabric, trims and finished goods",
            "Purchase orders and supplier bills",
            "HR and payroll for a large workforce: attendance, leave and salary",
        ],
        "custom": [
            "Buyer order and style tracking",
            "Bill of materials and consumption sheets",
            "Production stages and line reports",
            "Print formats and reports your buyers and auditors expect",
        ],
        "faqs": [
            ("Is there a ready-made garments module?", "Not as a separate module today. The standard modules cover accounts, stock, purchasing and payroll, and garment-specific steps such as buyer orders and production stages are set up on request after a requirement analysis, quoted separately."),
            ("Can it handle a large payroll?", "The HRMS module covers employees, attendance, shifts, leave and payroll. For very large or multi-site factories we advise on set-up during analysis."),
            ("Can you run it on our own server?", "Yes. A dedicated cloud or on-premises installation is available on request."),
        ],
    },
    {
        "slug": "textile",
        "name": "Textile",
        "title": "Textile ERP software in Bangladesh",
        "description": "Cloud ERP for textile mills and traders in Bangladesh: accounts, stock, purchasing and payroll, with process-specific steps set up on request.",
        "intro": "Textile businesses move yarn, fabric and chemicals through several stages and need to know cost and stock at each one. ReckonERP covers the money, stock and people, and we add the process steps your mill needs.",
        "modules": ["accounts", "hrms"],
        "standard": [
            "Accounts with supplier and customer ledgers",
            "Stock and warehouses by item and location",
            "Purchasing and supplier bills",
            "Payroll and attendance",
        ],
        "custom": [
            "Process stages from yarn to finished fabric",
            "Batch and lot tracking",
            "Wastage and yield reports",
            "Customer-specific print formats",
        ],
        "faqs": [
            ("Do you offer a textile-specific module?", "Not today. Standard modules cover the core, and process-specific work is customisation after requirement analysis, quoted separately."),
            ("Can we track stock by batch?", "Batch and lot tracking can be set up as part of a customisation project."),
            ("Can we start small?", "Yes. Start with Accounts and add modules and customisation as you grow."),
        ],
    },
    {
        "slug": "pharmaceutical",
        "name": "Pharmaceutical",
        "title": "Pharmaceutical ERP software in Bangladesh",
        "description": "Cloud ERP for pharmaceutical companies and distributors in Bangladesh: accounts, stock, distribution, with batch and expiry workflows set up on request.",
        "intro": "Pharmaceutical companies and distributors care about batches, expiry dates and clean records. ReckonERP covers accounts, stock and distribution, and batch and expiry controls are set up to your requirements.",
        "modules": ["distribution", "accounts"],
        "standard": [
            "Distribution routes, retailer dues and collections for pharmacy and agent networks",
            "Stock and warehouses",
            "Accounts, purchasing and supplier bills",
            "Roles that limit who can see and change records",
        ],
        "custom": [
            "Batch numbers and expiry tracking",
            "Controlled-item handling and approval steps",
            "Reports and print formats for your records",
        ],
        "faqs": [
            ("Does it meet pharmaceutical regulations?", "ReckonERP does not claim a regulatory certification. Batch, expiry and approval workflows can be set up to match your own quality procedures after requirement analysis."),
            ("Can it serve a distributor of medicines?", "The Distribution module covers routes, retailer dues, collections and stock. Batch and expiry controls are added as customisation."),
            ("Who owns the data?", "Each company works in its own private workspace, and your data can be exported."),
        ],
    },
    {
        "slug": "healthcare",
        "name": "Healthcare",
        "title": "Healthcare ERP software in Bangladesh",
        "description": "Cloud ERP for clinics and hospitals in Bangladesh: accounts, stock, purchasing and HR, with clinical workflows scoped separately on request.",
        "intro": "Clinics and hospitals need clean finances, medicine and supply stock, and rostered staff. ReckonERP covers those back-office needs, and anything clinical is scoped separately with you.",
        "modules": ["accounts", "hrms"],
        "standard": [
            "Accounts, billing and payments",
            "Stock for medicine and supplies, with purchasing",
            "HR, shifts, leave and payroll",
            "Roles and permissions that keep records apart",
        ],
        "custom": [
            "Patient and appointment workflows, scoped after analysis",
            "Department and cost-centre reporting",
            "Integration with the systems you already use",
        ],
        "faqs": [
            ("Is it a hospital management system?", "No. It covers the business back office: accounts, stock, purchasing and HR. Clinical workflows are scoped separately and quoted after analysis."),
            ("Can we keep data on our own premises?", "Yes. On-premises installation is available on request."),
            ("Is patient data protected?", "Records are kept in your company's private workspace with permission rules. Discuss your data-protection requirements with us during analysis."),
        ],
    },
    {
        "slug": "manufacturing",
        "name": "Manufacturing",
        "title": "Manufacturing ERP software in Bangladesh",
        "description": "Cloud ERP for manufacturers in Bangladesh: accounts, stock, purchasing and payroll, with production planning and costing set up on request.",
        "intro": "Manufacturers need to know what they hold, what they owe and what each product costs. ReckonERP gives you accounts, stock, purchasing and people in one system, and production steps are shaped to your plant.",
        "modules": ["accounts", "hrms"],
        "standard": [
            "Accounts and ledgers with cash and bank",
            "Stock and warehouses for raw material and finished goods",
            "Purchase orders, supplier bills and payments",
            "Payroll and attendance",
        ],
        "custom": [
            "Bill of materials and production orders",
            "Product costing and wastage reports",
            "Quality checks and approvals",
        ],
        "faqs": [
            ("Does it include production planning?", "Production planning and costing are set up through customisation after requirement analysis, quoted separately. The standard modules cover accounts, stock, purchasing and payroll."),
            ("Can we add modules later?", "Yes. Each module is its own subscription and can be added from your Subscription page."),
            ("Can several factories use it?", "Multi-site set-up is discussed during analysis. Dedicated cloud and on-premises options are available."),
        ],
    },
    {
        "slug": "trading",
        "name": "Trading and wholesale",
        "title": "Trading business ERP software in Bangladesh",
        "description": "Cloud ERP for trading and wholesale businesses in Bangladesh: sales, purchases, stock, dues and accounts in one place. Start online today.",
        "intro": "Traders buy, store and sell all day and live on stock levels and customer dues. ReckonERP's Accounts module covers invoices, bills, stock and books so you always know what you hold and who owes you.",
        "modules": ["accounts", "crm"],
        "standard": [
            "Sales invoices, quotations and customer dues",
            "Purchase orders, bills and supplier payments",
            "Stock and warehouses with reorder visibility",
            "Cash, bank and books in a Tally-style layout",
        ],
        "custom": [
            "Price lists by customer group",
            "Credit-limit rules and approvals",
            "Imports from your spreadsheets",
        ],
        "faqs": [
            ("Can a small trader use it?", "Yes. Start with the Accounts module on a self-serve plan and add others when you need them."),
            ("Can I import my spreadsheet data?", "Data migration is available as an additional service, quoted by how much data there is."),
            ("Can my sales team track leads too?", "Yes, add the CRM module for leads, deals and organizations."),
        ],
    },
    {
        "slug": "fmcg-distribution",
        "name": "FMCG distribution",
        "title": "FMCG distribution software in Bangladesh",
        "description": "Distribution management software for FMCG distributors in Bangladesh: routes, retailer dues, DSR cash custody, stock and accounts. Start online.",
        "intro": "FMCG distributors run routes, collect cash daily and carry goods for principals. The Distribution module is built for exactly that, with a Bangla-first mobile screen for the field team.",
        "modules": ["distribution", "accounts"],
        "standard": [
            "Route planning and delivery tracking per SR and DSR",
            "Retailer dues, collections and running balances",
            "DSR cash custody: collected and handed in",
            "Supplier-provided goods tracked alongside your own stock",
            "A mobile app in the phone's browser, designed Bangla-first",
        ],
        "custom": [
            "Principal-specific reports",
            "Scheme and discount rules",
            "Integration with your accounting and messaging channels",
        ],
        "faqs": [
            ("Is distribution a ready-made module?", "Yes. The Distribution module is a standard subscription with its own plans, shown on the pricing page."),
            ("Do reps need an app?", "No. The field screens work in the phone's browser."),
            ("Does it post to my accounts?", "Yes. Invoices, stock and payments post to your Company's books."),
        ],
    },
)
