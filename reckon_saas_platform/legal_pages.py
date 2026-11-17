"""The policy pages linked from checkout and the footers: privacy, refunds, payments and security.

Plain statements of how ReckonERP works today. Edit the text here; the pages, the footer links and the
payment footer pick it up. Dates are the day the text was last reviewed.
"""

from __future__ import annotations

COMPANY = "Reckon Technologies Ltd."
CONTACT_EMAIL = "info@reckon.tech"
ADDRESS = "Saleh Tower, 5th Floor, Garib-E-Nawaz Avenue, Plot 1, Road 13, Sector 13, Uttara, Dhaka 1230, Bangladesh"
UPDATED = "17 November 2026"

# slug -> page. A section is (heading, [paragraph or [bullet, ...]]).
PAGES = {
    "privacy-policy": {
        "title": "Privacy policy",
        "description": "A short, plain summary of what ReckonERP collects, why, who it is shared with and how to ask for your data to be corrected or deleted.",
        "lead": f"A short summary of how {COMPANY} handles your information.",
        "sections": [
            ("What we collect", [
                "When you sign up: your business name, your name, your work email, your mobile number and a password, which is kept only as a one-way hash. When you use ReckonERP: the business records you and your team enter in your workspace, and basic technical records such as sign-in times, pages opened and errors.",
                "If you start the signup form but do not finish it, we may keep the details you entered, with basic visit information such as the time, IP address and approximate location, so our team can help you complete it. You can ask us to delete it at any time.",
            ]),
            ("How we use it", [
                ["To run your workspace and your subscription.",
                 "To send invoices, receipts and service messages.",
                 "To keep the service secure and fix problems.",
                 "To understand how the website is used, where you allow it."],
            ]),
            ("How we protect it", [
                "Each company's data stays in its own private workspace, and data travels over encrypted connections. The credentials and keys connected to your subscription are kept encrypted using the Frappe framework's built-in encryption.",
            ]),
            ("Who we share it with", [
                "We do not sell personal data, and we do not disclose it to third parties for their own purposes. To run the service we use hosting, email, SMS, messaging, AI and bot-protection providers as channels that act on our behalf. Each receives only the data its function needs, over encrypted connections (HTTPS/TLS), and AI features send only the text you ask them to work on.",
                "Card details are entered by you in Paddle's checkout and handled by Paddle under its own terms; they do not pass through our servers. We may disclose information where the law requires it.",
            ]),
            ("Cookies", [
                "The website uses cookies for sign-in, language and theme and, with your consent where required, for analytics. You can refuse non-essential cookies in the banner or in your browser.",
            ]),
            ("Keeping and deleting your data", [
                f"We keep account and billing records while your subscription is active and for as long afterwards as the law requires. You can ask to see, correct, export or delete your information by writing to {CONTACT_EMAIL}; we reply within a reasonable time.",
            ]),
            ("Changes and contact", [
                f"We update this page when our practices change. Questions: {CONTACT_EMAIL}, {COMPANY}, {ADDRESS}.",
            ]),
        ],
    },
    "refund-policy": {
        "title": "Refund policy",
        "description": "When ReckonERP subscription payments are refunded, how to ask, and how refunds are paid.",
        "lead": "A fair way out if ReckonERP is not right for you.",
        "sections": [
            ("Free trial first", [
                "Most plans start with a free trial, so you can try the product before you pay. Use it to check that ReckonERP fits your business.",
            ]),
            ("First payment", [
                f"If you are not satisfied, ask for a refund of your first subscription payment within 14 days of paying. Write to {CONTACT_EMAIL} with your company name and the payment reference. We refund the subscription amount in full.",
            ]),
            ("Renewals", [
                "Renewal payments are not refunded once the new period has started, except for billing errors, a payment taken twice, or a renewal you asked us to cancel before its date. Cancel before the renewal date to avoid the next charge.",
            ]),
            ("What is not refunded", [
                "Usage-based charges for AI and messaging channels, third-party fees, and paid services such as implementation, data migration, training and customisation follow the quote you accepted for them.",
            ]),
            ("How refunds are paid", [
                ["Card and wallet payments are refunded by our payment provider Paddle to the original payment method. Banks usually take 5 to 10 working days to show it.",
                 "Payments made in Taka by bank transfer, bKash, Nagad or Rocket are refunded to the account or wallet they came from, after we verify the request."],
                "If you are covered by consumer rights that give you more than this policy, those rights still apply.",
            ]),
        ],
    },
    "payment-policy": {
        "title": "Payment policy",
        "description": "How ReckonERP is billed: Taka payments, card and wallet payments through Paddle, renewals, taxes, invoices and what happens when a payment fails.",
        "lead": "How you pay for ReckonERP, and what to expect.",
        "sections": [
            ("Plans and prices", [
                "Each module has its own plan, price and billing period (monthly or yearly). The price, billing period and trial days are shown at signup before you pay. The plan price is for the software only. Implementation, training, customisation and AI and channel usage are quoted or billed separately.",
            ]),
            ("Paying in Taka", [
                "Plans priced in Taka are paid by bank transfer, bKash, Nagad or Rocket using the details on your invoice. Enter your transaction ID on the signup or Subscription page and we unlock your workspace once we verify the payment.",
            ]),
            ("Paying by card and wallet", [
                "Plans priced in US dollars can be paid by card and wallet. Card payments are processed by Paddle, our payment provider and reseller, which appears on your statement and shows the available payment methods for your country at checkout. Paddle can show the price in your local currency; the amount you are charged is the one shown at checkout.",
                "Card subscriptions renew automatically each billing period until you cancel. You can change your card or cancel in the customer portal under Subscription.",
            ]),
            ("Taxes and invoices", [
                "Listed prices exclude VAT, GST and other sales taxes. Where tax applies to your purchase, it is added on top at checkout, and the total is shown before you pay. Business customers are responsible for the taxes that apply to them in their own country, and can enter a tax ID at checkout where it is accepted. We send an invoice and a receipt by email for every payment.",
            ]),
            ("If a payment fails or is late", [
                "Your access continues to the end of the period you paid for and then through the grace days of your plan. If the payment is still missing after that, your workspace is locked. Your data is kept, and access returns when the payment is verified.",
            ]),
            ("Questions", [f"Write to {CONTACT_EMAIL}."]),
        ],
    },
    "security": {
        "title": "Security",
        "description": "How ReckonERP protects your data: private company workspaces, role-based access, encrypted connections, secure payments and how to report a vulnerability.",
        "lead": "How we protect your business data.",
        "sections": [
            ("Your own private workspace", [
                "Every company works in its own workspace. Records belong to a company, and each person can open only the records of their own company. Vendor staff are kept apart from customer workspaces by role.",
            ]),
            ("Who can do what", [
                "Company admins give each person only the modules and roles they need, and can remove access at any time. Plans can limit the number of users.",
            ]),
            ("Protected connections and secrets", [
                ["All traffic to the website and the app uses HTTPS.",
                 "Passwords are stored only in a protected form (a one-way hash), and the credentials, API keys and tokens of your subscription are stored encrypted using the Frappe framework's built-in encryption with a secret key of the installation.",
                 "Signup is protected by email and mobile verification, rate limits and bot checks."],
            ]),
            ("Payments", [
                "Card details are entered on Paddle's checkout and never reach our servers. Payment notifications from Paddle are checked with a signature before they are used.",
            ]),
            ("Operations", [
                "We keep regular backups, monitor the service for errors and security events, and apply updates to the platform. Network access to customer devices that sync attendance is limited to public addresses you provide.",
            ]),
            ("Reporting a problem", [
                f"If you think you have found a security problem, write to {CONTACT_EMAIL}. Please give us a chance to fix it before sharing it publicly. We will confirm that we received your report.",
            ]),
        ],
    },
}

