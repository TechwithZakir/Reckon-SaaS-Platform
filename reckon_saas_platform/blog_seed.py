"""Ten long-form comparison posts, loaded as drafts and refreshed in place.

Each is written to be read by people and quoted by AI assistants: a short answer first, an introductory
story, the problem, a comparison table, a write-up of each option, a decision guide, a practical solution
path, where ReckonERP fits, a conclusion and a FAQ that becomes FAQ structured data. They compare
approaches and technology choices, not named competitors, and make no claim this platform cannot back.

``seed_drafts`` creates missing posts as drafts. ``refresh_posts`` rewrites the text, summary and cover of
the ten slugs in place (keeping their status), which is how an improved edition reaches a site that already
has them. A vendor user reads and publishes drafts in SEO Agent Studio.
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


def numbered(items: list[str]) -> str:
    return "<ol>" + "".join(f"<li>{i}</li>" for i in items) + "</ol>"


def paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{p}</p>" for p in items)


def faq(pairs: list[tuple[str, str]]) -> str:
    return "<h2>Frequently asked questions</h2>" + "".join(f"<h3>{q}</h3><p>{a}</p>" for q, a in pairs)


def build_body(post: dict) -> str:
    """The article's HTML in a fixed order, so every post reads the same way."""
    parts = [
        f"<p><strong>Short answer:</strong> {post['short']}</p>",
        f"<h2>{post['story_title']}</h2>" + paragraphs(post["story"]),
        "<h2>The problem</h2>" + paragraphs(post["problem"]) + bullets(post["symptoms"]),
        "<h2>The options side by side</h2>" + table(*post["table"]),
    ]
    parts += [f"<h2>{heading}</h2>" + paragraphs(paras) for heading, paras in post["options"]]
    parts += [
        "<h2>How to decide</h2>" + paragraphs([post["decide_intro"]]) + bullets(post["decide"]),
        "<h2>The solution: a practical path</h2>" + paragraphs([post["steps_intro"]]) + numbered(post["steps"]),
        "<h2>Where ReckonERP fits</h2>" + paragraphs(post["fits"]),
        "<h2>Conclusion</h2>" + paragraphs(post["conclusion"]),
        faq(post["faqs"]),
    ]
    return "".join(parts)


