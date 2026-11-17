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
        "description": "What ReckonERP collects, why, who it is shared with, how long it is kept and how to ask for your data to be corrected or deleted.",
        "lead": f"How {COMPANY} handles personal information in ReckonERP.",
        "sections": [
            ("What we collect", [
                "When you sign up we collect your business name, your name, your work email, your mobile number with its country code and the password you choose (stored only in a protected form).",
                "When you use ReckonERP we keep the business records you and your team enter in your own company workspace, and the technical records needed to run the service: sign-in times, the pages you open, errors and security events.",
                "If you start the signup form and give us your email address or mobile number but do not submit it, we may keep what you entered, with the time, your IP address, the country of your browser's time zone, your browser language, device type, the page you came from and any campaign tags in the link, so our team can contact you and help you finish. We work out the country of your IP address on our own server, with the free DB-IP Lite country table (db-ip.com, licensed CC BY 4.0), so your IP address is not sent to any other service to find where you are. Ask us to delete it at any time.",
                "We do not store your card number. Card payments are handled by our payment provider Paddle, which shows you its own checkout.",
            ]),
            ("How we protect your data", [
                "We protect your data because we value your consent and your privacy. We never sell your data, and we never share it with anyone for their own purposes. It reaches only the services we need to run ReckonERP for you, listed under Who we share it with, and each receives only what its job needs.",
                "The credentials and keys connected to your subscription, such as API keys, tokens and secrets for the services you connect, are kept encrypted. ReckonERP is built on the Frappe framework, whose password-field encryption stores them encrypted with a secret key of the installation. Your sign-in password is not stored at all in readable form; only a one-way hash of it is kept.",
            ]),
            ("How we use it", [
                ["To create and run your workspace and your subscription.",
                 "To verify your email address and mobile number, and to send invoices, receipts and service messages.",
                 "To keep the service secure, prevent abuse and fix problems.",
                 "To understand how the website is used, where you have allowed it."],
                "We do not sell personal information.",
            ]),
            ("Who we share it with", [
                "We do not sell personal data, and we do not disclose it to third parties for their own purposes.",
                "To deliver the service we route data through infrastructure and communication providers that act on our behalf: hosting infrastructure, an AI model endpoint, SMS and email delivery, a WhatsApp messaging channel, Google reCAPTCHA for bot protection and Google Tag Manager for tag management. Each is used as a delivery channel for one specific function. It receives only the data that function needs for the request in hand (data minimisation), and the connection to it is encrypted in transit (HTTPS/TLS, and SMTP over SSL for email).",
                "Card and payment details are entered by you directly in Paddle's checkout and are processed by Paddle as the merchant of record, under its own terms. They do not pass through our servers.",
                "We may disclose information where the law requires it.",
            ]),
            ("Your workspace data", [
                "Each company works in its own private workspace. Your records stay inside your company, and other customers cannot open them. You decide who in your team can see what.",
                "AI features send the text you ask them to work on to the AI provider configured for your workspace. They are optional and billed separately.",
            ]),
            ("Cookies and analytics", [
                "The website uses cookies and similar technology for sign-in, language and theme choices and, where you agree or where the law does not require consent, analytics and advertising measurement. You can refuse non-essential cookies in the banner and in your browser.",
            ]),
            ("How long we keep it", [
                "We keep account and billing records while your subscription is active and for as long afterwards as the law or a dispute requires. Workspace data is deleted or returned to you on request after your subscription ends, unless the law says we must keep part of it.",
            ]),
            ("Your choices", [
                f"You can ask to see, correct, export or delete your personal information, or object to how it is used, by writing to {CONTACT_EMAIL}. We reply within a reasonable time and may need to confirm who you are first.",
            ]),
            ("Changes and contact", [
                f"We will update this page when our practices change. Questions: {CONTACT_EMAIL}, {COMPANY}, {ADDRESS}.",
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