# The facts a reader wants first, per page: (label, value). Each page answers its own question.
GLANCE = {
    "privacy-policy": [
        ("We collect", "Business, name, email, mobile, usage logs"),
        ("We never", "Sell or share your data with others, or store your card number"),
        ("Credentials", "Kept encrypted (Frappe encryption)"),
        ("Your data", "Export, correct or delete it on request"),
        ("Ask us at", CONTACT_EMAIL),
    ],
    "refund-policy": [
        ("First payment", "Full refund within 14 days"),
        ("Renewals", "Cancel before the renewal date"),
        ("Refund time", "5 to 10 working days to your bank"),
        ("Ask us at", CONTACT_EMAIL),
    ],
    "payment-policy": [
        ("Taka plans", "Bank transfer, bKash, Nagad, Rocket"),
        ("USD plans", "Card and wallet through Paddle"),
        ("Renewal", "Automatic by card; invoice for Taka"),
        ("Late payment", "Grace days, then workspace locks, data kept"),
    ],
    "security": [
        ("Workspaces", "Private per company"),
        ("In transit", "HTTPS everywhere"),
        ("Card data", "Never reaches our servers"),
        ("Report a flaw", CONTACT_EMAIL),
    ],
}

ICONS = {
    "privacy-policy": "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4",
    "refund-policy": "M4 12a8 8 0 1 0 3-6.2M4 4v4h4M12 8v4l3 2",
    "payment-policy": "M3 7h18v11H3zM3 11h18M7 15h3",
    "security": "M7 11V8a5 5 0 0 1 10 0v3M5 11h14v9H5zM12 15v2",
}

LINKS = (
    ("Security", "/security"),
    ("Payment policy", "/payment-policy"),
    ("Refund policy", "/refund-policy"),
    ("Privacy policy", "/privacy-policy"),
)