POSTS = [
    {
        "slug": "cloud-erp-vs-on-premises-erp",
        "title": "Cloud ERP vs On-Premises ERP: How to Choose",
        "summary": "A plain comparison of cloud and on-premises ERP: cost, control, upkeep and speed, and how to choose for your business.",
        "keywords": "cloud ERP, on-premises ERP, ERP deployment, ERP comparison",
        "module": "",
        "style": "cloud",
        "short": "choose cloud ERP when you want to start quickly and avoid running servers; choose on-premises when rules, connectivity or control make your own servers the safer path. Many businesses start in the cloud and move to a dedicated or on-premises setup only if they must.",
        "story_title": "A Saturday the office computer stopped",
        "story": [
            "Picture a trading company with two shops and a warehouse. The accountant keeps the books on a computer in the back office, the warehouse tracks stock on paper, and the owner asks for numbers by phone call. It works, until one Saturday the office computer's disk fails.",
            "The books are on that disk. The last backup is three weeks old. By Monday the owner has learned two things: the company depends on one machine, and nobody owns the job of keeping it safe. The question is no longer whether to buy business software, but where it should live.",
        ],
        "problem": [
            "Choosing between cloud and on-premises ERP looks like a technology question, but it is really a question about who carries the work and the risk. Someone has to keep servers running, apply updates, take backups, restore them when something breaks and keep the system secure. Either your provider does that, or you do.",
            "Getting it wrong costs money in both directions. Companies that run their own servers without the people to look after them end up with unpatched machines and untested backups. Companies that choose cloud without checking their requirements sometimes find that a contract or a poor internet link rules it out.",
        ],
        "symptoms": [
            "Backups exist, but nobody has tried to restore one.",
            "Updates are postponed because the people who could apply them are busy.",
            "Staff in the warehouse or on the road cannot reach the system.",
            "The cost of keeping old hardware alive keeps rising.",
        ],
        "table": (["Question", "Cloud ERP", "On-premises ERP"], [
            ["How fast can we start?", "Usually days, because nothing has to be installed.", "Weeks, because servers, installation and setup come first."],
            ["Who runs the servers?", "The provider.", "You or your partner."],
            ["Upfront cost", "Low; you pay a subscription.", "Higher; hardware and setup come first."],
            ["Control over data location", "Set by the provider, or by a dedicated cloud.", "Full control."],
            ["Updates and backups", "Handled for you.", "Your responsibility."],
            ["Working with a weak internet link", "Needs a steady connection.", "Works on your own network."],
        ]),
        "options": [
            ("Cloud ERP in practice", [
                "With cloud ERP the provider runs the servers, the backups and the updates, and your team signs in from a browser. You pay a subscription instead of buying hardware, and a new user can be working the same day.",
                "The trade-off is dependence on two things you do not control: the provider's care and your own internet connection. A good provider shows you how data is separated between customers and how backups work. A poor connection at a site can turn a small outage into a stopped warehouse.",
            ]),
            ("On-premises ERP in practice", [
                "On-premises ERP runs on servers you own or rent, on your network, looked after by your own people or a partner. You decide when updates happen, where data sits and who may touch the machines.",
                "That control has a price: hardware, installation, patching, monitoring, backups and the skills to do all of it. It is a good fit when a rule or contract demands local data, when the site's internet is unreliable, or when you already run servers well.",
            ]),
        ],
        "decide_intro": "Answer these five questions honestly and the choice usually becomes clear.",
        "decide": [
            "Must the data stay on a server only you control? If yes, on-premises or a dedicated server is likely.",
            "Do you have people who can run servers and backups every week? If not, cloud saves you from a risk you cannot manage.",
            "How reliable is the internet where the work happens? A weak link favours local servers.",
            "How soon do you need to be working? Days points to cloud; months can allow on-premises.",
            "Will you customise heavily? Deep customisation is easier on a dedicated or on-premises setup.",
        ],
        "steps_intro": "Most companies do best by starting small and keeping the door open.",
        "steps": [
            "Write down your hard requirements: data location rules, internet reliability, who can run servers.",
            "Start on a shared cloud with one module so you learn what you really need.",
            "Check how the provider separates customers, backs up data and lets you export it.",
            "If a requirement appears later, move to a dedicated cloud or on-premises installation with your data carried across.",
            "Review the choice once a year against cost and risk.",
        ],
        "fits": [
            "ReckonERP starts as a shared cloud service: you <a href=\"/reckonerp-signup\">sign up</a>, pick a module such as <a href=\"/modules/accounts\">Accounts</a> or <a href=\"/modules/distribution\">Distribution</a>, and work in your own private company workspace.",
            "If you later need your own server or your own premises, a dedicated cloud or on-premises installation is available on request, quoted separately. See <a href=\"/blog/shared-cloud-vs-dedicated-cloud-vs-on-premises\">Shared Cloud, Dedicated Cloud or On-Premises ERP?</a> for the three side by side, and <a href=\"/pricing\">pricing</a> for the subscription plans.",
        ],
        "conclusion": [
            "There is no universal winner. Cloud ERP wins on speed, upfront cost and freedom from server work. On-premises wins on control, local data and independence from the internet. The right choice is the one whose weaknesses you can live with.",
            "If you are unsure, start in the cloud, keep your data exportable and let real needs decide whether to move. That path keeps both options open and costs little to try.",
        ],
        "faqs": [
            ("Is cloud ERP safe for business data?", "It can be, but it depends on how the service is run. In ReckonERP every customer works in its own Company with permission rules that keep records apart, and a dedicated installation is available if you need stronger isolation."),
            ("Can we move from cloud to on-premises later?", "Yes. Your data can be exported and loaded into a dedicated or on-premises installation. Migration is a planned, quoted piece of work."),
            ("Does cloud ERP cost less over time?", "Not always. It costs less to start and to look after. Over many years the answer depends on your size, your IT staff and how much you customise."),
            ("What if our internet goes down?", "A cloud system needs a connection, so plan for a backup link at busy sites. If work cannot pause at all, an on-premises installation on your own network is safer."),
            ("How long does it take to start with cloud ERP?", "Signup and verification take minutes. The time after that depends on how much you need to configure and how much data you bring."),
        ],
    },
    {
        "slug": "spreadsheets-vs-accounting-software-vs-erp",
        "title": "Spreadsheets vs Accounting Software vs ERP",
        "summary": "Spreadsheets, accounting software or a full ERP? See what each does well, where it breaks, and when it is time to move up.",
        "keywords": "spreadsheets vs ERP, accounting software, small business ERP, inventory",
        "module": "accounts",
        "style": "spreadsheet",
        "short": "spreadsheets are fine for a one-person business with few transactions; accounting software suits a business whose main need is clean books; an ERP is worth it when stock, purchasing, sales and accounts need to agree with each other.",
        "story_title": "The sheet that knew too much",
        "story": [
            "A small wholesaler starts with one spreadsheet. It lists customers, invoices and payments, and it is wonderful: flexible, free and understood by everyone. Two years later it has eleven tabs, three colours that mean different things and one formula nobody dares touch.",
            "Then a customer disputes a balance. The owner opens the sheet and finds two versions saved by two people on the same day. Nobody can say which one is right. The sheet did not fail because spreadsheets are bad; it failed because it was asked to be accounts, stock and a customer database at once.",
        ],
        "problem": [
            "Spreadsheets are the right first tool and a risky last one. They have no built-in rules: nothing stops a duplicate invoice number, an overwritten formula or a payment typed against the wrong customer. They also do not know that selling an item should reduce stock and increase what a customer owes.",
            "The problem grows quietly. Each month the sheet gets a little more complicated and a little more important, and the cost of an error rises with it. By the time the owner notices, replacing it is harder than it would have been a year earlier.",
        ],
        "symptoms": [
            "Two people edit the same file and one change is lost.",
            "A formula is overwritten and nobody notices for months.",
            "Stock on the sheet no longer matches the shelf.",
            "The owner cannot see dues or profit without asking someone to build a report.",
        ],
        "table": (["Need", "Spreadsheets", "Accounting software", "ERP"], [
            ["Record sales and purchases", "By hand, one sheet at a time.", "Yes, with invoices and bills.", "Yes, linked to stock and orders."],
            ["Know what is in stock", "A sheet someone must keep updated.", "Basic, or not at all.", "Updated by every sale and purchase."],
            ["Books you can trust", "Depends on careful formulas.", "Double-entry books.", "Double-entry books fed by every module."],
            ["Several people at once", "Easy to overwrite each other.", "Yes, with roles.", "Yes, with roles per area."],
            ["Growth beyond accounts", "Gets slow and risky.", "Needs add-ons.", "Add modules as you grow."],
        ]),
        "options": [
            ("Where spreadsheets still make sense", [
                "If you are a sole trader with a few dozen transactions a month, a spreadsheet is cheap, fast and enough. The risk is low because one person controls it and the volume is small.",
                "The warning signs are not size alone. Watch for the second person who needs access, the first customer who asks for a statement, and the first time stock is wrong. Any of these means the sheet is carrying more than it should.",
            ]),
            ("What accounting software adds", [
                "Accounting software gives you double-entry books, invoices, bills, payments and tax-ready reports with rules that spreadsheets lack. For a business that sells a small range and holds little stock, this is often all that is needed.",
                "Its limit is everything around the books. Stock, purchasing workflows, warehouses and staff roles are usually thin or missing, so growing businesses start bolting on other tools and typing the same data twice.",
            ]),
            ("What an ERP adds", [
                "An ERP connects the work around the books: a sale reduces stock, a purchase raises a payable, a payment clears a balance, and the accounts reflect all of it without anyone re-typing. Roles control who can do what.",
                "The cost is more to set up and more to learn. That cost is worth paying when the same data is entered in more than one place or when stock and sales disagree.",
            ]),
        ],
        "decide_intro": "Use the first question that gets a yes as your signal to move up one step.",
        "decide": [
            "Does more than one person need to change the data? Move off a shared spreadsheet.",
            "Do customers or the tax office expect formal invoices and statements? Use accounting software or ERP.",
            "Do you hold stock that must match the books? Choose an ERP, or accounting software with stock.",
            "Do purchasing, warehouses or several staff roles come into it? Choose an ERP.",
        ],
        "steps_intro": "Moving up is easier when you do it in a planned order rather than in a crisis.",
        "steps": [
            "Clean the sheet: one row per customer, one per supplier, one per item, no duplicates.",
            "Decide your opening date and list balances for customers, suppliers, stock and cash as of that date.",
            "Choose the smallest tool that covers your needs today and lets you add modules later.",
            "Load opening balances, then run both systems side by side for one month and compare.",
            "Retire the sheet for transactions and keep it only as an archive.",
        ],
        "fits": [
            "The <a href=\"/modules/accounts\">Accounts module</a> gives a small business sales invoices and quotations, purchase bills and orders, stock and warehouses, cash and bank, and books in a Tally-style layout. The numbers are real double-entry records, not a summary on top of a sheet.",
            "Because each module is its own subscription, you can start with Accounts and add <a href=\"/modules/distribution\">Distribution</a> or <a href=\"/modules/hrms\">HRMS</a> later without changing systems. Data migration from spreadsheets is available as an additional service.",
        ],
        "conclusion": [
            "Spreadsheets, accounting software and ERP are not rivals so much as steps. Each is right at a certain size and a certain level of risk. The mistake is staying on a step after the work has outgrown it.",
            "If your sheet already has a second user, a stock problem or a disputed balance, you have your answer. Pick the smallest system that fixes today's problem and leaves room to grow.",
        ],
        "faqs": [
            ("Can I move my spreadsheet data into ERP?", "Yes. Data migration from spreadsheets is available as an additional service, quoted by how much data there is and how clean it is."),
            ("Is an ERP too much for a small business?", "Not if you start with one module. You pay for the module you use and add others later."),
            ("Will my accountant be able to use it?", "The Accounts module includes books and reports in a Tally-style layout that accountants know."),
            ("How long does it take to switch from spreadsheets?", "The setup is quick. Most of the time goes into cleaning data and agreeing opening balances, which is worth doing carefully."),
            ("Can I keep using spreadsheets for some things?", "Yes. Many companies keep spreadsheets for ad hoc analysis and export data from the ERP to work in them."),
        ],
    },
    {
        "slug": "fmcg-route-sales-spreadsheets-vs-distribution-erp",
        "title": "FMCG Route Sales: Spreadsheets vs a Distribution ERP",
        "summary": "Compare FMCG route sales on spreadsheets and chat with a distribution ERP: routes, dues, cash custody and stock.",
        "keywords": "FMCG distribution software, route sales, DSR, retailer dues, cash custody",
        "module": "distribution",
        "style": "route",
        "short": "spreadsheets and chat groups work for a handful of retailers; once you have several routes, sales reps and daily collections, a distribution ERP keeps routes, dues, cash and stock in one place and stops money leaking between them.",
        "story_title": "Thirty retailers, one WhatsApp group",
        "story": [
            "A distributor starts with three delivery vans and about thirty retailers. Orders arrive by phone and chat, a clerk copies them onto a sheet, the vans load in the morning and the drivers come back in the evening with cash and a handful of notes.",
            "It holds together until the evening count is short. The driver says a retailer paid; the retailer says he paid yesterday; the sheet says neither. Nobody is lying, but nobody can prove anything, and the owner spends an hour every night reconstructing the day.",
        ],
        "problem": [
            "Route sales moves money and goods through many hands in one day. Each step is a place where a number can go missing: a delivery not recorded, a collection not handed in, a retailer's balance not updated before the next visit.",
            "Spreadsheets and chat can record all of this, but they cannot enforce it. They do not warn you that a retailer is over a credit limit, that a van loaded more than it delivered, or that a rep's cash does not match his collections.",
        ],
        "symptoms": [
            "End-of-day cash counts that nobody can fully explain.",
            "Retailer balances that differ between your sheet and their notebook.",
            "Stock that disappears between the warehouse and the van.",
            "Reps who spend the evening typing instead of resting.",
        ],
        "table": (["Task", "Spreadsheets and chat", "Distribution ERP"], [
            ["Plan the day's routes", "A sheet copied to each rep.", "Routes planned per SR and DSR in one system."],
            ["Retailer dues", "A balance column someone must update.", "A running balance per retailer, updated by invoices and collections."],
            ["Cash carried by a DSR", "Counted at the end, then argued about.", "Recorded as collected and handed in, per DSR."],
            ["Goods from principals", "Mixed into your own stock sheet.", "Tracked as supplier-provided goods."],
            ["Field staff on phones", "Photos and messages.", "A mobile screen with Bangla labels."],
            ["Accounting", "Re-typed later.", "Invoices, stock and payments post to the books."],
        ]),
        "options": [
            ("Running routes on spreadsheets and chat", [
                "This approach costs nothing to start and everyone already knows how to use it. For a few vans and a stable set of retailers it can work for years, especially when the owner knows every customer personally.",
                "It strains when the number of routes grows, when reps change, or when a principal asks for proof of what was delivered. The information exists, but it is scattered across sheets, chats and memories.",
            ]),
            ("Running routes on a distribution ERP", [
                "A distribution ERP gives each SR and DSR a route, records each delivery and collection as it happens, and keeps a running balance per retailer. Cash carried by each DSR is recorded as collected and as handed in, so a shortage shows on the same day.",
                "It also handles awkward cases that sheets fumble: goods supplied by principals alongside your own stock, and invoices and payments that must reach the books without re-typing.",
            ]),
        ],
        "decide_intro": "Look at the cost of one bad week rather than the cost of software.",
        "decide": [
            "How many retailers and routes do you have today, and how many in a year?",
            "How much cash do your reps carry, and how quickly can you tell if it is short?",
            "Do you hold goods for principals who may ask for reports?",
            "Do your reps use smartphones, and would a Bangla screen help them?",
            "Does someone currently re-type field data into accounts?",
        ],
        "steps_intro": "Rolling out route software works best one route at a time.",
        "steps": [
            "List your retailers, their opening balances and your items with prices.",
            "Choose one route and one rep for a two-week pilot.",
            "Record every delivery and collection in the system and compare the evening count with the system's total.",
            "Fix the gaps you find, then add the next route.",
            "Move accounting to post from the same records so the books and the field agree.",
        ],
        "fits": [
            "The <a href=\"/modules/distribution\">Distribution module</a> covers route planning and delivery tracking, retailer dues and collections, DSR cash custody, supplier-provided goods and a Bangla-first mobile app that works in the phone's browser.",
            "It posts to your Company's books, and each company works in its own private workspace. Plans and prices are on the <a href=\"/pricing\">pricing page</a>; if your accounts need tidying too, see the <a href=\"/modules/accounts\">Accounts module</a>.",
        ],
        "conclusion": [
            "Spreadsheets and chat are a fine start for route sales. They stop being fine when money moves faster than anyone can reconcile it. A distribution ERP does not make reps honest or retailers punctual; it makes every number checkable on the day it is created.",
            "If your evenings are spent hunting for a missing amount, the cost of the problem is already higher than the cost of fixing it. Pilot one route and see what the numbers tell you.",
        ],
        "faqs": [
            ("Do my reps need to install an app?", "No. The field screens work in the phone's browser."),
            ("Can it track cash carried by each DSR?", "Yes. DSR cash custody records what each DSR collected and what was handed in."),
            ("Does it replace my accounting?", "It posts invoices, stock and payments to your Company's books, so you do not keep two sets of numbers."),
            ("Can it handle goods that belong to a principal?", "Yes. Supplier-provided goods are tracked alongside your own stock."),
            ("Is it available in Bangla?", "The field screens are designed Bangla-first, so reps can work in their own language."),
        ],
    },
    {
        "slug": "shared-cloud-vs-dedicated-cloud-vs-on-premises",
        "title": "Shared Cloud, Dedicated Cloud or On-Premises ERP?",
        "summary": "Shared cloud, dedicated cloud or on-premises? Compare cost, isolation, control and effort to pick the right ERP deployment.",
        "keywords": "dedicated cloud ERP, shared cloud ERP, on-premises ERP, ERP deployment options",
        "module": "",
        "style": "servers",
        "short": "start on a shared cloud if you want speed and a low price; move to a dedicated cloud for your own server and release schedule; choose on-premises only when your own premises are a requirement.",
        "story_title": "The audit that changed the question",
        "story": [
            "A mid-sized manufacturer has run on a shared cloud ERP for a year and is happy. Then a large customer sends a supplier questionnaire: where is your data stored, who can access the servers, and can you apply updates on a schedule we approve?",
            "The finance manager realises the honest answers are: on a provider's platform, the provider's staff, and no. Nothing is wrong with the system, but the company now needs to know whether a different kind of hosting would serve it better.",
        ],
        "problem": [
            "Most ERP discussions say cloud or on-premises, as if there were only two answers. In practice there are three, and the middle one is the most overlooked: a dedicated cloud, where the server is yours alone but someone else runs it.",
            "Choosing wrongly has a cost either way. Paying for your own servers before you need them wastes money and attention. Staying on a shared platform after a requirement demands isolation puts a contract or an audit at risk.",
        ],
        "symptoms": [
            "A customer or regulator asks where data lives and who can reach it.",
            "You need to approve updates before your users see them.",
            "You want deep customisation that a shared platform does not allow.",
            "You run reports so heavy that other tenants' performance becomes a worry.",
        ],
        "table": (["", "Shared cloud", "Dedicated cloud", "On-premises"], [
            ["Where it runs", "A provider's platform, shared by many companies.", "A server just for you, run by a provider.", "Your own servers."],
            ["Isolation", "Each company in its own workspace with permission rules.", "Your own server and database.", "Your own network."],
            ["Start-up time", "Fastest.", "Days to weeks.", "Weeks."],
            ["Customisation", "The standard modules.", "Deeper customisation is practical.", "Full customisation."],
            ["Release timing", "The provider's schedule.", "Agreed with you.", "Yours."],
            ["Who looks after backups", "The provider.", "The provider, to your needs.", "You or a partner."],
            ["Cost shape", "Subscription.", "Subscription plus setup.", "Setup plus your own running costs."],
        ]),
        "options": [
            ("Shared cloud", [
                "On a shared cloud many companies use one platform, each in its own workspace with permission rules that keep records apart. It is the quickest and lowest-cost way to start, and the provider handles servers, backups and updates.",
                "The limits are timing and depth: updates arrive on the provider's schedule, and customisation is limited to what the standard modules offer.",
            ]),
            ("Dedicated cloud", [
                "A dedicated cloud gives you your own server and database, run by a provider. You gain stronger isolation, an update schedule agreed with you and room for deeper customisation, without buying hardware or hiring server staff.",
                "It costs more than a shared plan and takes longer to set up, because the server is built for you.",
            ]),
            ("On-premises", [
                "On-premises means the software runs on servers you own, on your network, under your control. It suits organisations where data must stay on site, where the internet is unreliable, or where policy forbids external hosting.",
                "You carry the work and the risk: hardware, patching, monitoring, backups and security. Plan the people and processes before you plan the purchase.",
            ]),
        ],
        "decide_intro": "These questions separate the three options quickly.",
        "decide": [
            "Must data stay on a server only you control? That points to dedicated or on-premises.",
            "Do you need to approve updates before they reach users? Dedicated or on-premises.",
            "Will you customise beyond the standard modules? Dedicated or on-premises.",
            "Do you have people to run servers? Without them, avoid on-premises.",
            "Is speed and low cost your priority? Shared cloud.",
        ],
        "steps_intro": "A sensible path keeps your choices open as you learn.",
        "steps": [
            "Start on a shared cloud with the modules you need now.",
            "Write down any requirement that the shared platform cannot meet, with the date it appeared.",
            "When one is real, ask for a dedicated cloud quote and compare it with your growth plan.",
            "Move your data to the new server in a planned, tested migration.",
            "Choose on-premises only if your own premises are a requirement, and plan the people first.",
        ],
        "fits": [
            "All three are offered. The shared cloud is self-service: <a href=\"/reckonerp-signup\">sign up</a> and start. Dedicated cloud and on-premises installations, with customisation, are set up with you and quoted separately.",
            "See the <a href=\"/faq\">FAQ</a> for how licences, pricing and implementation work, and <a href=\"/blog/cloud-erp-vs-on-premises-erp\">Cloud ERP vs On-Premises ERP</a> for the two-way comparison.",
        ],
        "conclusion": [
            "Shared, dedicated and on-premises are three answers to one question: how much of the running and the risk do you want to own? The more you own, the more control you have and the more work you take on.",
            "For most companies the sensible start is the shared cloud, with a clear trigger for moving up. Decide the trigger now, and the move later becomes a plan instead of a scramble.",
        ],
        "faqs": [
            ("Is a dedicated cloud more secure than a shared one?", "It gives stronger isolation because the server and database are yours alone. A well-run shared cloud with strict permission rules can also be sound; the right choice depends on your requirements."),
            ("Can we change option later?", "Yes. Moving is a planned piece of work that carries your data across."),
            ("What does a dedicated cloud cost?", "It is quoted for your needs, because it depends on size, customisation and support."),
            ("Who maintains a dedicated cloud?", "The provider runs the server and its backups to the needs you agree, so you do not need your own server staff."),
            ("When is on-premises really necessary?", "When data must stay on your own premises by rule or contract, or when a poor connection makes any hosted system impractical."),
        ],
    },
    {
        "slug": "hr-payroll-spreadsheets-vs-hrms-module",
        "title": "HR and Payroll: Spreadsheets vs an HRMS Module",
        "summary": "Compare running HR and payroll on spreadsheets with an HRMS module: attendance, leave, payroll accuracy and self-service.",
        "keywords": "HRMS, payroll software, attendance and leave, small business HR",
        "module": "hrms",
        "style": "people",
        "short": "spreadsheets cope with a small team and a simple payroll; an HRMS pays for itself when attendance, leave and salary rules start to interact, because it computes payroll from the records instead of from someone's memory.",
        "story_title": "The last working day of the month",
        "story": [
            "In a company of forty, payroll week begins on the 25th. The HR officer collects attendance registers from three sites, reconciles them against a leave sheet, adjusts for the new joiner and the person who left, and builds salaries line by line.",
            "This month an employee points out that a leave day was counted as absence. Fixing it means re-checking his row, then wondering what else was missed. The payroll goes out a day late, and the HR officer spends the weekend wondering which of the other thirty-nine rows are wrong.",
        ],
        "problem": [
            "HR is not one task. It is employee records, daily attendance, shifts, leave requests and approvals, and then payroll that depends on all of them. In a spreadsheet each of these lives in a different file, and payroll is where the gaps show up as real money.",
            "The deeper problem is trust. When people cannot see how their pay or leave balance was worked out, every question becomes an investigation, and the HR officer becomes a human lookup table.",
        ],
        "symptoms": [
            "Payroll takes days and is checked line by line.",
            "Employees argue about leave balances.",
            "More than one person edits HR files.",
            "You cannot show who approved what.",
        ],
        "table": (["Task", "Spreadsheets", "HRMS module"], [
            ["Employee records", "One row per person, easy to let drift.", "A record per employee, kept in one place."],
            ["Attendance and shifts", "Typed in from registers.", "Recorded in the system."],
            ["Leave", "Requests by message, balances by hand.", "Requested and approved in the system."],
            ["Payroll", "Formulas that must be checked every month.", "Built from attendance and leave."],
            ["Employees seeing their own data", "Ask HR.", "A self-service role."],
            ["Privacy", "A file that gets forwarded.", "Roles decide who sees what."],
        ]),
        "options": [
            ("HR on spreadsheets", [
                "For a team of ten with a simple salary structure, spreadsheets are workable: a sheet of employees, a sheet of attendance, a sheet of leave. Setup costs nothing and the owner understands every cell.",
                "Trouble starts when the sheets must agree with each other. Attendance affects leave, leave affects payroll, and a change in one place has to be repeated in the others by hand. Privacy suffers too, because a file with everyone's salary gets emailed around.",
            ]),
            ("HR on an HRMS module", [
                "An HRMS keeps the connected pieces in one system: employees, attendance and shifts, leave with approvals, and payroll that reads the first three. Employees see their own records through a self-service role, so fewer questions reach HR.",
                "The benefit is not speed alone but traceability. Every leave day has an approver and every payroll line has a source.",
            ]),
        ],
        "decide_intro": "Count the places where the same fact is typed twice.",
        "decide": [
            "How many people are on payroll, and how many sites?",
            "How many hours does payroll take each month?",
            "Do employees dispute leave or attendance?",
            "Do you need to show who approved leave and payroll?",
            "Should employees see their own records without asking HR?",
        ],
        "steps_intro": "Moving HR into a system goes smoothly when the groundwork is done first.",
        "steps": [
            "Clean your employee list so every person appears once, with the right joining date.",
            "Write down working hours, shifts and the leave types with their yearly days.",
            "Decide who may approve leave and who may run payroll.",
            "Load employees, set up attendance and leave, and run payroll in parallel with your sheet for one month.",
            "Compare the two, fix the differences and then retire the sheet.",
        ],
        "fits": [
            "The <a href=\"/modules/hrms\">HRMS module</a> is compact HR and payroll for small businesses: employees, attendance and shifts, leave, and payroll, in a private workspace per company. Roles include HR manager, payroll manager, talent admin and employee self-service.",
            "If your accounts also need to be tidy, pair it with <a href=\"/modules/accounts\">Accounts</a>. See <a href=\"/pricing\">pricing</a> for plans and trial days.",
        ],
        "conclusion": [
            "Spreadsheets are a reasonable way to start HR and an unreliable way to carry it once attendance, leave and payroll depend on each other. An HRMS does not remove judgement from HR; it removes the arithmetic and the guessing.",
            "If payroll week is the week everyone dreads, the sheet has done its job and it is time to hand the counting to a system.",
        ],
        "faqs": [
            ("Can employees see their own leave and records?", "Yes. The employee self-service role lets each person see their own records, subject to what the company allows."),
            ("Is payroll based on attendance?", "Payroll is built from the attendance and leave you record in the module."),
            ("Does the HRMS file tax returns for us?", "No. Statutory filings and tax returns are outside the module."),
            ("Can several managers use it at once?", "Yes. Roles such as HR manager and payroll manager let different people work in their own areas."),
            ("How do I move from spreadsheets?", "Clean your employee list, load it, set up leave types and attendance, and run one month in parallel. Data migration help is available as an additional service."),
        ],
    },
    {
        "slug": "standalone-crm-vs-erp-integrated-crm",
        "title": "Standalone CRM vs an ERP-Integrated CRM",
        "summary": "Standalone CRM or CRM built into your ERP? Compare data, reporting, cost and effort to decide what suits your sales team.",
        "keywords": "CRM vs ERP, integrated CRM, sales pipeline, leads and deals",
        "module": "crm",
        "style": "crm",
        "short": "a standalone CRM is quick to adopt and strong for sales workflows; a CRM that shares data with your ERP gives one customer record across quotes, invoices and payments. Choose by whether your sales team's biggest pain is following up or knowing what the customer owes.",
        "story_title": "The deal that shipped to a customer who owed us",
        "story": [
            "A sales rep spends three weeks closing a good order. The CRM shows the deal as won, and the warehouse ships. Two days later accounts calls: the customer has two overdue invoices from last year, and the credit controller would have stopped the order if anyone had asked.",
            "Nobody did anything wrong. The CRM did not know about invoices, accounts did not know about the deal, and the customer record in each system was a stranger to the other.",
        ],
        "problem": [
            "Sales and accounts look at the same customer through different windows. When those windows are separate systems, each team sees half the story: sales sees interest and promises, accounts sees invoices and payments.",
            "Joining the two can be done with integrations, but integrations need someone to build and maintain them, and they break quietly. The question is whether the connection should be an extra project or part of the foundation.",
        ],
        "symptoms": [
            "The same customer is typed into two systems.",
            "Sales promises deliveries to accounts that are overdue.",
            "Quotes are re-keyed as invoices.",
            "Nobody can report sales, collections and pipeline in one view.",
        ],
        "table": (["Question", "Standalone CRM", "ERP-integrated CRM"], [
            ["Adoption", "Quick; sales teams can start alone.", "Needs the ERP in place, or set up together."],
            ["Customer record", "One for sales, another in accounts.", "One shared record."],
            ["Quote to invoice", "Re-entered or connected by an integration.", "Flows into invoicing."],
            ["What the customer owes", "Not visible to sales.", "Visible alongside the deal."],
            ["Cost and upkeep", "Another system and its connectors.", "One system."],
            ["Flexibility", "Often rich sales-specific features.", "Focused on core sales records."],
        ]),
        "options": [
            ("The case for a standalone CRM", [
                "A standalone CRM is fast to adopt because sales can start without waiting for anyone else. It tends to offer rich sales features such as sequences, forecasts and many integrations with email and calendars.",
                "The cost appears later, when customers, quotes and payments need to line up with the accounts. You either re-type, or you build and maintain connectors.",
            ]),
            ("The case for an integrated CRM", [
                "An ERP-integrated CRM shares one customer record with quotes, invoices and payments. Sales sees what a customer owes before a new deal; accounts sees which deals are coming. There is one login, one set of roles and one place to look.",
                "It may offer fewer niche sales features than a specialist product, so it suits teams that need solid core records more than advanced automation.",
            ]),
        ],
        "decide_intro": "Ask which of these hurts more today.",
        "decide": [
            "Does sales need to see unpaid invoices before a new deal?",
            "How many times is the same customer typed in today?",
            "Who will keep integrations working when something changes?",
            "Do you want one login and one set of roles?",
            "Does your team need advanced sales automation, or solid records?",
        ],
        "steps_intro": "You can connect sales and accounts step by step.",
        "steps": [
            "List your active customers once, with the right company name and contact.",
            "Move leads and open deals into the CRM and agree the pipeline stages.",
            "Connect quotes and invoices so a won deal flows into billing.",
            "Show dues next to each deal so sales sees them before promising delivery.",
            "Review the pipeline weekly with the numbers from one place.",
        ],
        "fits": [
            "The <a href=\"/modules/crm\">CRM module</a> gives sales teams leads, deals and organizations in a private workspace, with admin and user roles. It works with the <a href=\"/modules/sales_agent\">Sales AI Agent</a>, which finds and qualifies leads and syncs them in, so your team follows up instead of searching.",
            "Because it belongs to the same platform as <a href=\"/modules/accounts\">Accounts</a>, you can subscribe to both from one account, each with its own plan.",
        ],
        "conclusion": [
            "A standalone CRM is the quick choice and an integrated CRM is the connected one. Neither is wrong; the right one depends on whether your sales team's costliest mistake is missing a follow-up or ignoring what a customer owes.",
            "If your problem is the second, joining the records is worth more than any extra sales feature.",
        ],
        "faqs": [
            ("Can I use the CRM without the ERP?", "Yes. Each module is its own subscription, so you can start with the CRM alone."),
            ("Does the Sales AI Agent message leads on its own?", "No. Drafts wait for a person's approval before any message is sent."),
            ("Is my CRM data separate from other companies?", "Yes. Every company works in its own private workspace."),
            ("Can I add accounts later?", "Yes. Subscribe to Accounts from your Subscription page and the two work from the same company."),
            ("What does a CRM module need from me?", "A clean customer list and an agreed pipeline. Both can be set up in a day."),
        ],
    },
    {
        "slug": "open-source-vs-proprietary-vs-custom-built-erp",
        "title": "Open-Source, Proprietary or Custom-Built ERP?",
        "summary": "Compare open-source, proprietary and custom-built ERP stacks on cost, flexibility, risk and long-term ownership.",
        "keywords": "open-source ERP, proprietary ERP, custom ERP, ERP technology stack",
        "module": "",
        "style": "stack",
        "short": "open-source ERP usually gives a good balance of flexibility and cost if you have a partner who knows it; proprietary suites suit buyers who want a single vendor to hold accountable; a custom build suits only needs no product can meet, and it carries the most risk.",
        "story_title": "Three quotes on one desk",
        "story": [
            "A growing manufacturer asks for ERP quotes and gets three very different answers. One vendor offers a proprietary suite with a per-user licence. A consultant proposes an open-source platform with a one-time setup fee. A software house says it can build exactly what the company wants in nine months.",
            "The prices are not comparable, the promises are not comparable, and the owner suspects the real costs are hiding in places the quotes do not mention. He is right, and the way to compare them is to look at ownership, not just price.",
        ],
        "problem": [
            "ERP is a decade-long decision disguised as a purchase. The stack you pick determines who can change the software, who can leave, what happens when the vendor changes its pricing and how easily you can add the next module.",
            "Price tags hide most of that. A licence fee tells you nothing about the cost of customising, the cost of switching or the cost of depending on one person who wrote the code.",
        ],
        "symptoms": [
            "Quotes that cannot be compared line by line.",
            "Fear of being locked in to one vendor or one developer.",
            "A need for features that no product seems to offer.",
            "Uncertainty about who will maintain the system in five years.",
        ],
        "table": (["", "Open-source ERP", "Proprietary ERP", "Custom-built ERP"], [
            ["Licence cost", "No licence fee for the software itself.", "Licence or subscription per user or module.", "None, but you pay to build it."],
            ["Flexibility", "High; the code can be extended.", "Limited to what the vendor allows.", "Total."],
            ["Time to first use", "Short.", "Short to medium.", "Long."],
            ["Who maintains it", "The community and your partner.", "The vendor.", "You."],
            ["Lock-in", "Low; you can change partners.", "High.", "High, to whoever built it."],
            ["Main risk", "Needs a capable partner.", "Cost and rigidity.", "Cost, delay and key-person risk."],
        ]),
        "options": [
            ("Open-source ERP", [
                "Open-source ERP has no licence fee for the software, an active community and code you can extend. You can change implementation partners without losing the system, and you can export your data.",
                "The catch is that free software still needs skilled people. Without a partner who knows the platform well, customisation can become messy and upgrades painful.",
            ]),
            ("Proprietary ERP", [
                "A proprietary suite gives you one vendor to call, a defined product and often a large partner network. It suits buyers who want accountability and a standard process more than flexibility.",
                "You pay licence fees that grow with users and modules, you change only what the vendor permits, and leaving later can be expensive.",
            ]),
            ("Custom-built ERP", [
                "A custom build can match your process exactly. It makes sense when your way of working is genuinely unlike what any product supports and the advantage is worth the cost.",
                "It is the slowest and riskiest route: it takes months, depends on the people who wrote it, and you inherit every bug and every missing feature, including accounting rules a mature product already handles.",
            ]),
        ],
        "decide_intro": "Check these before you compare prices.",
        "decide": [
            "Is double-entry accounting a real part of it, not an add-on?",
            "Can you customise without breaking upgrades?",
            "Is there an API and a way to export your data?",
            "How do roles and permissions work, and can they separate companies?",
            "Who will maintain it in five years, and what happens if they leave?",
        ],
        "steps_intro": "A careful buyer can narrow the choice in a few weeks.",
        "steps": [
            "List the processes that make your business different and rank how much each matters.",
            "Ask each option to show those processes in a demo with your data, not theirs.",
            "Price five years, including customisation, upgrades and exit.",
            "Check how each option exports data and what leaving would take.",
            "Start with one module on the option that fits and expand once it proves itself.",
        ],
        "fits": [
            "ReckonERP is built on open-source ERP technology and adds what most companies end up needing: separate company workspaces, modules you subscribe to one at a time, Bangla and English screens, and an AI assistant that works inside your own permissions.",
            "You get a managed service without being tied to a closed product, and customisation for enterprise packages is quoted separately. See the <a href=\"/features/modular-erp\">modular ERP</a> page for how modules fit together, and <a href=\"/pricing\">pricing</a> for plans.",
        ],
        "conclusion": [
            "Open-source, proprietary and custom-built ERP trade cost against control in different ways. Open-source offers flexibility and exit; proprietary offers accountability at the price of rigidity; custom offers fit at the price of risk.",
            "For most growing businesses an open stack with a capable partner is the balanced choice. Whatever you pick, insist on data you can export and a plan for who maintains it.",
        ],
        "faqs": [
            ("Is open-source ERP less secure?", "Not by nature. Security comes from how the system is configured, run and updated. Open code can be reviewed by many people."),
            ("Can I leave if I am not happy?", "Yes. You can export your data, which is one of the benefits of an open stack."),
            ("When is a custom build justified?", "When your process is unlike anything a product supports and the cost of adapting is higher than the cost of building. That is rare."),
            ("Does open-source mean no support?", "No. Support comes from your service provider or partner, who should agree what they cover."),
            ("How does ReckonERP fit?", "It is a managed service built on open-source ERP technology, with modules, workspaces and AI added on top."),
        ],
    },
    {
        "slug": "rules-vs-machine-learning-vs-llm-assistants-in-erp",
        "title": "Rules, Machine Learning or LLMs: AI Options in ERP",
        "summary": "Compare rule-based automation, machine learning and LLM assistants inside an ERP: what each does well and where it needs a person.",
        "keywords": "AI in ERP, LLM assistant, machine learning, rule-based automation, AI technology stack",
        "module": "sales_agent",
        "style": "ai",
        "short": "use rules where the answer must be exactly the same every time, machine learning where you have lots of history and a clear number to predict, and an LLM assistant where people need to ask questions or draft text. In an ERP the safest design mixes all three and keeps a person approving changes.",
        "story_title": "The finance director's three questions",
        "story": [
            "A finance director hears the same pitch from three vendors in one week: AI that scores your leads, AI that forecasts your cash, and AI that answers questions about your accounts in plain English. All three are called AI. Only one will help with Monday's real problem.",
            "She asks each vendor the same questions: how does it decide, what happens when it is wrong, and can it change my data on its own? The answers reveal three quite different technologies, and the right use for each.",
        ],
        "problem": [
            "AI in ERP is a label covering very different techniques. Rules follow logic you write. Machine learning finds patterns in past data. Large language models read and write text. Each is good at one job and poor at others, and mixing them up leads to disappointment or risk.",
            "The risk is not only that AI is wrong, but that it is wrong confidently, in a system where numbers feed decisions, payments and tax. A good design decides in advance where AI may speak and where only a person may act.",
        ],
        "symptoms": [
            "Vendors call everything AI, so comparisons are impossible.",
            "A model gives a score nobody can explain.",
            "An assistant sounds sure about something the records do not say.",
            "Staff fear that AI will change data without anyone noticing.",
        ],
        "table": (["", "Rules", "Machine learning", "LLM assistants"], [
            ["Good at", "Fixed logic such as scoring or validation.", "Forecasts and anomalies from past data.", "Language: answering questions, summarising, drafting."],
            ["Explainable", "Completely.", "Partly.", "Hard to prove why a sentence was written."],
            ["Needs", "Someone to write the rules.", "Clean history and monitoring.", "Good context and guardrails."],
            ["Can be wrong", "Only if the rule is.", "Yes, on new patterns.", "Yes, and sounds confident."],
            ["Typical use in ERP", "Lead scoring, approvals, checks.", "Demand and cash forecasts, odd transactions.", "Asking your records questions, first drafts."],
        ]),
        "options": [
            ("Rules: exact and explainable", [
                "Rules are plain logic: if the order exceeds the credit limit, hold it; if a lead has a website and a phone number, give it these points. They are predictable, auditable and cheap to run, and anyone can read why a result happened.",
                "They do not learn. When the business changes, someone must change the rules, which is usually what you want for anything that must be exactly the same every time.",
            ]),
            ("Machine learning: patterns in history", [
                "Machine learning learns from past data to predict a number or flag something unusual, such as next month's demand or a payment that looks out of pattern. It shines when you have a lot of clean history and a clear thing to predict.",
                "It is harder to explain and it can fail quietly when conditions change, so it needs monitoring and a person who understands its limits.",
            ]),
            ("LLM assistants: language and questions", [
                "A large language model reads and writes text. In an ERP it can answer a question about your records, summarise a customer's history or draft a reply. It saves time on work that is mostly reading and writing.",
                "It can also state something untrue in a confident voice, so it should read only what the user may see, cite where facts came from and never change data without approval.",
            ]),
        ],
        "decide_intro": "Match the technique to the job, not the job to the technique.",
        "decide": [
            "Must the answer be identical every time? Use rules.",
            "Do you have a year or more of clean history and a number to predict? Consider machine learning.",
            "Is the job reading or writing text? Use an LLM assistant with guardrails.",
            "Would a wrong answer cost money? Add a preview and a person's approval.",
            "Do you need to explain the result to an auditor? Prefer rules.",
        ],
        "steps_intro": "A safe rollout adds capability in the order of risk.",
        "steps": [
            "Start with rules for checks and scores you can read and explain.",
            "Add an assistant for questions and first drafts, limited to what each user may see.",
            "Require a preview and a person's approval before anything changes data, and log every action.",
            "Collect clean history, then add forecasting where a clear number is worth predicting.",
            "Review results monthly and retire anything that is not earning its place.",
        ],
        "fits": [
            "The <a href=\"/features/reckon-ai-assistant\">Reckon AI assistant</a> works inside the permissions of the person asking, and changes are applied only after you review and approve them.",
            "The <a href=\"/modules/sales_agent\">Sales AI Agent</a> scores leads with fixed rules you can read, uses AI for research and drafts, and waits for a person to approve any message. AI and integration usage is billed separately. See <a href=\"/features/ai-assisted-selling\">AI-assisted selling</a>.",
        ],
        "conclusion": [
            "Rules, machine learning and language models are three tools, not three versions of the same tool. A sound ERP uses rules for what must be exact, learning for what can be predicted and language models for what is read and written, with a person approving changes.",
            "Ask every AI vendor how it decides, what happens when it is wrong and whether it may change your data alone. The answers tell you more than the demo.",
        ],
        "faqs": [
            ("Should an AI change my data on its own?", "Not without approval. Show a preview, let a person approve, and keep a log."),
            ("Do I need machine learning to start?", "No. Start with rules and an assistant for questions and drafts. Add forecasting when you have enough clean history."),
            ("Why score leads with rules?", "Because you can read and explain the result, and it does not change unexpectedly."),
            ("Can an assistant see all my records?", "It should only see what the signed-in user may see. In ReckonERP it works inside that person's permissions."),
            ("Who pays for AI usage?", "AI and integration usage is billed separately from the module subscription."),
        ],
    },
    {
        "slug": "hosted-ai-vs-self-hosted-ai-models-for-erp-data",
        "title": "Hosted AI vs Self-Hosted AI Models for ERP Data",
        "summary": "Hosted AI or self-hosted AI models for ERP data? Compare privacy, quality, cost and effort, and what to ask before you choose.",
        "keywords": "AI privacy, self-hosted AI, hosted AI API, ERP AI, AI technology stack",
        "module": "",
        "style": "privacy",
        "short": "hosted AI services give stronger models with almost no setup, while self-hosted models keep prompts on your own servers at the cost of effort and usually of quality. Pick by how sensitive the data is and how much quality you need, and send only the records a task actually needs.",
        "story_title": "The question from the security officer",
        "story": [
            "A company turns on an AI assistant in its ERP and staff love it. A week later the security officer asks a simple question: when someone asks the assistant about a customer, where does that customer's data go?",
            "Nobody has an answer. The data goes to an AI provider's servers, under that provider's terms, for as long as those terms allow. The assistant is still useful, but now the company needs to decide, deliberately, which information may travel and which must not.",
        ],
        "problem": [
            "AI in business software almost always means sending text to a model. The model may run at a provider you do not control, or on a server you do. That one fact decides your privacy position, your costs and the quality you get.",
            "The mistake is treating it as an all-or-nothing choice. Different tasks carry different sensitivity: drafting a public-facing email is not the same as summarising a payroll run.",
        ],
        "symptoms": [
            "Nobody can say what data an assistant sends out.",
            "A provider's data terms are unread or unclear.",
            "Usage costs grow with no cap.",
            "A rule or customer contract limits where data may go.",
        ],
        "table": (["", "Hosted AI service", "Self-hosted model"], [
            ["Setup", "An account and a key.", "Servers, a model and upkeep."],
            ["Quality", "Typically strongest.", "Depends on the model and hardware."],
            ["Where prompts go", "To the provider.", "Stay on your servers."],
            ["Cost shape", "Pay for what you use.", "Hardware and people, then little per request."],
            ["Speed and scale", "Provider's capacity.", "Your capacity."],
            ["Good fit", "Drafting, research, general questions.", "Sensitive data or strict data rules."],
        ]),
        "options": [
            ("Hosted AI services", [
                "A hosted service needs only an account and a key, and gives you some of the strongest models without any hardware. You pay for what you use and scale without planning.",
                "Your prompts travel to the provider, so you must read its terms on storage and training, send only what a task needs and cap spending so a busy month cannot surprise you.",
            ]),
            ("Self-hosted models", [
                "A self-hosted model runs on your own server. Prompts never leave your network, which answers the privacy question completely and satisfies strict data rules.",
                "In return you take on hardware, setup and upkeep, and open models that fit a modest server are usually weaker than the strongest hosted ones. Good for focused tasks, less so for demanding ones.",
            ]),
        ],
        "decide_intro": "Sort your AI tasks by the sensitivity of their data first.",
        "decide": [
            "What data would the model see, and could less be enough?",
            "Does the provider keep prompts, and for how long?",
            "Who pays for usage and how is it capped?",
            "Can you switch provider without rebuilding?",
            "Do you have the skills to run a model server?",
        ],
        "steps_intro": "Most companies end up using both, for different jobs.",
        "steps": [
            "List the tasks you want AI for and mark each as low, medium or high sensitivity.",
            "Use a hosted service for low-sensitivity tasks such as drafting and public research.",
            "For high-sensitivity tasks, use a self-hosted model or design the task so those fields are never sent.",
            "Respect each user's permissions before any record reaches a model, and cap monthly usage.",
            "Keep keys in a protected settings store, review the provider's terms yearly, and test switching providers once.",
        ],
        "fits": [
            "The AI features can use a hosted provider or an OpenAI-compatible server, including one you run yourself. Each business can keep its own keys, and a monthly call limit caps usage.",
            "Usage is billed separately from the module subscription. For dedicated or on-premises installations, ask us about keeping AI on your own servers. See <a href=\"/integrations\">integrations</a> for the services that connect.",
        ],
        "conclusion": [
            "Hosted and self-hosted AI answer different needs. Hosted gives quality and simplicity; self-hosted gives privacy and control. The sensible answer for most businesses is to use each where it fits and to send a model only what a task requires.",
            "Decide the rules before the first prompt: what may leave, who may ask, and what it may cost. That is far easier than undoing a habit later.",
        ],
        "faqs": [
            ("Can I use my own AI server?", "Yes, where the operator allows it, an OpenAI-compatible server address can be used."),
            ("Does AI see all my records?", "No. It works inside the permissions of the person using it and only receives what a task needs."),
            ("Who pays for AI usage?", "AI and integration usage is billed separately from your module subscription."),
            ("Is self-hosted AI always more private?", "It keeps prompts on your servers, which is stronger on privacy, but you are then responsible for securing that server."),
            ("Can I switch AI providers later?", "Yes. Use an OpenAI-compatible interface and keep prompts independent of one provider."),
        ],
    },
    {
        "slug": "standard-vs-customised-erp-for-enterprises",
        "title": "Standard vs Customised ERP: What Enterprises Need",
        "summary": "Compare standard and customised ERP for enterprises: multi-currency, multi-language, workflows, cost and how to customise safely.",
        "keywords": "customised ERP, enterprise ERP, multi-currency ERP, multi-language ERP, ERP customization",
        "module": "",
        "style": "globe",
        "short": "start with the standard modules and customise only where your process truly differs. Enterprises usually need more than defaults, such as several currencies, several languages and their own workflows, so plan customisation as a managed project with analysis first, not as a pile of one-off changes.",
        "story_title": "Four offices, three currencies, two languages",
        "story": [
            "A regional group has offices in four cities. Sales are invoiced in dollars and euros, the books are kept in the local currency, and half the staff work in Bangla while the other half work in English. Approvals need two signatures above a set amount and three above another.",
            "The standard ERP covers eighty per cent of this on day one. The remaining twenty per cent is what the group's finance team talks about every week, because it is exactly where their business differs from everyone else's.",
        ],
        "problem": [
            "Enterprises rarely need an ERP that is dramatically different from the standard one. They need the standard core plus a handful of carefully chosen differences: currencies, languages, approval chains, reports and print formats that auditors and customers expect.",
            "The danger lies in how the differences are made. One-off changes written under pressure pile up, make upgrades risky and leave nobody who understands why a rule exists.",
        ],
        "symptoms": [
            "Staff keep side spreadsheets for what the system cannot do.",
            "Approvals happen by email instead of in the system.",
            "Reports must be rebuilt by hand for each audit.",
            "A past change makes every upgrade nervous.",
        ],
        "table": (["", "Standard ERP", "Customised ERP"], [
            ["Time to start", "Fast.", "Longer, after requirement analysis."],
            ["Fit to your process", "You adapt to the product.", "The product adapts to you."],
            ["Upgrades", "Simple.", "Easy if customisation follows the platform's rules."],
            ["Cost", "Subscription.", "Subscription plus quoted customisation."],
            ["Suits", "Small and growing companies.", "Enterprises with specific workflows and reporting."],
        ]),
        "options": [
            ("What the standard modules already give you", [
                "A standard ERP gives you proven accounting, stock, sales and purchasing, with roles and permissions, ready to use. Starting here keeps cost low and teaches you what your real differences are.",
                "For many enterprises the standard modules, configured carefully, cover most needs without any custom code. Configuration, such as settings, fields and approval rules, is cheaper and safer than customisation.",
            ]),
            ("What enterprises usually ask for", [
                "<strong>Multi-currency:</strong> quote, invoice and keep books in more than one currency. <strong>Multi-language:</strong> screens in the languages your teams use. <strong>Workflows:</strong> approvals that match your authority levels. <strong>Reports and print formats:</strong> layouts your auditors and customers expect. <strong>Integrations:</strong> the channels and systems your business already runs.",
                "These are normal enterprise requirements, not exotic ones, and a platform built for them handles most through configuration and a modest amount of customisation.",
            ]),
            ("How to customise without regret", [
                "Analyse the requirement first and write down what is standard, what is configuration and what is real customisation. Prefer configuration to code, keep every customisation in one place, and test with real data before go-live.",
                "Done this way, upgrades stay simple, because the changes follow the platform's own rules instead of fighting them.",
            ]),
        ],
        "decide_intro": "Ask these before you commission any change.",
        "decide": [
            "Is this a real difference in how we work, or a habit we could change?",
            "Can configuration meet it, or is code truly needed?",
            "Who will own and document the change?",
            "Will it survive the next upgrade?",
            "What does it cost to run it for five years, not just to build it?",
        ],
        "steps_intro": "A managed customisation project keeps the work small and the risk low.",
        "steps": [
            "Run a requirement analysis and sort every need into standard, configuration or customisation.",
            "Go live on the standard modules first, with currencies and languages configured.",
            "Customise the most valuable differences one at a time, each with an owner and a test.",
            "Keep all customisations in one documented place so upgrades stay simple.",
            "Review the list every six months and retire anything no longer used.",
        ],
        "fits": [
            "ReckonERP is built to be easy to customise for enterprise packages: extra fields, workflows, reports, print formats and integrations are shaped to your business after a requirement analysis.",
            "It supports several currencies (plans are priced in BDT, USD, EUR or INR) and English and Bangla screens today, with more languages through translation on request. Choose the shared cloud, a dedicated cloud or an on-premises installation. Training, data migration and on-site support are available as paid services. Read the <a href=\"/faq\">FAQ</a> or <a href=\"/pricing\">pricing</a> to start.",
        ],
        "conclusion": [
            "Standard and customised ERP are not opposites. The sound path is standard first, configuration second and customisation last, each justified by a real difference in how your business works.",
            "Enterprises that follow it get a system that fits and still upgrades cleanly. Those that skip the analysis get a collection of exceptions. Plan the project, own the changes and the result will outlast the first go-live.",
        ],
        "faqs": [
            ("Does ERP support more than one currency?", "Yes. You can quote, invoice and keep books in more than one currency, and ReckonERP plans are priced in BDT, USD, EUR or INR."),
            ("Which languages are supported?", "English and Bangla screens today. Other languages can be added through translation on request."),
            ("Will customisation make upgrades hard?", "Not if it is done within the platform's rules and kept in one place. We plan it that way after requirement analysis."),
            ("Who does the customisation?", "We do, after a requirement analysis, quoted separately from your subscription."),
            ("Can we try the standard modules first?", "Yes. Most enterprises start on the standard modules and add customisation where the real gaps appear."),
        ],
    },
]

