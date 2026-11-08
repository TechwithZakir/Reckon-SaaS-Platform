"""Ten comparison posts, loaded once as drafts in the same SEO Article records the admin tool uses.

They are written to be read by people and quoted by AI assistants: a short answer first, a
comparison table, when each option fits, where ReckonERP fits, and a short FAQ that becomes
FAQ structured data. They compare approaches and technology choices, not named competitors,
and they make no claim about anything this platform does not do. A vendor user reviews each
draft in **SEO Agent Studio** and publishes it; nothing is live until then.
"""

from __future__ import annotations

import frappe

from reckon_saas_platform import blog, marketing


def table(head: list[str], rows: list[list[str]]) -> str:
    header = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"


def bullets(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def faq(pairs: list[tuple[str, str]]) -> str:
    return "<h2>Frequently asked questions</h2>" + "".join(f"<h3>{q}</h3><p>{a}</p>" for q, a in pairs)


def short_answer(text: str) -> str:
    return f"<p><strong>Short answer:</strong> {text}</p>"


POSTS = [
    {
        "slug": "cloud-erp-vs-on-premises-erp",
        "title": "Cloud ERP vs On-Premises ERP: How to Choose",
        "summary": "A plain comparison of cloud and on-premises ERP: cost, control, upkeep and speed, and how to choose for your business.",
        "keywords": "cloud ERP, on-premises ERP, ERP deployment, ERP comparison",
        "module": "",
        "body": short_answer("choose cloud ERP when you want to start quickly and avoid running servers; choose on-premises when rules, connectivity or control make your own servers the safer path. Many businesses start in the cloud and move to a dedicated or on-premises setup only if they must.")
        + "<h2>What each option means</h2><p>With cloud ERP the vendor runs the servers, backups and updates, and your team signs in from a browser. With on-premises ERP the software runs on servers you own or rent, and your own people, or a partner, look after them.</p>"
        + table(["Question", "Cloud ERP", "On-premises ERP"], [
            ["How fast can we start?", "Usually days, because nothing has to be installed.", "Weeks, because servers, installation and setup come first."],
            ["Who runs the servers?", "The provider.", "You or your partner."],
            ["Upfront cost", "Low; you pay a subscription.", "Higher; hardware and setup come first."],
            ["Control over data location", "Set by the provider, or by a dedicated cloud.", "Full control."],
            ["Updates and backups", "Handled for you.", "Your responsibility."],
            ["Working with a weak internet link", "Needs a steady connection.", "Works on your own network."],
        ])
        + "<h2>When cloud fits</h2>" + bullets(["You want to be working within days, not months.", "You have no IT team to run servers and backups.", "Your staff work from several places, such as an office, vans and homes.", "You would rather pay monthly than invest upfront."])
        + "<h2>When on-premises fits</h2>" + bullets(["A rule or customer contract says the data must stay on your own premises.", "Your site has an unreliable internet link and the work cannot pause.", "You already run servers and have people to look after them.", "You need deep control over when changes are applied."])
        + "<h2>The middle path</h2><p>A dedicated cloud gives you your own server run by someone else. You keep isolation and a release schedule of your own without buying hardware. We compare it in detail in <a href=\"/blog/shared-cloud-vs-dedicated-cloud-vs-on-premises\">Shared Cloud, Dedicated Cloud or On-Premises ERP?</a></p>"
        + "<h2>Where ReckonERP fits</h2><p>ReckonERP starts as a shared cloud service: you sign up, pick a module such as <a href=\"/modules/accounts\">Accounts</a> or <a href=\"/modules/distribution\">Distribution</a>, and work in your own private company workspace. If you later need your own server or your own premises, a dedicated cloud or on-premises installation is available on request, quoted separately. See <a href=\"/pricing\">pricing</a> for the subscription plans.</p>"
        + faq([("Is cloud ERP safe for business data?", "It can be, but it depends on how the service is run. In ReckonERP every customer works in its own Company with permission rules that keep records apart, and a dedicated installation is available if you need stronger isolation."), ("Can we move from cloud to on-premises later?", "Yes. Your data can be exported and loaded into a dedicated or on-premises installation. Migration is a planned, quoted piece of work."), ("Does cloud ERP cost less over time?", "Not always. It costs less to start and to look after. Over many years the answer depends on your size, your IT staff and how much you customise.")]),
    },
    {
        "slug": "spreadsheets-vs-accounting-software-vs-erp",
        "title": "Spreadsheets vs Accounting Software vs ERP",
        "summary": "Spreadsheets, accounting software or a full ERP? See what each does well, where it breaks, and when it is time to move up.",
        "keywords": "spreadsheets vs ERP, accounting software, small business ERP, inventory",
        "module": "accounts",
        "body": short_answer("spreadsheets are fine for a one-person business with few transactions; accounting software suits a business whose main need is clean books; an ERP is worth it when stock, purchasing, sales and accounts need to agree with each other.")
        + "<h2>How the three differ</h2>"
        + table(["Need", "Spreadsheets", "Accounting software", "ERP"], [
            ["Record sales and purchases", "By hand, one sheet at a time.", "Yes, with invoices and bills.", "Yes, linked to stock and orders."],
            ["Know what is in stock", "A sheet someone must keep updated.", "Basic, or not at all.", "Updated by every sale and purchase."],
            ["Books you can trust", "Depends on careful formulas.", "Double-entry books.", "Double-entry books fed by every module."],
            ["Several people at once", "Easy to overwrite each other.", "Yes, with roles.", "Yes, with roles per area."],
            ["Growth beyond accounts", "Gets slow and risky.", "Needs add-ons.", "Add modules as you grow."],
        ])
        + "<h2>Where spreadsheets break first</h2>" + bullets(["Two people edit the same file and one change is lost.", "A formula is overwritten and nobody notices for months.", "Stock on the sheet no longer matches the shelf.", "The owner cannot see dues or profit without asking someone to build a report."])
        + "<h2>When accounting software is enough</h2><p>If you sell a small range, hold little stock and mostly need invoices, bills, payments and tax-ready books, accounting software does the job without the weight of a full ERP.</p>"
        + "<h2>When to move to an ERP</h2><p>Move when the same data is typed in more than one place, when stock and sales disagree, or when you need purchasing, warehouses and several staff roles working together.</p>"
        + "<h2>Where ReckonERP fits</h2><p>The <a href=\"/modules/accounts\">Accounts module</a> gives a small business sales invoices and quotations, purchase bills and orders, stock and warehouses, cash and bank, and books in a Tally-style layout. It runs on ERPNext's accounting, so you can grow into other modules, such as <a href=\"/modules/distribution\">Distribution</a> or <a href=\"/modules/hrms\">HRMS</a>, without changing systems.</p>"
        + faq([("Can I move my spreadsheet data into ERP?", "Yes. Data migration from spreadsheets is available as an additional service, quoted by how much data there is and how clean it is."), ("Is an ERP too much for a small business?", "Not if you start with one module. You pay for the module you use and add others later."), ("Will my accountant be able to use it?", "The Accounts module includes books and reports in a Tally-style layout that accountants know.")]),
    },
    {
        "slug": "fmcg-route-sales-spreadsheets-vs-distribution-erp",
        "title": "FMCG Route Sales: Spreadsheets vs a Distribution ERP",
        "summary": "Compare FMCG route sales on spreadsheets and chat with a distribution ERP: routes, dues, cash custody and stock.",
        "keywords": "FMCG distribution software, route sales, DSR, retailer dues, cash custody",
        "module": "distribution",
        "body": short_answer("spreadsheets and chat groups work for a handful of retailers; once you have several routes, sales reps and daily collections, a distribution ERP keeps routes, dues, cash and stock in one place and stops money leaking between them.")
        + "<h2>The daily problem</h2><p>A distributor plans routes, loads vans, delivers to retailers, collects cash and cheques, and settles stock at night. Every step is a place where a number can be lost: a delivery not recorded, a collection not handed in, a retailer's balance out of date.</p>"
        + table(["Task", "Spreadsheets and chat", "Distribution ERP"], [
            ["Plan the day's routes", "A sheet copied to each rep.", "Routes planned per SR and DSR in one system."],
            ["Retailer dues", "A balance column someone must update.", "A running balance per retailer, updated by invoices and collections."],
            ["Cash carried by a DSR", "Counted at the end, then argued about.", "Recorded as collected and handed in, per DSR."],
            ["Goods from principals", "Mixed into your own stock sheet.", "Tracked as supplier-provided goods."],
            ["Field staff on phones", "Photos and messages.", "A mobile screen with Bangla labels."],
            ["Accounting", "Re-typed later.", "Invoices, stock and payments post to the books."],
        ])
        + "<h2>What to look for</h2>" + bullets(["Dues per retailer that update the moment a collection is recorded.", "Cash custody per DSR, so shortages are visible the same day.", "A mobile screen your reps will actually use, in their language.", "Real accounting underneath, so you do not re-enter data."])
        + "<h2>Where ReckonERP fits</h2><p>The <a href=\"/modules/distribution\">Distribution module</a> covers route planning and delivery tracking, retailer dues and collections, DSR cash custody, supplier-provided goods and a Bangla-first mobile app that works in the phone's browser. It posts to ERPNext's accounting, and each company works in its own private workspace. Plans and prices are on the <a href=\"/pricing\">pricing page</a>.</p>"
        + faq([("Do my reps need to install an app?", "No. The field screens work in the phone's browser."), ("Can it track cash carried by each DSR?", "Yes. DSR cash custody records what each DSR collected and what was handed in."), ("Does it replace my accounting?", "It posts invoices, stock and payments to your Company's books, so you do not keep two sets of numbers.")]),
    },
    {
        "slug": "shared-cloud-vs-dedicated-cloud-vs-on-premises",
        "title": "Shared Cloud, Dedicated Cloud or On-Premises ERP?",
        "summary": "Shared cloud, dedicated cloud or on-premises? Compare cost, isolation, control and effort to pick the right ERP deployment.",
        "keywords": "dedicated cloud ERP, shared cloud ERP, on-premises ERP, ERP deployment options",
        "module": "",
        "body": short_answer("start on a shared cloud if you want speed and a low price; move to a dedicated cloud for your own server and release schedule; choose on-premises only when your own premises are a requirement.")
        + "<h2>The three options</h2>"
        + table(["", "Shared cloud", "Dedicated cloud", "On-premises"], [
            ["Where it runs", "A provider's platform, shared by many companies.", "A server just for you, run by a provider.", "Your own servers."],
            ["Isolation", "Each company in its own workspace with permission rules.", "Your own server and database.", "Your own network."],
            ["Start-up time", "Fastest.", "Days to weeks.", "Weeks."],
            ["Customisation", "The standard modules.", "Deeper customisation is practical.", "Full customisation."],
            ["Release timing", "The provider's schedule.", "Agreed with you.", "Yours."],
            ["Who looks after backups", "The provider.", "The provider, to your needs.", "You or a partner."],
            ["Cost shape", "Subscription.", "Subscription plus setup.", "Setup plus your own running costs."],
        ])
        + "<h2>Questions that decide it</h2>" + bullets(["Must data stay on a server only you control?", "Will you customise beyond what the standard modules offer?", "Do you need to approve every update before it reaches your users?", "Do you have people to run servers, or would you rather not?"])
        + "<h2>A sensible path</h2><p>Most companies lose nothing by starting on the shared cloud. You can export your data and move to a dedicated or on-premises installation if a requirement appears. Starting small also shows you what you really need to customise.</p>"
        + "<h2>Where ReckonERP fits</h2><p>All three are offered. The shared cloud is self-service: <a href=\"/reckonerp-signup\">sign up</a> and start. Dedicated cloud and on-premises installations, with customisation, are set up with you and quoted separately. See the <a href=\"/faq\">FAQ</a> for how licences, pricing and implementation work.</p>"
        + faq([("Is a dedicated cloud more secure than a shared one?", "It gives stronger isolation because the server and database are yours alone. A well-run shared cloud with strict permission rules can also be sound; the right choice depends on your requirements."), ("Can we change option later?", "Yes. Moving is a planned piece of work that carries your data across."), ("What does a dedicated cloud cost?", "It is quoted for your needs, because it depends on size, customisation and support.")]),
    },
    {
        "slug": "hr-payroll-spreadsheets-vs-hrms-module",
        "title": "HR and Payroll: Spreadsheets vs an HRMS Module",
        "summary": "Compare running HR and payroll on spreadsheets with an HRMS module: attendance, leave, payroll accuracy and self-service.",
        "keywords": "HRMS, payroll software, attendance and leave, small business HR",
        "module": "hrms",
        "body": short_answer("spreadsheets cope with a small team and a simple payroll; an HRMS pays for itself when attendance, leave and salary rules start to interact, because it computes payroll from the records instead of from someone's memory.")
        + "<h2>What HR work really involves</h2><p>HR is not one task. It is employee records, daily attendance, shifts, leave requests and approvals, and then payroll that depends on all of them. In a spreadsheet each of these lives in a different sheet, and the payroll month is when the gaps show.</p>"
        + table(["Task", "Spreadsheets", "HRMS module"], [
            ["Employee records", "One row per person, easy to let drift.", "A record per employee, kept in one place."],
            ["Attendance and shifts", "Typed in from registers.", "Recorded in the system."],
            ["Leave", "Requests by message, balances by hand.", "Requested and approved in the system."],
            ["Payroll", "Formulas that must be checked every month.", "Built from attendance and leave."],
            ["Employees seeing their own data", "Ask HR.", "A self-service role."],
            ["Privacy", "A file that gets forwarded.", "Roles decide who sees what."],
        ])
        + "<h2>Signs it is time to move</h2>" + bullets(["Payroll takes days and is checked line by line.", "Employees argue about leave balances.", "More than one person edits HR files.", "You need to show who approved what."])
        + "<h2>Before you switch</h2><p>Moving HR to a system goes smoothly when the groundwork is done first. Clean your employee list so every person appears once, write down your working hours and shifts, list the leave types and how many days each allows, and decide who may approve leave and who may run payroll. An hour spent on this saves days of corrections later.</p>"
        + "<h2>Where ReckonERP fits</h2><p>The <a href=\"/modules/hrms\">HRMS module</a> is compact HR and payroll for small businesses: employees, attendance and shifts, leave, and payroll, in a private workspace per company. Roles include HR manager, payroll manager, talent admin and employee self-service. If your accounts also need to be tidy, pair it with <a href=\"/modules/accounts\">Accounts</a>.</p>"
        + faq([("Can employees see their own leave and records?", "Yes. The employee self-service role lets each person see their own records, subject to what the company allows."), ("Is payroll based on attendance?", "Payroll is built from the attendance and leave you record in the module."), ("Does the HRMS file tax returns for us?", "No. Statutory filings and tax returns are outside the module.")]),
    },
    {
        "slug": "standalone-crm-vs-erp-integrated-crm",
        "title": "Standalone CRM vs an ERP-Integrated CRM",
        "summary": "Standalone CRM or CRM built into your ERP? Compare data, reporting, cost and effort to decide what suits your sales team.",
        "keywords": "CRM vs ERP, integrated CRM, sales pipeline, leads and deals",
        "module": "crm",
        "body": short_answer("a standalone CRM is quick to adopt and strong for sales workflows; a CRM that shares data with your ERP gives one customer record across quotes, invoices and payments. Choose by whether your sales team's biggest pain is following up or knowing what the customer owes.")
        + "<h2>Two approaches</h2><p>A standalone CRM lives apart from your accounts and stock. You connect them with imports or integrations. An ERP-integrated CRM sits on the same company data, so the people in sales and in accounts look at the same customer.</p>"
        + table(["Question", "Standalone CRM", "ERP-integrated CRM"], [
            ["Adoption", "Quick; sales teams can start alone.", "Needs the ERP in place, or set up together."],
            ["Customer record", "One for sales, another in accounts.", "One shared record."],
            ["Quote to invoice", "Re-entered or connected by an integration.", "Flows into invoicing."],
            ["What the customer owes", "Not visible to sales.", "Visible alongside the deal."],
            ["Cost and upkeep", "Another system and its connectors.", "One system."],
            ["Flexibility", "Often rich sales-specific features.", "Focused on core sales records."],
        ])
        + "<h2>Questions to ask</h2>" + bullets(["Does sales need to see unpaid invoices before a new deal?", "How many times is the same customer typed in today?", "Who will keep integrations working when something changes?", "Do you want one login and one set of roles?"])
        + "<h2>A quick example</h2><p>Imagine a sales rep about to close a deal with a customer who has two unpaid invoices. In a standalone CRM the rep sees only the deal and promises delivery. With a shared customer record the rep sees the dues first and can agree a payment plan before anything ships. That single view is often what justifies the integration.</p>"
        + "<h2>Where ReckonERP fits</h2><p>The <a href=\"/modules/crm\">CRM module</a> gives sales teams leads, deals and organizations in a private workspace, with admin and user roles. It works with the <a href=\"/modules/sales_agent\">Sales AI Agent</a>, which finds and qualifies leads and syncs them in, so your team follows up instead of searching. Because it belongs to the same platform as <a href=\"/modules/accounts\">Accounts</a>, you can subscribe to both from one account.</p>"
        + faq([("Can I use the CRM without the ERP?", "Yes. Each module is its own subscription, so you can start with the CRM alone."), ("Does the Sales AI Agent message leads on its own?", "No. Drafts wait for a person's approval before any message is sent."), ("Is my CRM data separate from other companies?", "Yes. Every company works in its own private workspace.")]),
    },
    {
        "slug": "open-source-vs-proprietary-vs-custom-built-erp",
        "title": "Open-Source, Proprietary or Custom-Built ERP?",
        "summary": "Compare open-source, proprietary and custom-built ERP stacks on cost, flexibility, risk and long-term ownership.",
        "keywords": "open-source ERP, proprietary ERP, custom ERP, ERP technology stack",
        "module": "",
        "body": short_answer("open-source ERP usually gives a good balance of flexibility and cost if you have a partner who knows it; proprietary suites suit buyers who want a single vendor to hold accountable; a custom build suits only needs no product can meet, and it carries the most risk.")
        + "<h2>The three stacks</h2>"
        + table(["", "Open-source ERP", "Proprietary ERP", "Custom-built ERP"], [
            ["Licence cost", "No licence fee for the software itself.", "Licence or subscription per user or module.", "None, but you pay to build it."],
            ["Flexibility", "High; the code can be extended.", "Limited to what the vendor allows.", "Total."],
            ["Time to first use", "Short.", "Short to medium.", "Long."],
            ["Who maintains it", "The community and your partner.", "The vendor.", "You."],
            ["Lock-in", "Low; you can change partners.", "High.", "High, to whoever built it."],
            ["Main risk", "Needs a capable partner.", "Cost and rigidity.", "Cost, delay and key-person risk."],
        ])
        + "<h2>What to check in any stack</h2>" + bullets(["Is double-entry accounting a real part of it, not an add-on?", "Can you customise without breaking upgrades?", "Is there an API and a way to export your data?", "How do roles and permissions work, and can they separate companies?"])
        + "<h2>Where ReckonERP fits</h2><p>ReckonERP is built on open-source ERP technology and adds what most companies end up needing: separate company workspaces, modules you subscribe to one at a time, Bangla and English screens, and an AI assistant that works inside your own permissions. You get a managed service without being tied to a closed product, and customisation for enterprise packages is quoted separately. See the <a href=\"/features/modular-erp\">modular ERP</a> page for how modules fit together.</p>"
        + faq([("Is open-source ERP less secure?", "Not by nature. Security comes from how the system is configured, run and updated. Open code can be reviewed by many people."), ("Can I leave if I am not happy?", "Yes. You can export your data, which is one of the benefits of an open stack."), ("When is a custom build justified?", "When your process is unlike anything a product supports and the cost of adapting is higher than the cost of building. That is rare.")]),
    },
    {
        "slug": "rules-vs-machine-learning-vs-llm-assistants-in-erp",
        "title": "Rules, Machine Learning or LLMs: AI Options in ERP",
        "summary": "Compare rule-based automation, machine learning and LLM assistants inside an ERP: what each does well and where it needs a person.",
        "keywords": "AI in ERP, LLM assistant, machine learning, rule-based automation, AI technology stack",
        "module": "sales_agent",
        "body": short_answer("use rules where the answer must be exactly the same every time, machine learning where you have lots of history and a clear number to predict, and an LLM assistant where people need to ask questions or draft text. In an ERP the safest design mixes all three and keeps a person approving changes.")
        + "<h2>Three kinds of AI, three jobs</h2>"
        + table(["", "Rules", "Machine learning", "LLM assistants"], [
            ["Good at", "Fixed logic such as scoring or validation.", "Forecasts and anomalies from past data.", "Language: answering questions, summarising, drafting."],
            ["Explainable", "Completely.", "Partly.", "Hard to prove why a sentence was written."],
            ["Needs", "Someone to write the rules.", "Clean history and monitoring.", "Good context and guardrails."],
            ["Can be wrong", "Only if the rule is.", "Yes, on new patterns.", "Yes, and sounds confident."],
            ["Best use in ERP", "Lead scoring, approvals, checks.", "Demand and cash forecasts, odd transactions.", "Asking your records questions, first drafts."],
        ])
        + "<h2>A simple way to start</h2><p>Begin with rules for anything that must be exact, such as scoring leads or checking an order against a limit. Add an assistant for questions and first drafts, because mistakes there are cheap to catch. Bring in machine learning later, once you have a year or more of clean history and a number worth predicting, such as monthly demand.</p>"
        + "<h2>Guardrails that matter</h2>" + bullets(["The assistant only reads what the signed-in user may read.", "Any change is shown as a preview and applied only after a person approves.", "Actions are logged.", "Facts come from your records, not from guesses."])
        + "<h2>Where ReckonERP fits</h2><p>The <a href=\"/features/reckon-ai-assistant\">Reckon AI assistant</a> works inside the permissions of the person asking, and changes are applied only after you review and approve them. The <a href=\"/modules/sales_agent\">Sales AI Agent</a> scores leads with fixed rules you can read, uses AI for research and drafts, and waits for a person to approve any message. AI and integration usage is billed separately. See <a href=\"/features/ai-assisted-selling\">AI-assisted selling</a>.</p>"
        + faq([("Should an AI change my data on its own?", "Not without approval. Show a preview, let a person approve, and keep a log."), ("Do I need machine learning to start?", "No. Start with rules and an assistant for questions and drafts. Add forecasting when you have enough clean history."), ("Why score leads with rules?", "Because you can read and explain the result, and it does not change unexpectedly.")]),
    },
    {
        "slug": "hosted-ai-vs-self-hosted-ai-models-for-erp-data",
        "title": "Hosted AI vs Self-Hosted AI Models for ERP Data",
        "summary": "Hosted AI or self-hosted AI models for ERP data? Compare privacy, quality, cost and effort, and what to ask before you choose.",
        "keywords": "AI privacy, self-hosted AI, hosted AI API, ERP AI, AI technology stack",
        "module": "",
        "body": short_answer("hosted AI services give stronger models with almost no setup, while self-hosted models keep prompts on your own servers at the cost of effort and usually of quality. Pick by how sensitive the data is and how much quality you need, and send only the records a task actually needs.")
        + "<h2>The trade-off</h2>"
        + table(["", "Hosted AI service", "Self-hosted model"], [
            ["Setup", "An account and a key.", "Servers, a model and upkeep."],
            ["Quality", "Typically strongest.", "Depends on the model and hardware."],
            ["Where prompts go", "To the provider.", "Stay on your servers."],
            ["Cost shape", "Pay for what you use.", "Hardware and people, then little per request."],
            ["Speed and scale", "Provider's capacity.", "Your capacity."],
            ["Good fit", "Drafting, research, general questions.", "Sensitive data or strict data rules."],
        ])
        + "<h2>Questions to ask before choosing</h2>" + bullets(["What data would the model see, and could less be enough?", "Does the provider keep prompts, and for how long?", "Who pays for usage and how is it capped?", "Can you switch provider without rebuilding?"])
        + "<h2>A simple way to decide</h2><p>Sort your tasks by how sensitive the data is. Drafting a reply or researching a public website can use a hosted service safely. Anything involving payroll, bank details or confidential contracts deserves either a self-hosted model or a design that never sends those fields at all.</p>"
        + "<h2>Practical safeguards</h2>" + bullets(["Send only the fields a task needs.", "Respect the user's permissions before any record reaches the model.", "Cap monthly usage.", "Keep keys in a protected settings store, not in code."])
        + "<h2>Where ReckonERP fits</h2><p>The AI features can use a hosted provider or an OpenAI-compatible server, including one you run yourself. Each business can keep its own keys, and a monthly call limit caps usage. Usage is billed separately from the module subscription. For dedicated or on-premises installations, ask us about keeping AI on your own servers. See <a href=\"/integrations\">integrations</a> for the services that connect.</p>"
        + faq([("Can I use my own AI server?", "Yes, where the operator allows it, an OpenAI-compatible server address can be used."), ("Does AI see all my records?", "No. It works inside the permissions of the person using it and only receives what a task needs."), ("Who pays for AI usage?", "AI and integration usage is billed separately from your module subscription.")]),
    },
    {
        "slug": "standard-vs-customised-erp-for-enterprises",
        "title": "Standard vs Customised ERP: What Enterprises Need",
        "summary": "Compare standard and customised ERP for enterprises: multi-currency, multi-language, workflows, cost and how to customise safely.",
        "keywords": "customised ERP, enterprise ERP, multi-currency ERP, multi-language ERP, ERP customization",
        "module": "",
        "body": short_answer("start with the standard modules and customise only where your process truly differs. Enterprises usually need more than defaults, such as several currencies, several languages and their own workflows, so plan customisation as a managed project with analysis first, not as a pile of one-off changes.")
        + "<h2>Standard versus customised</h2>"
        + table(["", "Standard ERP", "Customised ERP"], [
            ["Time to start", "Fast.", "Longer, after requirement analysis."],
            ["Fit to your process", "You adapt to the product.", "The product adapts to you."],
            ["Upgrades", "Simple.", "Easy if customisation follows the platform's rules."],
            ["Cost", "Subscription.", "Subscription plus quoted customisation."],
            ["Best for", "Small and growing companies.", "Enterprises with specific workflows and reporting."],
        ])
        + "<h2>What enterprises usually ask for</h2>" + bullets(["<strong>Multi-currency:</strong> quote, invoice and keep books in more than one currency.", "<strong>Multi-language:</strong> screens in the languages your teams use.", "<strong>Workflows:</strong> approvals that match your authority levels.", "<strong>Reports and print formats:</strong> layouts your auditors and customers expect.", "<strong>Integrations:</strong> channels and systems your business already runs."])
        + "<h2>How to customise safely</h2>" + bullets(["Analyse the requirement first and write down what is standard, what is configuration and what is real customisation.", "Prefer configuration to code.", "Keep customisations in one place so upgrades stay simple.", "Test with real data before go-live."])
        + "<h2>Where ReckonERP fits</h2><p>ReckonERP is built to be easy to customise for enterprise packages: extra fields, workflows, reports, print formats and integrations are shaped to your business after a requirement analysis. It supports several currencies (plans are priced in BDT, USD, EUR or INR) and English and Bangla screens today, with more languages through translation on request. Choose the shared cloud, a dedicated cloud or an on-premises installation. Training, data migration and on-site support are available as paid services. Read the <a href=\"/faq\">FAQ</a> or <a href=\"/pricing\">pricing</a> to start.</p>"
        + faq([("Does ERP support more than one currency?", "Yes. You can quote, invoice and keep books in more than one currency, and ReckonERP plans are priced in BDT, USD, EUR or INR."), ("Which languages are supported?", "English and Bangla screens today. Other languages can be added through translation on request."), ("Will customisation make upgrades hard?", "Not if it is done within the platform's rules and kept in one place. We plan it that way after requirement analysis.")]),
    },
]


def plain_promo(post: dict, link: str) -> str:
    return (
        f"LinkedIn post:\nNew on the ReckonERP blog: {post['title']}. {post['summary']} {link}\n\n"
        f"Facebook post:\n{post['title']}. A plain comparison for business owners. {link}\n\n"
        f"Outreach pitch:\nHello, we published a neutral comparison, \"{post['title']}\", that may help your readers choose between the options. "
        f"You are welcome to read or link to it: {link}"
    )


def seed_drafts() -> list[str]:
    """Create each post as a Draft with a cover and a promotion kit, unless its slug already exists."""
    created = []
    base = marketing.site_base()
    for post in POSTS:
        if frappe.db.exists(blog.DOCTYPE, post["slug"]):
            continue
        link = f"{base}{blog.article_url(post['slug'])}"
        frappe.get_doc(
            {
                "doctype": blog.DOCTYPE,
                "slug": post["slug"],
                "title": post["title"],
                "category": "Comparison",
                "status": "Draft",
                "source": "Manual",
                "summary": post["summary"],
                "body": post["body"],
                "keywords": post["keywords"],
                "related_module": post["module"],
                "promo_kit": plain_promo(post, link),
            }
        ).insert(ignore_permissions=True)
        try:
            from reckon_saas_platform import blog_image

            cover = blog_image.attach_cover(post["slug"], post["title"], "Comparison")
            if cover:
                frappe.db.set_value(blog.DOCTYPE, post["slug"], "cover_image", cover)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Comparison post cover")
        created.append(post["slug"])
    return created
