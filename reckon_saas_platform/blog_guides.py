"""Nine buyer-guide and AI-automation posts, loaded as drafts and refreshed in place.

They follow the same long-form structure as the comparison posts (see ``blog_seed``): short answer, story,
problem, side-by-side table, options, how to decide, a practical path, where ReckonERP fits, a conclusion and
a FAQ. They name no competitor, quote no price or statistic we cannot back, and are created as Drafts: a
vendor user reads and publishes them in SEO Agent Studio.
"""

from __future__ import annotations

import frappe

from reckon_saas_platform import blog, marketing
from reckon_saas_platform.blog_seed import build_body, plain_promo

GUIDES = [
    {
        "slug": "erp-software-in-bangladesh-buyers-guide",
        "title": "ERP Software in Bangladesh: A Buyer's Guide",
        "summary": "A plain buyer's guide to ERP software in Bangladesh: what to ask, what it costs you in effort, and how to compare options fairly.",
        "keywords": "ERP software Bangladesh, ERP buyer's guide, cloud ERP Bangladesh, ERP selection",
        "module": "",
        "category": "Article",
        "style": "stack",
        "short": "list your processes first, shortlist two or three options, test each with your own data, and judge them on fit, support and exit, not on feature lists. Start with the modules you need now and keep the rest for later.",
        "story_title": "The shortlist that grew to nine",
        "story": [
            "A distributor in Dhaka decides it is time for proper business software. A friend recommends one product, a consultant recommends another, and a salesman leaves a brochure for a third. By the end of the week the shortlist has nine names and nobody can say how they differ.",
            "The owner is not short of information. He is short of a way to compare it. Every vendor says it covers accounts, stock, sales and HR, and every demo looks smooth. What he needs is a short list of questions that separates the options that fit his business from the ones that only look good.",
        ],
        "problem": [
            "Buying an ERP is unlike buying a tool. You will live in it every day, put your finances and your customers into it, and be reluctant to leave once it holds years of records. A poor choice does not fail loudly; it wastes a little time every day until the cost is large.",
            "Most buyers compare feature lists, but features are the least useful measure. Almost every product has the features. What differs is how well it fits your way of working, who helps you when something breaks, how much of it you will actually use and what leaving would cost.",
        ],
        "symptoms": [
            "Demos that cover what the vendor wants to show, not what you do.",
            "Quotes that cannot be compared because they include different things.",
            "A feature list that nobody on your team has checked against real work.",
            "No answer to the question: what if we want to leave?",
        ],
        "table": (["Question to ask", "Why it matters", "A good sign"], [
            ["Can you show my process with my data?", "Demos hide gaps that real data exposes.", "They load a sample of your records and run it."],
            ["How is my data kept separate?", "Your records must not mix with other companies'.", "Each company has its own workspace and permission rules."],
            ["Can I export everything?", "It decides how locked in you are.", "A clear export of all your records at any time."],
            ["Who supports me, and in what language?", "Problems arrive at awkward hours.", "Support in Bangla and English, with a named channel."],
            ["What is not included in the price?", "Training, migration and customisation add up.", "A written list of what is quoted separately."],
            ["Can I start with one module?", "Paying for everything on day one wastes money.", "Modules you add and pay for one at a time."],
        ]),
        "options": [
            ("Start from your processes, not from products", [
                "Write down what happens in your business in a normal week: how an order arrives, how stock moves, how a customer pays, how staff are paid. Mark the three steps that hurt most. A product that fixes those three is worth more than one that has a hundred extra features.",
                "This list also keeps vendors honest. When a demo drifts, you can bring it back to your own steps and ask them to show exactly that.",
            ]),
            ("Compare on fit, support and exit", [
                "Fit is how little you must bend your business to the software. Support is how quickly a real person helps, in your language. Exit is whether you can take your data and leave. A product strong on all three is safer than one that is strong on features alone.",
                "Ask each vendor for the same three things in writing: what is included, what is quoted separately and how you export your records. Differences show up at once.",
            ]),
            ("Test with your own data before you commit", [
                "Load a small sample of your real customers, items and opening balances and run a week of normal work. Problems that a demo never shows, such as awkward item names, unusual taxes or messy balances, appear within a day.",
                "A cloud product with a free trial is ideal for this, because you can test without installing anything or signing a long contract.",
            ]),
        ],
        "decide_intro": "A simple scoring habit keeps the choice honest.",
        "decide": [
            "Score each option from one to five on fit, support, exit and cost, using the same questions.",
            "Weight fit and exit above price; a cheap system you must leave is expensive.",
            "Ask a current user of each option, not only the vendor's reference.",
            "Check how each handles Bangla screens, local SMS and your reporting needs.",
            "Prefer the option that lets you start small and add modules later.",
        ],
        "steps_intro": "A practical path from first search to first week of use.",
        "steps": [
            "Write your three most painful processes and the numbers you wish you could see.",
            "Shortlist two or three options and send each the same list of questions.",
            "Run a trial with your own sample data for a week, with the people who will use it.",
            "Agree in writing what is included, what is extra and how data export works.",
            "Go live with one module, then add others once the first is running smoothly.",
        ],
        "fits": [
            "ReckonERP is a cloud ERP you can try online: <a href=\"/reckonerp-signup\">sign up</a>, pick a module and a plan, and test with your own data. Each company works in its own private workspace, screens are in English and Bangla, and plans are priced in BDT, USD, EUR or INR.",
            "Modules are bought one at a time, from <a href=\"/modules/accounts\">Accounts</a> to <a href=\"/modules/distribution\">Distribution</a>, <a href=\"/modules/hrms\">HRMS</a> and <a href=\"/modules/crm\">CRM</a>. Implementation, training and customisation are quoted separately; see <a href=\"/pricing\">pricing</a> and the <a href=\"/faq\">FAQ</a>, and <a href=\"/industries\">industry pages</a> for your sector.",
        ],
        "conclusion": [
            "A good ERP choice is made by asking better questions, not by collecting more brochures. Start from your processes, compare on fit, support and exit, and test with your own data.",
            "Do that and the shortlist of nine becomes a choice of two, then of one, with reasons you can explain to your team and to yourself a year later.",
        ],
        "faqs": [
            ("How long does choosing an ERP take?", "A focused search takes a few weeks: a week to write your processes, a week or two to shortlist and test, and a few days to agree terms."),
            ("Should I pick the lowest-priced option?", "Not on price alone. Compare fit, support and the cost of leaving as well, because a system you outgrow or cannot exit costs more than the saving."),
            ("Do I need all the modules at once?", "No. Start with the module that fixes your most painful process and add others as you grow."),
            ("Can I try before I buy?", "With a cloud product you usually can. ReckonERP plans show their trial days at signup."),
            ("What should I avoid?", "Avoid choosing from a feature list, signing without a data export clause, and skipping a trial with your own data."),
        ],
    },
    {
        "slug": "how-to-choose-an-erp-provider-in-bangladesh",
        "title": "How to Choose an ERP Provider in Bangladesh",
        "summary": "How to choose an ERP provider in Bangladesh: questions about support, implementation, data and cost that separate good partners from risky ones.",
        "keywords": "ERP provider Bangladesh, ERP implementation partner, ERP vendor selection, ERP support",
        "module": "",
        "category": "Article",
        "style": "people",
        "short": "judge a provider on how they will treat you after the sale: implementation help, support in your language, clear pricing and an honest answer on how you can leave. The software matters, but the partner decides whether it works.",
        "story_title": "Two vendors, one very different Monday",
        "story": [
            "Two companies buy ERP in the same month. Both pick well-reviewed products. On the first Monday after go-live, the first company finds its stock opening balances are wrong and calls its provider, who has the data corrected by noon. The second company calls its provider and is given a ticket number.",
            "Six months later the first company is running smoothly and the second is back on spreadsheets. The software was not the difference. The partner was.",
        ],
        "problem": [
            "An ERP is a long relationship with the people who set it up and support it. After the sale the work begins: loading data, training staff, fixing the odd problem and adapting the system as the business changes. A provider who is brilliant at selling and thin at supporting is the most common cause of failed projects.",
            "Buyers rarely test this before signing. They compare demos and prices, and learn how the provider behaves only after the contract is signed and the money is paid.",
        ],
        "symptoms": [
            "Support that answers only in office hours or only in one language.",
            "Implementation promised in a sentence, with no plan or owner.",
            "Training and data migration that appear as surprise charges.",
            "No clear answer on who owns the data and how it leaves.",
        ],
        "table": (["Area", "Strong provider", "Warning sign"], [
            ["Implementation", "A written plan, a named lead and milestones.", "We will set it up quickly, no details."],
            ["Support", "A clear channel, response times and your language.", "A shared inbox with no promises."],
            ["Pricing", "Included and extra items listed in writing.", "A low headline price and vague extras."],
            ["Training", "Sessions for each role, with materials.", "A video link and good luck."],
            ["Data", "Export at any time, your records are yours.", "Evasive about leaving."],
            ["Customisation", "Analysis first, then a quote.", "Yes to everything, on the spot."],
        ]),
        "options": [
            ("Ask how implementation will actually run", [
                "Ask who will lead your project, what the first four weeks look like and what you must provide. A provider who has done this often answers in specifics: opening balances, item lists, user roles, a test week.",
                "Vague answers are a signal. Implementation is where most of the effort and most of the surprises are, and a good provider has a routine for it.",
            ]),
            ("Test support before you need it", [
                "Send a real question to support during your trial and see how long it takes to get a useful answer, in the language your team uses. Ask which channels they offer, such as email and WhatsApp, and what hours they cover.",
                "Support quality is easy to measure before you buy and very hard to fix after.",
            ]),
            ("Get the money and the exit in writing", [
                "Ask for a written list of what the subscription includes and what is quoted separately: training, data migration, customisation, on-site visits, AI and integration usage. Ask what happens to your data if you stop paying or choose to leave.",
                "Clear answers here mean the provider has nothing awkward to hide. Hedged answers mean you should keep looking.",
            ]),
        ],
        "decide_intro": "Use the same short checklist with every provider.",
        "decide": [
            "Did they ask about your business before quoting?",
            "Can they name who will implement and who will support you?",
            "Is every cost listed, including the extras?",
            "Do they support Bangla and English, and on which channels?",
            "Can they explain how your data is separated and exported?",
        ],
        "steps_intro": "You can learn most of this in a week.",
        "steps": [
            "Send each provider the same list of questions and compare the written replies.",
            "Ask for a trial and use it for a real task with real data.",
            "Contact support once during the trial and note the speed and the quality.",
            "Ask for a written statement of inclusions, extras and data export.",
            "Choose the provider whose answers were clear, specific and consistent.",
        ],
        "fits": [
            "ReckonERP lists what is quoted separately: implementation, data migration, training, customisation, on-site support, and AI and integration usage. Subscription plans, billing periods and trial days are shown at <a href=\"/reckonerp-signup\">signup</a> and on the <a href=\"/pricing\">pricing page</a>.",
            "Support is available by email and WhatsApp, in English and Bangla, and dedicated cloud or on-premises installations are available on request. The <a href=\"/faq\">FAQ</a> answers the usual questions on licences, deployment and support.",
        ],
        "conclusion": [
            "The software gets you started; the provider keeps you going. Ask how implementation runs, test support during the trial and get costs and exit terms in writing.",
            "A provider who answers those questions plainly before you sign is likely to answer your problems plainly after.",
        ],
        "faqs": [
            ("What should an implementation plan include?", "A named lead, a timeline with milestones, the data you must provide, training sessions and a test period before go-live."),
            ("Is on-site support important?", "It can be, especially for larger teams. Ask whether it is offered, what it costs and how quickly someone can come."),
            ("How do I check support quality?", "Send a real question during your trial and compare the speed, clarity and language of the reply."),
            ("What costs are usually extra?", "Implementation, data migration, training, customisation and on-site visits. Ask for them in writing."),
            ("Can I ask for a reference?", "Yes. Speak to a current customer of similar size about their first three months."),
        ],
    },
    {
        "slug": "erp-implementation-cost-in-bangladesh",
        "title": "ERP Implementation Cost in Bangladesh: What Drives It",
        "summary": "What drives ERP implementation cost in Bangladesh: scope, data, training, customisation and hosting, and how to budget without surprises.",
        "keywords": "ERP implementation cost Bangladesh, ERP pricing, ERP budget, implementation services",
        "module": "",
        "category": "Article",
        "style": "spreadsheet",
        "short": "implementation cost is driven by scope, data quality, training, customisation and hosting, not by the licence alone. Start with one module, clean your data first and budget separately for training and changes, and the final bill stays close to the plan.",
        "story_title": "The quote that was only half the cost",
        "story": [
            "A trading company compares two quotes. The first is a low monthly subscription. The second is higher, but lists setup, data loading and training as lines. The owner picks the first because it is cheaper.",
            "Three months in, he has paid for data migration, two training days, a custom print format and a support plan, each billed separately. The cheaper quote ended up costing more, because its extras were not on the page.",
        ],
        "problem": [
            "ERP cost has two parts: what you pay to use the software, and what you pay to get your business into it and keep it fitting. The first is predictable. The second varies with your size, your data and how different your processes are from the standard.",
            "Budgets go wrong when only the first part is counted. Companies then discover the second part midway through the project, when they are least able to say no.",
        ],
        "symptoms": [
            "A subscription price with no mention of setup or training.",
            "Data that is messy, so loading it takes far longer than planned.",
            "Requests for custom changes that grow after go-live.",
            "Nobody has priced the time your own staff will spend.",
        ],
        "table": (["Cost driver", "What makes it grow", "How to control it"], [
            ["Subscription", "More modules and more users.", "Start with the module that fixes your biggest problem."],
            ["Setup and configuration", "Many companies, warehouses or roles.", "List them up front and phase the rest."],
            ["Data migration", "Messy, duplicated or incomplete records.", "Clean your lists before they are loaded."],
            ["Training", "Many roles and many sites.", "Train a few champions who train the rest."],
            ["Customisation", "Processes unlike the standard.", "Use configuration first and customise last."],
            ["Hosting choice", "Dedicated or on-premises installation.", "Start shared and move only if a requirement demands it."],
            ["Your staff's time", "Long projects with unclear owners.", "Name an owner and set weekly checkpoints."],
        ]),
        "options": [
            ("Software cost: the part you can see", [
                "The subscription or licence is easy to compare and easy to budget. For a cloud ERP it is usually a recurring fee per module or per user, with the billing period and any trial days stated. This is the number on the quote.",
                "It is rarely the largest cost over the first year for a business with real data and several users, so treat it as the starting point of the budget, not the budget itself.",
            ]),
            ("Implementation cost: the part you plan for", [
                "Implementation covers configuration, loading data, training and the testing week before go-live. Its size depends on how many companies, warehouses, items and people you have, and how clean your data is.",
                "The most reliable way to shrink it is to clean your customer, supplier and item lists before anything is loaded. Every duplicate removed beforehand is a problem you will not meet during the test week.",
            ]),
            ("Customisation and hosting: the part that varies", [
                "Customisation is the biggest swing factor. Extra fields and reports are modest; new workflows and integrations are larger. Work out whether configuration can meet the need before you commission code.",
                "Hosting adds another choice. A shared cloud has no setup cost beyond the subscription. A dedicated cloud or on-premises installation adds server and setup effort, in return for isolation or control.",
            ]),
        ],
        "decide_intro": "Ask these before you accept any quote.",
        "decide": [
            "Does the quote list setup, data migration, training and support, or only the subscription?",
            "What is quoted separately, and how is it priced?",
            "Who will clean and supply the data, and by when?",
            "How many people need training, and in how many sites?",
            "Which of your processes are truly different from the standard?",
        ],
        "steps_intro": "A budget built in this order rarely surprises you.",
        "steps": [
            "List the modules you need now and the ones that can wait.",
            "Clean your customer, supplier, item and opening-balance lists.",
            "Ask for a written quote with each cost line, including what is extra.",
            "Plan training for a few champions per role rather than for everyone at once.",
            "Hold back a modest amount for changes that appear after go-live.",
        ],
        "fits": [
            "ReckonERP shows the subscription price, billing period and trial days for every module at signup and on the <a href=\"/pricing\">pricing page</a>. Implementation, data migration, training, customisation, on-site support, and AI and integration usage are quoted separately, so you can see where the line falls.",
            "You can start self-serve on a shared cloud with no implementation, or ask for guided set-up. Dedicated cloud and on-premises installations are quoted for your needs. Read the <a href=\"/faq\">FAQ</a> on implementation cost, or <a href=\"/reckonerp-signup\">sign up</a> to see the plans.",
        ],
        "conclusion": [
            "ERP implementation cost is the sum of the software, the effort to get your business into it and the changes you ask for later. Counting only the first is how budgets break.",
            "Start with one module, clean your data, get every cost line in writing and keep customisation for what truly differs. The final bill will then stay close to the plan.",
        ],
        "faqs": [
            ("Can I start without any implementation cost?", "Yes. Self-serve signup needs no implementation, and you configure the workspace yourself. Guided set-up, migration and training are optional extras."),
            ("What affects the cost most?", "Scope, data quality and customisation. Training and hosting choices also matter."),
            ("Is data migration expensive?", "It depends on how much data you have and how clean it is. Cleaning your lists first reduces the effort."),
            ("Do I pay for AI and integrations separately?", "Yes. AI and integration usage is billed separately because it depends on usage and on outside providers."),
            ("How do I avoid surprises?", "Get a written list of included and extra costs, phase the work and keep a small reserve for changes."),
        ],
    },
    {
        "slug": "how-ai-agents-are-changing-business-automation",
        "title": "How AI Agents Are Changing Business Automation",
        "summary": "How AI agents differ from older automation, what they do well in business, where they need a person, and how to start safely.",
        "keywords": "AI agents, business automation, agentic AI, AI workflow automation",
        "module": "sales_agent",
        "category": "Article",
        "style": "ai",
        "short": "older automation follows fixed steps; an AI agent can read a situation, decide the next step and use your tools to carry it out. That makes it useful for messy, language-heavy work, provided it is limited to what it may touch and a person approves what matters.",
        "story_title": "The Monday-morning inbox",
        "story": [
            "A sales manager opens her inbox on Monday to forty new enquiries. Some are clear requests for a quote, some are questions that need a salesperson, some are spam. A rule-based tool can file the ones that contain the word quote. It cannot tell that a short, polite note from a large company is actually the most important message of the week.",
            "She wants help that reads the messages, understands which ones matter, prepares the first reply and updates the customer record, and then waits for her to approve before anything is sent. That is the kind of work AI agents are being built for.",
        ],
        "problem": [
            "Automation has long meant rules: when this happens, do that. Rules are reliable and cheap, but they break when the input is untidy. Real business work is untidy: free-text emails, different document layouts, requests that do not fit a form.",
            "As a result, much of the routine around sales, support and back-office work is still done by hand, not because it is hard but because it is varied. AI agents target that variety, and bring new risks that a rules engine never had.",
        ],
        "symptoms": [
            "Staff copy details between emails, sheets and the ERP all day.",
            "Rules that cover the common case and fail on the rest.",
            "Enquiries that wait because nobody has time to read them.",
            "Worry about letting software act without anyone checking.",
        ],
        "table": (["", "Fixed automation", "AI agent"], [
            ["How it works", "Follows steps you wrote.", "Chooses steps to reach a goal."],
            ["Handles untidy input", "Poorly.", "Reasonably, with checks."],
            ["Predictability", "High.", "Lower, so it needs limits."],
            ["Needs a person to approve", "Rarely.", "For anything that changes data or goes out."],
            ["Best for", "Exact, repeatable steps.", "Reading, research and drafting."],
        ]),
        "options": [
            ("What an AI agent actually does", [
                "An agent is given a goal, a set of tools and limits. It reads the situation, picks a step, uses a tool such as search the customer record or draft a reply, looks at the result and decides what to do next, until the goal is met or it needs help.",
                "The useful part is that you describe the goal in plain language rather than coding every branch. The risky part is that it may choose a path you did not expect, which is why limits matter.",
            ]),
            ("Where agents help most in a business", [
                "Agents suit work that is mostly reading and writing: qualifying leads, answering routine questions from your own records, summarising a customer's history, drafting follow-ups, preparing reports. They save time on the first draft and the first look.",
                "They are a poor fit for anything that must be exactly the same every time, such as tax calculations or approvals, where rules remain the right tool.",
            ]),
            ("How to keep them safe", [
                "Give an agent only the tools and records it needs. Make it show a preview and wait for a person's approval before it changes data or sends a message. Log every action. Cap how much it may spend on AI calls each month.",
                "These limits do not slow it down much, and they turn an unpredictable assistant into one you can trust with real work.",
            ]),
        ],
        "decide_intro": "Choose an agent when these are true.",
        "decide": [
            "The work is mostly reading, research or drafting.",
            "Inputs vary and a rule would miss many of them.",
            "A wrong first draft is cheap because a person checks it.",
            "You can limit the records and tools it may use.",
            "You can log what it did and review it.",
        ],
        "steps_intro": "Start small and expand as trust grows.",
        "steps": [
            "Pick one repeated task that is mostly reading or drafting.",
            "Define what the agent may read, what tools it may use and what it must never do.",
            "Run it in suggest-only mode, where every output is reviewed by a person.",
            "Measure time saved and mistakes caught, and adjust the limits.",
            "Add a second task only when the first is steady.",
        ],
        "fits": [
            "The <a href=\"/modules/sales_agent\">Sales AI Agent</a> finds and researches businesses, scores leads with rules you can read, drafts follow-ups and syncs to CRM, and nothing goes out without a person's approval. The <a href=\"/features/reckon-ai-assistant\">Reckon AI assistant</a> answers questions from your own records inside each user's permissions.",
            "For your own processes, we build custom agents after a requirement analysis; see <a href=\"/features/ai-agent-development\">AI agent development and automation</a>. AI and integration usage is billed separately.",
        ],
        "conclusion": [
            "AI agents extend automation from fixed steps to untidy, language-heavy work. They are powerful where the task is reading, research and drafting, and risky where exactness is required.",
            "Used with limits, a preview and a person's approval, they take the first pass off your team's hands and leave the decisions where they belong.",
        ],
        "faqs": [
            ("Will an AI agent replace my staff?", "It takes the first draft and the first look. People still decide, approve and handle the exceptions."),
            ("Is it safe to let an agent use my ERP?", "It can be, if it works inside a user's permissions, shows a preview and waits for approval before changing data."),
            ("Do agents make mistakes?", "Yes. That is why drafts are reviewed and actions are logged."),
            ("What does an agent cost to run?", "AI usage is billed per call by the provider, so set a monthly cap and review it."),
            ("Where should I start?", "With one repeated task that is mostly reading or drafting, in suggest-only mode."),
        ],
    },
    {
        "slug": "ai-agent-vs-ai-chatbot",
        "title": "AI Agent vs AI Chatbot: What Is the Difference?",
        "summary": "AI agent or AI chatbot? Compare what each does, how they use your systems, the risks and which one your business needs.",
        "keywords": "AI agent vs chatbot, AI chatbot, agentic AI, business automation",
        "module": "",
        "category": "Comparison",
        "style": "ai",
        "short": "a chatbot talks: it answers questions in a conversation. An agent acts: it can use tools, look things up and carry out steps toward a goal. Choose a chatbot for answering and guiding, and an agent when the job involves doing something in your systems.",
        "story_title": "The customer who asked twice",
        "story": [
            "A customer messages a company's website: where is my order? The chatbot replies with the delivery policy and a link to the tracking page. The customer asks again, this time with an order number. The bot repeats the policy.",
            "A second company handles the same question differently. Its assistant looks up the order in the system, sees it is out for delivery, and answers with the actual status and expected time. The first bot could talk. The second could act.",
        ],
        "problem": [
            "The words chatbot and agent are used loosely, and vendors use them to sell very different things. A buyer who expects an agent and gets a chatbot is disappointed. A buyer who expects a simple chatbot and gets an agent with access to live data has a security question to answer.",
            "Knowing the difference lets you pick the right tool for each job, and decide in advance how much access each one should have.",
        ],
        "symptoms": [
            "A bot that answers with general text when the customer needs a specific fact.",
            "Staff who answer the same lookup question many times a day.",
            "Unclear limits on what an assistant may see or change.",
            "Vendors who use the two words interchangeably.",
        ],
        "table": (["", "AI chatbot", "AI agent"], [
            ["Main job", "Converse and answer.", "Pursue a goal using tools."],
            ["Uses your systems", "Rarely, or read-only.", "Yes, within limits you set."],
            ["Can change data", "No.", "Only with approval, if designed safely."],
            ["Risk level", "Lower.", "Higher, so it needs limits and logs."],
            ["Set-up effort", "Modest.", "Larger: tools, permissions and testing."],
            ["Good for", "FAQs, guidance, first contact.", "Lookups, research, multi-step tasks."],
        ]),
        "options": [
            ("What a chatbot is good at", [
                "A chatbot holds a conversation. It answers common questions from a set of documents, guides people to the right page and collects details before handing over to a person. It is relatively simple to set up and carries low risk, because it only talks.",
                "Its limit is that it usually cannot do anything in your systems. It can tell a customer how returns work but cannot look up this customer's return.",
            ]),
            ("What an agent adds", [
                "An agent can use tools. It can look up an order, check stock, read a customer's history, draft a reply and update a record. Given a goal such as find out where this order is and tell the customer, it plans the steps and carries them out.",
                "That power is the point and the risk. An agent that can change data needs permission checks, a preview and a person's approval for anything that matters.",
            ]),
            ("Using both together", [
                "Many businesses use a chatbot at the front for common questions and hand the harder ones to an agent that can look things up, with a person in the loop for decisions. The customer sees one helpful assistant; behind it the roles are separate.",
                "This layered design limits risk: the part that talks to the public has little access, and the part that touches your systems is not exposed to anonymous visitors.",
            ]),
        ],
        "decide_intro": "Use these questions to choose.",
        "decide": [
            "Does the job require looking up or changing something in your systems?",
            "Who will talk to it: the public, your staff, or both?",
            "How costly is a wrong answer?",
            "Can you limit what it may see and do?",
            "Do you need a record of what it did?",
        ],
        "steps_intro": "A sensible rollout adds access in steps.",
        "steps": [
            "Start with a chatbot for common questions from your own documents.",
            "Add read-only lookups for staff, inside each person's permissions.",
            "Add drafting, so the assistant prepares replies a person approves.",
            "Allow actions only with a preview, a permission check and an action log.",
            "Review results monthly and trim anything that does not help.",
        ],
        "fits": [
            "The <a href=\"/features/reckon-ai-assistant\">Reckon AI assistant</a> is an agent-style assistant inside the ERP: it answers from the records the signed-in person may see, suggests actions and applies them only after approval. The <a href=\"/modules/sales_agent\">Sales AI Agent</a> researches and drafts, and waits for a person before sending.",
            "If you need a chatbot or agent built around your own processes, see <a href=\"/features/ai-agent-development\">AI agent development and automation</a>. AI and integration usage is billed separately; see <a href=\"/pricing\">pricing</a>.",
        ],
        "conclusion": [
            "A chatbot talks and an agent acts. Both are useful; the difference lies in access and risk. Use a chatbot to answer and guide, and an agent where the work involves your systems.",
            "Start with the one that needs the least access, and give it more only as you gain trust and as the logs show it behaving as intended.",
        ],
        "faqs": [
            ("Is an AI agent just a smarter chatbot?", "Not exactly. A chatbot converses; an agent also uses tools to carry out steps toward a goal."),
            ("Which is safer?", "A chatbot is safer because it has little access. An agent can be made safe with permission checks, previews and approvals."),
            ("Can I use both?", "Yes. Many businesses put a chatbot at the front and an agent behind it for lookups and tasks."),
            ("Do agents need my data?", "They need access to the records relevant to the task. Limit this to what the signed-in user may see."),
            ("What does it cost?", "AI usage is billed by the provider per call. Set a monthly cap and review it."),
        ],
    },
    {
        "slug": "automate-sales-and-marketing-with-ai-agents",
        "title": "Automate Sales and Marketing with AI Agents",
        "summary": "How to automate sales and marketing with AI agents: lead discovery, research, scoring and follow-ups, while a person approves every message.",
        "keywords": "AI sales automation, AI marketing automation, AI sales agent, lead generation",
        "module": "sales_agent",
        "category": "Tutorial",
        "style": "crm",
        "short": "let an AI agent do the searching, reading and first drafts, such as finding prospects, researching their websites, scoring them and drafting follow-ups, and keep a person in charge of what is sent. That frees your team to talk to customers.",
        "story_title": "Three days to find ten leads",
        "story": [
            "A small B2B team spends three days a week searching for prospects. They open websites, hunt for a contact, decide whether the company is a fit and paste notes into a spreadsheet. By Friday they have ten leads and no time left to call them.",
            "The searching is necessary but it is not selling. What the team wants is for the research to be done before they sit down, so that Monday begins with a short list of well-understood companies and a draft message ready to review.",
        ],
        "problem": [
            "Sales and marketing teams spend much of their time on preparation: finding prospects, reading about them, deciding who is worth a call and writing the first message. This work is repetitive and slow, and it is what AI agents are good at.",
            "Handing it over carelessly is risky. An agent that sends messages on its own can annoy prospects, make claims you cannot back and damage your reputation. The goal is to automate the preparation and keep the decision with a person.",
        ],
        "symptoms": [
            "Days spent searching and reading instead of talking to customers.",
            "Lead notes that live in personal sheets and get lost.",
            "Follow-ups that slip because nobody has time to write them.",
            "Fear that automated messages will sound generic or make wrong claims.",
        ],
        "table": (["Step", "Done by hand", "With an AI agent"], [
            ["Find prospects", "Searching and note-taking.", "A discovery campaign lists businesses that match."],
            ["Research each one", "Reading websites for an hour.", "The agent reads the site and keeps its evidence."],
            ["Decide who is worth a call", "Gut feeling.", "A score from fixed rules you can read."],
            ["Write the first message", "From scratch each time.", "A draft that cites what was found."],
            ["Send and follow up", "When someone remembers.", "A sequence that waits for a person to approve."],
            ["Record it", "Later, if at all.", "Synced to your CRM automatically."],
        ]),
        "options": [
            ("Automating discovery and research", [
                "A discovery campaign defines who you want to reach: an industry, a place, a size. The agent finds matching businesses, visits their websites and notes what they do, with the evidence kept next to each claim so a person can check it.",
                "This replaces the slow, repetitive part of prospecting and gives the team a consistent starting point for every lead.",
            ]),
            ("Scoring and drafting", [
                "Scoring works best with fixed rules you can read, such as points for a clear fit and for a way to reach the right person. You can explain the score and change the rules, which a hidden model does not allow.",
                "The agent then drafts a follow-up that refers to what it found. A person reads, edits and approves it. The draft saves the blank page; the person keeps the voice and the decision.",
            ]),
            ("Marketing automation with limits", [
                "The same pattern works for marketing: draft a post, an email or a landing-page paragraph from your own facts, and have a person approve it before it is published. Keep claims to what you can back, and avoid inventing statistics or testimonials.",
                "Set a monthly cap on AI usage and review what was sent. Automation should make your team faster, not make your brand louder than it can justify.",
            ]),
        ],
        "decide_intro": "Check these before you automate sales and marketing.",
        "decide": [
            "Is the bottleneck preparation rather than the conversation itself?",
            "Can you describe your ideal customer in a few lines?",
            "Will a person approve every message before it goes out?",
            "Can the agent show where each claim came from?",
            "Do you have a CRM where results should land?",
        ],
        "steps_intro": "A first campaign can run within days.",
        "steps": [
            "Describe your ideal customer: industry, place, size and what you offer.",
            "Run a small discovery campaign and review the leads it finds.",
            "Read the research and the scores, and adjust the rules where they feel wrong.",
            "Review each draft, edit it and approve only what you would send yourself.",
            "Sync approved leads to your CRM and track replies.",
        ],
        "fits": [
            "The <a href=\"/modules/sales_agent\">Sales AI Agent</a> runs discovery campaigns, researches each lead's website with evidence, scores it with deterministic rules and drafts email sequences that wait for approval. It syncs leads to the <a href=\"/modules/crm\">CRM module</a>, so your team follows up instead of searching.",
            "Read more at <a href=\"/features/ai-assisted-selling\">AI-assisted selling</a>. AI and integration usage is billed separately, and custom agents for your own process are described at <a href=\"/features/ai-agent-development\">AI agent development and automation</a>.",
        ],
        "conclusion": [
            "AI agents are best at the work around selling: finding, reading, scoring and drafting. Your people are best at the conversation. Automating the first set lets them spend more time on the second.",
            "Keep a person approving every message, keep claims to what you can support, and review the results regularly. That is automation that helps a sales team without embarrassing it.",
        ],
        "faqs": [
            ("Will the agent send messages without my approval?", "No. Drafts wait for a person's approval before anything is sent."),
            ("How are leads scored?", "With fixed rules you can read and change, not a hidden model."),
            ("Where do the leads go?", "Approved leads sync to your CRM so your team can follow up."),
            ("Can it write marketing content?", "It can draft from your facts. A person should review before anything is published."),
            ("What does it cost?", "The module has its own plan. AI and integration usage is billed separately."),
        ],
    },
    {
        "slug": "distribution-management-software-for-fmcg-businesses",
        "title": "Distribution Management Software for FMCG Businesses",
        "summary": "What FMCG distribution software should do: routes, retailer dues, cash custody, stock and accounts, and how to choose one that fits.",
        "keywords": "distribution management software, FMCG distribution Bangladesh, route sales, retailer dues, DSR",
        "module": "distribution",
        "category": "Article",
        "style": "route",
        "short": "FMCG distribution software should cover routes and deliveries, retailer dues and collections, cash carried by each rep, stock and goods held for principals, and post everything to your books. Choose one that your field team will actually use on a phone.",
        "story_title": "A route that made money and lost it",
        "story": [
            "A distributor's best route sells well every week. Yet at month end the money from that route does not match the sales. Deliveries were made, retailers say they paid, and the cash handed in is lower than the total.",
            "The owner suspects nobody in particular. The truth is that there is no single record of who owed what at the start of each visit, who paid what during it and what the rep handed in afterwards. Without that chain, a shortfall is only a number.",
        ],
        "problem": [
            "FMCG distribution runs on thin margins and high volume. A small leak on each visit becomes a large loss over a month. The leaks hide in three places: retailer balances that are not updated at the visit, cash that is not tracked from collection to handover, and stock that moves without a record.",
            "General accounting software records the invoice and the payment, but not the route, the rep or the cash in the van. That gap is what distribution software exists to close.",
        ],
        "symptoms": [
            "Retailer balances that disagree with the retailer's own notebook.",
            "Cash shortfalls that cannot be traced to a visit or a rep.",
            "Goods for principals mixed with your own stock.",
            "Reps who spend the evening writing instead of resting.",
        ],
        "table": (["Capability", "Why it matters", "What to look for"], [
            ["Route planning", "Visits happen in a planned order.", "Routes per SR and DSR, with delivery tracking."],
            ["Retailer dues", "Credit must be controlled.", "A running balance updated at each visit."],
            ["Cash custody", "Money moves through the rep's hands.", "Collected and handed-in amounts per DSR."],
            ["Principal goods", "You may hold stock that is not yours.", "Supplier-provided goods tracked separately."],
            ["Field app", "Reps work on phones, often in Bangla.", "A phone-browser screen, Bangla-first."],
            ["Accounts", "The books must agree with the field.", "Invoices, stock and payments post to your books."],
        ]),
        "options": [
            ("Routes, visits and deliveries", [
                "Good distribution software plans the day for each sales rep and delivery rep, records each visit and delivery as it happens and lets a manager see progress during the day instead of the next morning.",
                "This turns the route from a habit into a record, and makes it possible to compare routes, spot slow ones and rebalance work.",
            ]),
            ("Dues, collections and cash custody", [
                "Each retailer has a running balance, updated by invoices and collections. Each rep's cash is recorded as collected during the day and as handed in afterwards, so a difference shows up the same evening, with the visit that caused it.",
                "This is the feature that most directly protects money, and it is the one general accounting tools lack.",
            ]),
            ("Stock, principals and accounts", [
                "Stock moves from the warehouse to the van to the retailer, and each step is a record. If you carry goods for principals, they are tracked as theirs, with their own reports.",
                "Everything posts to your accounts, so the field, the warehouse and the books show the same numbers without anyone re-typing.",
            ]),
        ],
        "decide_intro": "A short checklist for choosing distribution software.",
        "decide": [
            "Does it track cash from collection to handover, per rep?",
            "Does a retailer's balance update at the visit?",
            "Can it separate principal-supplied goods from your stock?",
            "Will your reps use it on their own phones, in Bangla?",
            "Does it post to accounts without re-typing?",
        ],
        "steps_intro": "Roll out one route at a time.",
        "steps": [
            "Load your retailers with opening balances and your items with prices.",
            "Pilot one route and one rep for two weeks.",
            "Compare the evening cash count with the system's total each day.",
            "Fix the gaps you find, then add the next route.",
            "Connect accounting so the books and the field agree.",
        ],
        "fits": [
            "The <a href=\"/modules/distribution\">Distribution module</a> covers route planning and delivery tracking, retailer dues and collections, DSR cash custody, supplier-provided goods and a Bangla-first mobile app that runs in the phone's browser. It posts to your Company's books.",
            "See <a href=\"/industries/fmcg-distribution\">FMCG distribution</a> for the sector overview, <a href=\"/blog/fmcg-route-sales-spreadsheets-vs-distribution-erp\">FMCG Route Sales: Spreadsheets vs a Distribution ERP</a> for the comparison and <a href=\"/pricing\">pricing</a> for plans.",
        ],
        "conclusion": [
            "FMCG distribution software earns its place by closing three leaks: retailer dues, cash custody and stock movement. If it does those and your team will use it on a phone, it pays for itself in the first bad week it prevents.",
            "Pilot one route, compare the numbers daily and expand once the evening count matches the system. The data will show you where the money was going.",
        ],
        "faqs": [
            ("What is DSR cash custody?", "It is the record of cash each delivery rep collected during the day and handed in afterwards, so differences show up the same day."),
            ("Do reps need to install an app?", "No. The field screens run in the phone's browser."),
            ("Can it handle goods I hold for a principal?", "Yes. Supplier-provided goods are tracked alongside your own stock."),
            ("Does it connect to accounting?", "Yes. Invoices, stock and payments post to your Company's books."),
            ("Can I try it first?", "Yes. Plans show their trial days at signup."),
        ],
    },
    {
        "slug": "hr-and-payroll-automation-in-bangladesh",
        "title": "HR and Payroll Automation for Bangladeshi Businesses",
        "summary": "How to automate HR and payroll in a Bangladeshi business: attendance, leave, approvals and salary runs, and what to set up first.",
        "keywords": "HR payroll software Bangladesh, payroll automation, attendance and leave, HRMS",
        "module": "hrms",
        "category": "Tutorial",
        "style": "people",
        "short": "automate HR in the order the data flows: employee records first, then attendance and shifts, then leave with approvals, then payroll built from them. Each step removes a manual copy and makes the next one reliable.",
        "story_title": "The payroll that took four days",
        "story": [
            "An HR officer at a mid-sized company starts payroll on the 25th. She gathers attendance registers from three sites, matches them to a leave sheet, adds overtime from a supervisor's note and builds each salary by hand. It takes four days, and every month somebody finds an error after pay day.",
            "The work is not difficult. It is long, repetitive and unforgiving, because the same facts, who was present, who was on leave, who worked extra, are held in separate places and must be copied by hand into the salary sheet.",
        ],
        "problem": [
            "Payroll is the end of a chain that begins with an employee record, passes through attendance and leave and ends in a salary. When each link lives in a different file, every link is a place for a copying error, and the error shows up as someone's pay.",
            "Automation works by connecting the links so that each fact is entered once, where it happens, and flows on to the next step without being retyped.",
        ],
        "symptoms": [
            "Payroll takes days and is checked line by line.",
            "Attendance, leave and overtime live in different files.",
            "Employees dispute balances and nobody can show the working.",
            "Approvals happen by message and are hard to prove later.",
        ],
        "table": (["Stage", "Manual", "Automated"], [
            ["Employee records", "A sheet with one row per person.", "One record per employee, kept current."],
            ["Attendance and shifts", "Registers typed in at month end.", "Recorded as it happens."],
            ["Leave", "Requests by message, balances by hand.", "Requested and approved in the system."],
            ["Payroll", "Formulas rebuilt monthly.", "Built from attendance and leave."],
            ["Employee questions", "Ask HR.", "Self-service view of their own records."],
            ["Proof of approval", "Search old messages.", "A record of who approved what."],
        ]),
        "options": [
            ("Start with clean employee records", [
                "Automation is only as good as its starting data. Make sure each person appears once, with the right joining date, grade and contact details. Duplicates and wrong dates here become wrong salaries later.",
                "This cleaning step is dull and it is the most valuable hour of the whole project.",
            ]),
            ("Record attendance and leave where they happen", [
                "Attendance and shifts are recorded in the system rather than typed from registers at month end. Leave is requested by the employee and approved by a manager, with balances updated automatically.",
                "The payoff is that disputes shrink: the balance and the approval are visible to both sides.",
            ]),
            ("Build payroll from the records", [
                "When attendance and leave are in the system, payroll reads them. The run becomes a review of exceptions rather than a rebuild from scratch. HR checks the unusual cases, not every row.",
                "Statutory filings and tax returns remain outside a basic HRMS, so plan how your accountant will handle them from the payroll output.",
            ]),
        ],
        "decide_intro": "Automate in this order, and stop when the next step is not worth it yet.",
        "decide": [
            "Is the employee list clean and complete?",
            "Is attendance recorded in more than one place?",
            "Do employees and managers need to approve leave in the system?",
            "How many hours does payroll take each month?",
            "Do employees need to see their own records?",
        ],
        "steps_intro": "A first month of automation, step by step.",
        "steps": [
            "Clean the employee list and agree joining dates, grades and contact details.",
            "Write down working hours, shifts and leave types with their yearly days.",
            "Set who approves leave and who may run payroll.",
            "Record attendance and leave in the system for one month while you keep your sheet.",
            "Run payroll in parallel, compare the results, fix differences and retire the sheet.",
        ],
        "fits": [
            "The <a href=\"/modules/hrms\">HRMS module</a> gives small businesses employees, attendance and shifts, leave and payroll in a private workspace per company, with roles for HR manager, payroll manager, talent admin and employee self-service.",
            "Pair it with <a href=\"/modules/accounts\">Accounts</a> to keep your books tidy. For the comparison with spreadsheets, read <a href=\"/blog/hr-payroll-spreadsheets-vs-hrms-module\">HR and Payroll: Spreadsheets vs an HRMS Module</a>, and see <a href=\"/pricing\">pricing</a> for plans.",
        ],
        "conclusion": [
            "HR and payroll automation is mostly about connecting facts that were always there. Clean records, attendance and leave in the system and a payroll built from them turn a four-day chore into a review.",
            "Start with the employee list, run one month in parallel with your sheet and retire the sheet when the numbers match. The saving is time, and the bigger gain is trust.",
        ],
        "faqs": [
            ("Does payroll use attendance and leave?", "Yes. Payroll is built from the attendance and leave recorded in the module."),
            ("Can employees see their own data?", "Yes, through the employee self-service role, subject to company settings."),
            ("Does it file tax returns?", "No. Statutory filings are outside the module."),
            ("How long does set-up take?", "Most of the time goes into cleaning the employee list and agreeing leave rules. The set-up itself is quick."),
            ("Can I run it alongside my sheet first?", "Yes, and it is the safest way to switch."),
        ],
    },
    {
        "slug": "how-to-implement-ai-in-erp-systems",
        "title": "How to Implement AI in ERP Systems, Step by Step",
        "summary": "A step-by-step guide to adding AI to an ERP: pick the use case, check your data, set limits, test with approvals and measure the result.",
        "keywords": "AI in ERP, implement AI ERP, ERP AI integration, AI assistant ERP",
        "module": "",
        "category": "Tutorial",
        "style": "ai",
        "short": "start with one use case that is mostly reading or drafting, check that your data is clean enough, limit what the AI can see and change, run it in suggest-only mode and measure the time saved. Expand only when the results justify it.",
        "story_title": "The pilot that started with a question",
        "story": [
            "A finance team asks a modest question: can we just ask the system which customers are overdue and why? Today someone runs three reports, joins them in a sheet and writes a summary. It takes an hour, and it is needed every Monday.",
            "That single question is a good first AI project. It is repeated, it is mostly reading, a wrong answer is easy to spot and the data already exists. Starting there teaches the team more than a grand plan would.",
        ],
        "problem": [
            "Adding AI to an ERP is tempting to attempt all at once: forecasting, assistants, automation, agents. Projects that start that way tend to stall, because the data is not ready, the limits are not set and nobody agrees how to judge success.",
            "The safer path treats AI as a series of small, measurable additions, each with a clear job, clear limits and a person approving what changes.",
        ],
        "symptoms": [
            "A long list of AI ideas with no first project.",
            "Doubt that the data is clean enough to be useful.",
            "No agreement on what the AI may see or change.",
            "No way to tell whether the pilot saved anything.",
        ],
        "table": (["Step", "Question to answer", "Output"], [
            ["Choose a use case", "What repeated task is mostly reading or drafting?", "One named task."],
            ["Check the data", "Is the data complete and consistent enough?", "A list of fixes."],
            ["Set limits", "What may the AI see, use and change?", "A short permission rule."],
            ["Run suggest-only", "Do people agree with what it proposes?", "A review log."],
            ["Measure", "Did it save time without raising errors?", "A before and after number."],
            ["Expand", "Is a second task worth it?", "A decision."],
        ]),
        "options": [
            ("Choose the first use case with care", [
                "Pick something repeated, mostly reading or drafting, and low in risk. Good first tasks are answering questions about your own records, summarising a customer's history, drafting a follow-up or flagging unusual entries for review.",
                "Avoid starting with anything that moves money or changes records automatically. Earn that trust first.",
            ]),
            ("Prepare the data and the limits", [
                "AI repeats whatever your data says, including its mistakes. Check that customer names, item codes and dates are consistent, and fix the worst problems before the pilot.",
                "Then decide, in writing, what the AI may read, which tools it may use and what it must never do. The simplest rule is that it works inside the permissions of the person asking and changes nothing without approval.",
            ]),
            ("Run it safely and measure it", [
                "Run the pilot in suggest-only mode: the AI proposes, a person decides. Keep a log of what was proposed, what was accepted and what was changed. Cap monthly AI usage so costs stay visible.",
                "After a few weeks compare time spent and errors caught against the old way. If the numbers are good, choose the next task. If not, adjust the limits or stop.",
            ]),
        ],
        "decide_intro": "Move to the next step only when these are true.",
        "decide": [
            "People accept most of what the AI proposes in suggest-only mode.",
            "The time saved is real and measured.",
            "Nobody has found the AI reading something it should not.",
            "Monthly cost is within the cap.",
            "The logs are being reviewed by a named person.",
        ],
        "steps_intro": "The same sequence works for almost any first AI project.",
        "steps": [
            "Pick one repeated task that is mostly reading or drafting.",
            "Clean the few data fields that task depends on.",
            "Write the limits: what it may see, use and change, and who approves.",
            "Run it in suggest-only mode for a few weeks and review the log.",
            "Measure time saved and errors, then decide whether to add a second task.",
        ],
        "fits": [
            "The <a href=\"/features/reckon-ai-assistant\">Reckon AI assistant</a> is built this way: it answers from the records the signed-in person may see, proposes actions with a preview and applies them only after approval, with every confirmed action logged.",
            "For processes particular to your business, we design custom agents after analysis; see <a href=\"/features/ai-agent-development\">AI agent development and automation</a>. AI and integration usage is billed separately; see <a href=\"/pricing\">pricing</a> and read <a href=\"/blog/rules-vs-machine-learning-vs-llm-assistants-in-erp\">Rules, Machine Learning or LLMs: AI Options in ERP</a> for choosing a technique.",
        ],
        "conclusion": [
            "Implementing AI in an ERP is a sequence of small wins, not one large project. Choose a modest first task, clean the data it uses, set limits, run it with approvals and measure the result.",
            "Teams that follow this order learn quickly, spend little and build the trust they need to give AI more to do later.",
        ],
        "faqs": [
            ("What is a good first AI use case in ERP?", "A repeated task that is mostly reading or drafting, such as answering questions about overdue customers or summarising a customer's history."),
            ("Does my data need to be perfect?", "No, but the fields the AI relies on should be consistent. Fix the worst problems first."),
            ("Should AI change records automatically?", "Not at first. Use suggest-only mode and require a person's approval."),
            ("How do I measure success?", "Compare time spent and errors caught before and after, over a few weeks."),
            ("What does it cost?", "AI usage is billed by the provider per call. Set a monthly cap and review it."),
        ],
    },
]

for _post in GUIDES:
    _post["body"] = build_body(_post)


def _cover(post: dict) -> None:
    try:
        from reckon_saas_platform import blog_image

        cover = blog_image.attach_cover(post["slug"], post["title"], post["category"], post["style"])
        if cover:
            frappe.db.set_value(blog.DOCTYPE, post["slug"], {"cover_image": cover, "cover_style": post["style"]})
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Guide post cover")


def seed_guides() -> list[str]:
    """Create each guide as a Draft with a cover and a promotion kit, unless its slug already exists."""
    created = []
    base = marketing.site_base()
    for post in GUIDES:
        if frappe.db.exists(blog.DOCTYPE, post["slug"]):
            continue
        link = f"{base}{blog.article_url(post['slug'])}"
        frappe.get_doc(
            {
                "doctype": blog.DOCTYPE,
                "slug": post["slug"],
                "title": post["title"],
                "category": post["category"],
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