for _post in POSTS:
    _post["body"] = build_body(_post)


def plain_promo(post: dict, link: str) -> str:
    return (
        f"LinkedIn post:\nNew on the ReckonERP blog: {post['title']}. {post['summary']} {link}\n\n"
        f"Facebook post:\n{post['title']}. A plain comparison for business owners. {link}\n\n"
        f"Outreach pitch:\nHello, we published a neutral comparison, \"{post['title']}\", that may help your readers choose between the options. "
        f"You are welcome to read or link to it: {link}"
    )


def _cover(post: dict) -> None:
    try:
        from reckon_saas_platform import blog_image

        cover = blog_image.attach_cover(post["slug"], post["title"], "Comparison", post["style"])
        if cover:
            frappe.db.set_value(blog.DOCTYPE, post["slug"], {"cover_image": cover, "cover_style": post["style"]})
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Comparison post cover")


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
                "cover_style": post["style"],
                "promo_kit": plain_promo(post, link),
            }
        ).insert(ignore_permissions=True)
        _cover(post)
        created.append(post["slug"])
    return created


def refresh_posts() -> list[str]:
    """Rewrite the ten posts in place with the current edition, keeping their status and publish date."""
    refreshed = []
    for post in POSTS:
        if not frappe.db.exists(blog.DOCTYPE, post["slug"]):
            continue
        doc = frappe.get_doc(blog.DOCTYPE, post["slug"])
        doc.title = post["title"]
        doc.summary = post["summary"]
        doc.keywords = post["keywords"]
        doc.related_module = post["module"]
        doc.cover_style = post["style"]
        doc.body = post["body"]
        doc.save(ignore_permissions=True)
        _cover(post)
        refreshed.append(post["slug"])
    return refreshed
