"""Bangla (Bangladesh) text for the public marketing pages, under ``/bn/...``.

English is the source. ``translate`` looks a string up here and returns it unchanged when there is no
entry, so a page is never blank: whatever is not translated yet simply stays English. Product and brand
names (ReckonERP, Reckon AI, module names) are kept in Latin script, as Bangladeshi business sites do.
Long reading material (blog posts, FAQ answers, module detail lists) is intentionally left in English.
"""

from __future__ import annotations

import re

LANG = "bn"
PREFIX = "/bn"
# Pages that have a Bangla twin. Blog, invoices and the signup form are handled elsewhere.
ROOTS = ("features", "modules", "industries", "pricing", "faq", "integrations")

BN = {
    # --- navigation and chrome ---
    "Skip to content": "মূল অংশে যান",
    "ReckonERP": "ReckonERP",
    "ReckonERP home": "ReckonERP হোম",
    "ReckonERP logo": "ReckonERP লোগো",
    "Main": "প্রধান মেনু",
    "Home": "হোম",
    "Features": "ফিচার",
    "Modules": "মডিউল",
    "Industries": "ইন্ডাস্ট্রি",
    "Pricing": "মূল্য",
    "Integrations": "ইন্টিগ্রেশন",
    "Blog": "ব্লগ",
    "FAQ": "সাধারণ জিজ্ঞাসা",
    "All features": "সব ফিচার",
    "All modules": "সব মডিউল",
    "Log in": "লগইন",
    "Sign up": "সাইন আপ",
    "Start free": "ফ্রি শুরু করুন",
    "Language": "ভাষা",
    "English": "English",
    "Theme": "থিম",
    "Dark": "ডার্ক",
    "Light": "লাইট",
    "Currency": "মুদ্রা",
    "Breadcrumb": "পথ",
    "Summary": "সারসংক্ষেপ",
    # --- footer and company ---
    "Cloud ERP with built-in AI for growing businesses, built on ERPNext.": "ক্রমবর্ধমান ব্যবসার জন্য বিল্ট-ইন AI সহ ক্লাউড ইআরপি, ERPNext-এর ওপর নির্মিত।",
    "Company": "কোম্পানি",
    "About us": "আমাদের সম্পর্কে",
    "Popular solutions": "জনপ্রিয় সমাধান",
    "Cloud ERP software in Bangladesh": "বাংলাদেশে ক্লাউড ইআরপি সফটওয়্যার",
    "ERP software by industry": "ইন্ডাস্ট্রিভিত্তিক ইআরপি সফটওয়্যার",
    "ERP and AI automation guides": "ইআরপি ও AI অটোমেশন গাইড",
    "AI agent development and automation": "AI এজেন্ট ডেভেলপমেন্ট ও অটোমেশন",
    "Website:": "ওয়েবসাইট:",
    "Mail Address:": "ইমেইল:",
    "Email:": "ইমেইল:",
    "WhatsApp / Cell:": "হোয়াটসঅ্যাপ / মোবাইল:",
    "WhatsApp:": "হোয়াটসঅ্যাপ:",
    "Address:": "ঠিকানা:",
    "Social profile:": "সোশ্যাল প্রোফাইল:",
    "ReckonERP by Reckon Technologies Ltd.": "ReckonERP — Reckon Technologies Ltd.",
    "Our services": "আমাদের সেবা",
    "We solve it best with our expertise": "আমাদের অভিজ্ঞতা দিয়ে আমরা সমাধান করি",
    "Ask about these on WhatsApp": "এ বিষয়ে হোয়াটসঅ্যাপে জিজ্ঞাসা করুন",
    "Ask us for a quote on WhatsApp": "কোটেশনের জন্য হোয়াটসঅ্যাপে জানান",
    "Ask us on WhatsApp": "হোয়াটসঅ্যাপে জিজ্ঞাসা করুন",
    "More from Reckon, on request": "Reckon-এর আরও সমাধান, অনুরোধে",
    # --- chat and cookie notice ---
    "Chat": "চ্যাট",
    "Chat with ReckonERP": "ReckonERP-এর সাথে চ্যাট করুন",
    "Ask about modules, pricing, deployment or AI. We reply on WhatsApp.": "মডিউল, মূল্য, ডেপ্লয়মেন্ট বা AI সম্পর্কে জিজ্ঞাসা করুন। আমরা হোয়াটসঅ্যাপে উত্তর দিই।",
    "Your name": "আপনার নাম",
    "Message": "বার্তা",
    "Continue on WhatsApp": "হোয়াটসঅ্যাপে চালিয়ে যান",
    "Nothing is sent until you press the button; WhatsApp then opens with your message ready. Prefer email?": "বোতাম চাপার আগে কিছুই পাঠানো হয় না; তখন হোয়াটসঅ্যাপে আপনার বার্তা তৈরি অবস্থায় খুলবে। ইমেইল পছন্দ করলে:",
    "Cookie notice": "কুকি বিজ্ঞপ্তি",
    "We use cookies for analytics and advertising measurement. Accept to allow them, or decline to browse without them.": "আমরা অ্যানালিটিক্স ও বিজ্ঞাপন পরিমাপের জন্য কুকি ব্যবহার করি। অনুমতি দিতে গ্রহণ করুন, অথবা কুকি ছাড়া ব্রাউজ করতে প্রত্যাখ্যান করুন।",
    "Accept": "গ্রহণ করুন",
    "Decline": "প্রত্যাখ্যান",
    # --- common words ---
    "AI": "AI",
    "ERP": "ইআরপি",
    "CRM": "সিআরএম",
    "Automation": "অটোমেশন",
    "Read": "পড়ুন",
    "Learn more": "আরও জানুন",
    "See": "দেখুন:",
    "about": "সম্পর্কে",
    "About": "বিস্তারিত:",
    "Choose": "বেছে নিন:",
    "Start here": "এখান থেকে শুরু করুন",
    "Verify": "যাচাই",
    "Work": "কাজ শুরু",
    "Included": "অন্তর্ভুক্ত",
    "Not included": "অন্তর্ভুক্ত নয়",
    "Feature": "ফিচার",
    "Industry": "ইন্ডাস্ট্রি",
    "ERP module": "ইআরপি মডিউল",
    "In short": "সংক্ষেপে",
    "Pause scrolling": "স্ক্রলিং থামান",
    "Play scrolling": "স্ক্রলিং চালু করুন",
    "&copy;": "&copy;",
    "&nbsp;&middot;": "&nbsp;&middot;",
    "{n}-day free trial": "{n} দিনের ফ্রি ট্রায়াল",
    "Choose {name}": "{name} বেছে নিন",
    # --- home page ---
    "Your ERP, now with": "আপনার ইআরপি, এখন সাথে",
    "an AI that reads every ledger.": "প্রতিটি খতিয়ান পড়তে পারা AI।",
    "Invoices, orders, stock and people &mdash; one calm, glass-clear workspace.": "ইনভয়েস, অর্ডার, স্টক ও মানুষ &mdash; একটি পরিচ্ছন্ন, স্বচ্ছ ওয়ার্কস্পেসে।",
    "AI built into ERP, CRM and automation": "ইআরপি, সিআরএম ও অটোমেশনে বিল্ট-ইন AI",
    "Private workspace for every company, in Bangla or English": "প্রতিটি কোম্পানির জন্য আলাদা ওয়ার্কস্পেস, বাংলা বা ইংরেজিতে",
    "Start online, or deploy on a dedicated cloud or on-premises": "অনলাইনে শুরু করুন, অথবা ডেডিকেটেড ক্লাউড বা নিজস্ব সার্ভারে চালান",
    "Explore modules": "মডিউল দেখুন",
    "ReckonERP accounts dashboard, campaign studio, integrations and AI assistant screens": "ReckonERP অ্যাকাউন্টস ড্যাশবোর্ড, ক্যাম্পেইন স্টুডিও, ইন্টিগ্রেশন ও AI অ্যাসিস্ট্যান্টের স্ক্রিন",
    "Reckon AI inside every module": "প্রতিটি মডিউলে Reckon AI",
    "AI that works on your own records, with a person in charge": "আপনার নিজের রেকর্ডে কাজ করা AI, নিয়ন্ত্রণে থাকেন মানুষ",
    "Meet Reckon AI": "Reckon AI সম্পর্কে জানুন",
    "AI assistant drafting a reply that waits for a person to approve": "AI অ্যাসিস্ট্যান্ট উত্তরের খসড়া তৈরি করছে, মানুষের অনুমোদনের অপেক্ষায়",
    "ERP, CRM, automation and AI working together": "ইআরপি, সিআরএম, অটোমেশন ও AI একসাথে",
    "One platform instead of four tools that never quite talk to each other.": "চারটি আলাদা টুলের বদলে একটি প্ল্যাটফর্ম, যেখানে সবকিছু একসাথে কাজ করে।",
    "Connects the channels your customers use": "আপনার গ্রাহকদের ব্যবহৃত চ্যানেলগুলোর সাথে যুক্ত",
    "WhatsApp, social, SMS, voice, email and AI services.": "হোয়াটসঅ্যাপ, সোশ্যাল, এসএমএস, ভয়েস, ইমেইল ও AI সার্ভিস।",
    "See every integration": "সব ইন্টিগ্রেশন দেখুন",
    "ERP modules": "ইআরপি মডিউল",
    "Subscribe to one module or several. Each runs in your own company workspace.": "একটি বা একাধিক মডিউলে সাবস্ক্রাইব করুন। প্রতিটি আপনার নিজস্ব কোম্পানি ওয়ার্কস্পেসে চলে।",
    "From the blog": "ব্লগ থেকে",
    "Guides, tutorials and weekly updates.": "গাইড, টিউটোরিয়াল ও সাপ্তাহিক আপডেট।",
    "All articles": "সব লেখা",
    "Deploy it your way": "আপনার মতো করে ডেপ্লয় করুন",
    "Start on the shared cloud today. Move to a dedicated cloud or your own servers when you need to.": "আজই শেয়ার্ড ক্লাউডে শুরু করুন। প্রয়োজন হলে ডেডিকেটেড ক্লাউড বা নিজস্ব সার্ভারে যান।",
    "Customisation, implementation, data migration, AI and integration tools are additional.": "কাস্টমাইজেশন, ইমপ্লিমেন্টেশন, ডাটা মাইগ্রেশন, AI ও ইন্টিগ্রেশন টুল আলাদা চার্জযোগ্য।",
    "Multi-currency, multi-language and easy to customise for enterprise packages.": "মাল্টি-কারেন্সি, মাল্টি-ল্যাঙ্গুয়েজ এবং এন্টারপ্রাইজ প্যাকেজের জন্য সহজে কাস্টমাইজযোগ্য।",
    "What the platform gives you": "প্ল্যাটফর্ম থেকে আপনি যা পাবেন",
    "Each feature has its own page.": "প্রতিটি ফিচারের আলাদা পেজ আছে।",
    "Start in three steps": "তিন ধাপে শুরু করুন",
    "Pick a module and a plan that fits your company.": "আপনার কোম্পানির উপযোগী একটি মডিউল ও প্ল্যান বেছে নিন।",
    "Confirm your email and phone number so only real owners get a workspace.": "ইমেইল ও ফোন নম্বর যাচাই করুন, যাতে শুধু প্রকৃত মালিকরাই ওয়ার্কস্পেস পান।",
    "Your workspace is set up with starting data and opens in your browser.": "আপনার ওয়ার্কস্পেস শুরুর ডাটাসহ প্রস্তুত হয়ে ব্রাউজারে খুলবে।",
    "Frequently asked questions": "সচরাচর জিজ্ঞাসা",
    "Ready to run on ReckonERP?": "ReckonERP-এ ব্যবসা চালাতে প্রস্তুত?",
    "Create your company workspace in minutes.": "কয়েক মিনিটে আপনার কোম্পানির ওয়ার্কস্পেস তৈরি করুন।",
    # --- pricing, modules, features, industries, faq, integrations ---
    "Each module is its own subscription with its own plan, so you pay only for what you use. Prices, billing periods and trial days are exactly what you will see at signup.": "প্রতিটি মডিউল আলাদা সাবস্ক্রিপশন ও আলাদা প্ল্যানে, তাই শুধু যা ব্যবহার করেন তারই মূল্য দেন। মূল্য, বিলিং সময়কাল ও ট্রায়ালের দিন ঠিক সাইন আপের সময় যা দেখবেন তা-ই।",
    "Plans are shown at signup.": "প্ল্যান সাইন আপের সময় দেখানো হয়।",
    "Plans are shown when you sign up.": "প্ল্যান সাইন আপের সময় দেখানো হয়।",
    "plans and pricing": "প্ল্যান ও মূল্য",
    "all plans": "সব প্ল্যান",
    ". Implementation, training, customisation and on-site support are quoted separately.": "। ইমপ্লিমেন্টেশন, প্রশিক্ষণ, কাস্টমাইজেশন ও অন-সাইট সাপোর্ট আলাদাভাবে কোট করা হয়।",
    "Implementation, data migration, training, customisation, on-site support, and AI and integration usage are quoted separately.": "ইমপ্লিমেন্টেশন, ডাটা মাইগ্রেশন, প্রশিক্ষণ, কাস্টমাইজেশন, অন-সাইট সাপোর্ট এবং AI ও ইন্টিগ্রেশন ব্যবহার আলাদাভাবে কোট করা হয়।",
    "Subscribe online. Your invoice arrives by email with a PDF, and a link by SMS.": "অনলাইনে সাবস্ক্রাইব করুন। আপনার ইনভয়েস পিডিএফসহ ইমেইলে এবং লিংক এসএমএসে পৌঁছাবে।",
    "Every module has its own plans, roles and starting data. Subscribe to one or several.": "প্রতিটি মডিউলের নিজস্ব প্ল্যান, রোল ও শুরুর ডাটা আছে। একটি বা একাধিক সাবস্ক্রাইব করুন।",
    "Module details": "মডিউলের বিবরণ",
    "What is inside": "ভেতরে যা আছে:",
    "Who uses": "কারা ব্যবহার করেন:",
    "Built for": "যাদের জন্য:",
    "What you can do": "আপনি যা করতে পারবেন",
    "Other modules": "অন্যান্য মডিউল",
    "More features": "আরও ফিচার",
    "One page for each thing the platform does, from signup to integrations.": "সাইন আপ থেকে ইন্টিগ্রেশন পর্যন্ত, প্ল্যাটফর্মের প্রতিটি কাজের জন্য আলাদা পেজ।",
    "The same cloud ERP, with the parts each sector needs. Standard modules are ready now; sector-specific steps are set up with you.": "একই ক্লাউড ইআরপি, প্রতিটি খাতের প্রয়োজনীয় অংশসহ। স্ট্যান্ডার্ড মডিউল এখনই প্রস্তুত; খাতভিত্তিক ধাপগুলো আপনার সাথে মিলে সাজানো হয়।",
    "Ready in the standard modules": "স্ট্যান্ডার্ড মডিউলে প্রস্তুত",
    "Set up for you on request": "অনুরোধে আপনার জন্য সাজানো হয়",
    "These parts are customisation after a requirement analysis, quoted separately.": "এই অংশগুলো চাহিদা বিশ্লেষণের পর কাস্টমাইজেশনের আওতায়, আলাদা কোটেশনে।",
    "Modules that fit": "উপযোগী মডিউল",
    "Other industries": "অন্যান্য ইন্ডাস্ট্রি",
    "Pricing, deployment, implementation, licences, AI and support, answered in one place.": "মূল্য, ডেপ্লয়মেন্ট, ইমপ্লিমেন্টেশন, লাইসেন্স, AI ও সাপোর্ট — সব উত্তর এক জায়গায়।",
    "Read the FAQ": "সাধারণ জিজ্ঞাসা পড়ুন",
    "Messaging, social, SMS, voice, email, AI and research services connect from one Integrations page, and each business keeps its own keys.": "মেসেজিং, সোশ্যাল, এসএমএস, ভয়েস, ইমেইল, AI ও রিসার্চ সার্ভিস এক ইন্টিগ্রেশন পেজ থেকে যুক্ত হয়, আর প্রতিটি ব্যবসা নিজস্ব কী রাখে।",
    "Guides for": "গাইড:",
    "Tell us about your business": "আপনার ব্যবসা সম্পর্কে আমাদের জানান",
    "Start online or message us for a requirement analysis.": "অনলাইনে শুরু করুন অথবা চাহিদা বিশ্লেষণের জন্য আমাদের বার্তা দিন।",
    "Pick a module and a plan, then sign up.": "মডিউল ও প্ল্যান বেছে সাইন আপ করুন।",
    "Pick a plan and start": "প্ল্যান বেছে শুরু করুন",
    "Sign up, verify, and you will receive your invoice by email and SMS.": "সাইন আপ ও যাচাই করুন, ইনভয়েস ইমেইল ও এসএমএসে পাবেন।",
    "Sign up for": "সাইন আপ করুন:",
    "Pricing questions": "মূল্য নিয়ে প্রশ্ন",
    "Start now": "এখনই শুরু করুন",
    "Try it with your company": "আপনার কোম্পানিতে চালিয়ে দেখুন",
    "Sign up and your workspace is ready after verification.": "সাইন আপ করুন, যাচাইয়ের পর আপনার ওয়ার্কস্পেস প্রস্তুত।",
    # --- feature titles and summaries ---
    "Self-serve signup": "নিজে নিজে সাইন আপ",
    "Create a verified company workspace on your own, in minutes.": "কয়েক মিনিটে নিজেই যাচাইকৃত কোম্পানি ওয়ার্কস্পেস তৈরি করুন।",
    "Separate company workspaces": "আলাদা কোম্পানি ওয়ার্কস্পেস",
    "Every customer works inside its own Company, apart from all others.": "প্রতিটি গ্রাহক নিজস্ব কোম্পানির ভেতরে কাজ করেন, অন্যদের থেকে সম্পূর্ণ আলাদা।",
    "Plans, trials and billing": "প্ল্যান, ট্রায়াল ও বিলিং",
    "Plans per module, trial days, billing cycles and verified payments.": "মডিউলভিত্তিক প্ল্যান, ট্রায়ালের দিন, বিলিং সাইকেল ও যাচাইকৃত পেমেন্ট।",
    "Modular ERP": "মডুলার ইআরপি",
    "Start with the module you need and add others on the same platform.": "প্রয়োজনীয় মডিউল দিয়ে শুরু করুন, একই প্ল্যাটফর্মে পরে অন্যগুলো যোগ করুন।",
    "Bangla and English": "বাংলা ও ইংরেজি",
    "Signup in Bangla or English, with Bangla-first workflows for field teams.": "বাংলা বা ইংরেজিতে সাইন আপ, মাঠ পর্যায়ের দলের জন্য বাংলা-প্রথম ওয়ার্কফ্লো।",
    "Roles and security": "রোল ও নিরাপত্তা",
    "Role-based access, verified owners and guarded sign-in.": "রোলভিত্তিক অ্যাক্সেস, যাচাইকৃত মালিক ও সুরক্ষিত সাইন-ইন।",
    "Integrations and channels": "ইন্টিগ্রেশন ও চ্যানেল",
    "WhatsApp, social, SMS, voice and email channels in one place.": "হোয়াটসঅ্যাপ, সোশ্যাল, এসএমএস, ভয়েস ও ইমেইল চ্যানেল এক জায়গায়।",
    "Reckon AI assistant": "Reckon AI অ্যাসিস্ট্যান্ট",
    "Ask questions about your own records and approve the actions it suggests.": "আপনার নিজের রেকর্ড নিয়ে প্রশ্ন করুন এবং প্রস্তাবিত কাজ অনুমোদন করুন।",
    "Field sales visits": "মাঠ পর্যায়ের বিক্রয় ভিজিট",
    "Schedule customer visits, check in with GPS and keep a history of every visit.": "গ্রাহক ভিজিটের সময়সূচি করুন, জিপিএসে চেক-ইন করুন এবং প্রতিটি ভিজিটের ইতিহাস রাখুন।",
    "Custom AI agents, assistants and workflow automation, built around your ERP and CRM data.": "আপনার ইআরপি ও সিআরএম ডাটাকে ঘিরে তৈরি কাস্টম AI এজেন্ট, অ্যাসিস্ট্যান্ট ও ওয়ার্কফ্লো অটোমেশন।",
    "AI-assisted selling": "AI-সহায়তায় বিক্রয়",
    "Find, research and qualify customers, with a person approving every message.": "গ্রাহক খুঁজুন, যাচাই করুন ও মূল্যায়ন করুন, প্রতিটি বার্তা অনুমোদন করেন একজন মানুষ।",
    # --- services, deployment, showcase, AI points ---
    "Cloud ERP modules": "ক্লাউড ইআরপি মডিউল",
    "Distribution, Accounts, HRMS, CRM and Sales AI, each in a private company workspace.": "ডিস্ট্রিবিউশন, অ্যাকাউন্টস, এইচআরএমএস, সিআরএম ও সেলস AI — প্রতিটি আলাদা কোম্পানি ওয়ার্কস্পেসে।",
    "Multi-currency": "মাল্টি-কারেন্সি",
    "Quote, invoice and keep books in more than one currency, with plans priced in BDT, USD, EUR or INR.": "একাধিক মুদ্রায় কোটেশন, ইনভয়েস ও হিসাব রাখুন; প্ল্যানের মূল্য BDT, USD, EUR বা INR-এ।",
    "Multi-language": "মাল্টি-ল্যাঙ্গুয়েজ",
    "Screens in English and Bangla today, and more languages through translation on request.": "আজ ইংরেজি ও বাংলা স্ক্রিন, অনুরোধে অনুবাদের মাধ্যমে আরও ভাষা।",
    "Easy to customise": "সহজে কাস্টমাইজযোগ্য",
    "The enterprise package shapes fields, workflows, reports, print formats and integrations to how you work.": "এন্টারপ্রাইজ প্যাকেজে ফিল্ড, ওয়ার্কফ্লো, রিপোর্ট, প্রিন্ট ফরম্যাট ও ইন্টিগ্রেশন আপনার কাজের ধরন অনুযায়ী সাজানো হয়।",
    "Dedicated cloud or on-premises": "ডেডিকেটেড ক্লাউড বা অন-প্রিমিসেস",
    "Your own server or ours, with your release schedule, backups and access rules.": "আপনার নিজের বা আমাদের সার্ভার, আপনার রিলিজ সময়সূচি, ব্যাকআপ ও অ্যাক্সেস নিয়মসহ।",
    "Reckon AI and integrations": "Reckon AI ও ইন্টিগ্রেশন",
    "AI that works on your own records with approval, plus WhatsApp, SMS and email channels. Usage is billed separately.": "অনুমোদনসহ আপনার নিজের রেকর্ডে কাজ করা AI, সাথে হোয়াটসঅ্যাপ, এসএমএস ও ইমেইল চ্যানেল। ব্যবহারের চার্জ আলাদা।",
    "Implementation and training": "ইমপ্লিমেন্টেশন ও প্রশিক্ষণ",
    "Requirement analysis, data migration, setup and team training, quoted for your business.": "চাহিদা বিশ্লেষণ, ডাটা মাইগ্রেশন, সেটআপ ও দলের প্রশিক্ষণ, আপনার ব্যবসা অনুযায়ী কোটেড।",
    "Support": "সাপোর্ট",
    "Help by email and WhatsApp, with faster or dedicated support available on request.": "ইমেইল ও হোয়াটসঅ্যাপে সহায়তা; অনুরোধে দ্রুত বা ডেডিকেটেড সাপোর্ট।",
    "Reckon AI reads and summarises invoices, orders, stock and customer records so people find answers faster": "Reckon AI ইনভয়েস, অর্ডার, স্টক ও গ্রাহকের রেকর্ড পড়ে সংক্ষেপে জানায়, ফলে উত্তর দ্রুত মেলে",
    "Researches leads from their own websites and keeps the evidence next to every claim": "লিডের নিজস্ব ওয়েবসাইট থেকে তথ্য খুঁজে প্রতিটি দাবির পাশে প্রমাণ রাখে",
    "Drafts replies and follow-ups; a person approves before anything is sent": "উত্তর ও ফলো-আপের খসড়া করে; কিছু পাঠানোর আগে একজন মানুষ অনুমোদন দেন",
    "Scores leads with fixed rules you can read, then syncs them to your CRM": "পড়া যায় এমন নির্দিষ্ট নিয়মে লিড স্কোর করে, তারপর আপনার সিআরএমে সিঙ্ক করে",
    "AI and integration tools are billed separately from the module subscription.": "AI ও ইন্টিগ্রেশন টুলের চার্জ মডিউল সাবস্ক্রিপশন থেকে আলাদা।",
    "Shared cloud": "শেয়ার্ড ক্লাউড",
    "Sign up online from anywhere and start in your own private company workspace. Fastest way to begin.": "যেকোনো জায়গা থেকে অনলাইনে সাইন আপ করে নিজস্ব কোম্পানি ওয়ার্কস্পেসে শুরু করুন। শুরু করার দ্রুততম উপায়।",
    "Dedicated cloud": "ডেডিকেটেড ক্লাউড",
    "Your own cloud server for isolation and your own release schedule. Customisation and set-up are quoted separately.": "আলাদা সুরক্ষা ও নিজস্ব রিলিজ সময়সূচির জন্য আপনার নিজস্ব ক্লাউড সার্ভার। কাস্টমাইজেশন ও সেটআপ আলাদা কোটেশনে।",
    "On-premises": "অন-প্রিমিসেস",
    "Installed on your own infrastructure with customisation and support. Quoted to your requirements.": "আপনার নিজস্ব অবকাঠামোতে কাস্টমাইজেশন ও সাপোর্টসহ ইনস্টল। চাহিদা অনুযায়ী কোটেড।",
    "Sales, stock, collections and books for your company, in one place.": "আপনার কোম্পানির বিক্রয়, স্টক, আদায় ও হিসাব এক জায়গায়।",
    "Leads and customers move through a pipeline your whole team can see.": "লিড ও গ্রাহক এমন পাইপলাইনে এগোয় যা পুরো দল দেখতে পায়।",
    "Triggers hand work to steps that draft, route and sync for you.": "ট্রিগার কাজ তুলে দেয় এমন ধাপে যা খসড়া, রাউট ও সিঙ্ক করে।",
    "AI assistance": "AI সহায়তা",
    "AI drafts and researches; a person approves before anything is sent.": "AI খসড়া ও গবেষণা করে; কিছু পাঠানোর আগে একজন মানুষ অনুমোদন দেন।",
    # --- module taglines ---
    "Routes, deliveries, collections and stock for FMCG distributors.": "এফএমসিজি ডিস্ট্রিবিউটরদের জন্য রুট, ডেলিভারি, আদায় ও স্টক।",
    "Invoices, bills, stock and Tally-style books for a small business.": "ছোট ব্যবসার জন্য ইনভয়েস, বিল, স্টক ও ট্যালি-ধাঁচের হিসাব।",
    "Find, research and follow up B2B customers, with approval before any send.": "বিটুবি গ্রাহক খুঁজুন, যাচাই করুন ও ফলো-আপ করুন; পাঠানোর আগে অনুমোদনসহ।",
    "Employees, attendance, leave and payroll in one private workspace per company.": "প্রতি কোম্পানির আলাদা ওয়ার্কস্পেসে কর্মী, উপস্থিতি, ছুটি ও বেতন।",
    "Leads, deals and organizations for sales teams, in a private workspace.": "বিক্রয় দলের জন্য লিড, ডিল ও প্রতিষ্ঠান, আলাদা ওয়ার্কস্পেসে।",
    "Distribution management software in Bangladesh": "বাংলাদেশে ডিস্ট্রিবিউশন ম্যানেজমেন্ট সফটওয়্যার",
    "Accounting and inventory software in Bangladesh": "বাংলাদেশে অ্যাকাউন্টিং ও ইনভেন্টরি সফটওয়্যার",
    "AI sales agent for B2B lead generation": "বিটুবি লিড জেনারেশনের জন্য AI সেলস এজেন্ট",
    "HR and payroll software in Bangladesh": "বাংলাদেশে এইচআর ও পে-রোল সফটওয়্যার",
    "CRM software in Bangladesh for leads and deals": "বাংলাদেশে লিড ও ডিলের জন্য সিআরএম সফটওয়্যার",
    # --- industries ---
    "Garments and RMG": "গার্মেন্টস ও আরএমজি",
    "Textile": "টেক্সটাইল",
    "Pharmaceutical": "ফার্মাসিউটিক্যাল",
    "Healthcare": "স্বাস্থ্যসেবা",
    "Manufacturing": "ম্যানুফ্যাকচারিং",
    "Trading and wholesale": "ট্রেডিং ও পাইকারি",
    "FMCG distribution": "এফএমসিজি ডিস্ট্রিবিউশন",
    "Garments ERP software in Bangladesh": "বাংলাদেশে গার্মেন্টস ইআরপি সফটওয়্যার",
    "Textile ERP software in Bangladesh": "বাংলাদেশে টেক্সটাইল ইআরপি সফটওয়্যার",
    "Pharmaceutical ERP software in Bangladesh": "বাংলাদেশে ফার্মাসিউটিক্যাল ইআরপি সফটওয়্যার",
    "Healthcare ERP software in Bangladesh": "বাংলাদেশে হেলথকেয়ার ইআরপি সফটওয়্যার",
    "Manufacturing ERP software in Bangladesh": "বাংলাদেশে ম্যানুফ্যাকচারিং ইআরপি সফটওয়্যার",
    "Trading business ERP software in Bangladesh": "বাংলাদেশে ট্রেডিং ব্যবসার ইআরপি সফটওয়্যার",
    "FMCG distribution software in Bangladesh": "বাংলাদেশে এফএমসিজি ডিস্ট্রিবিউশন সফটওয়্যার",
    # --- page titles, descriptions and headings ---
    "ReckonERP: Cloud ERP, CRM and AI Agents in Bangladesh": "ReckonERP: বাংলাদেশে ক্লাউড ইআরপি, সিআরএম ও AI এজেন্ট",
    "Cloud ERP, CRM, HR and payroll, distribution management and AI agent automation for growing businesses in Bangladesh and worldwide. Start online today.": "বাংলাদেশ ও বিশ্বের ক্রমবর্ধমান ব্যবসার জন্য ক্লাউড ইআরপি, সিআরএম, এইচআর ও পে-রোল, ডিস্ট্রিবিউশন ম্যানেজমেন্ট এবং AI এজেন্ট অটোমেশন। আজই অনলাইনে শুরু করুন।",
    "ERP, CRM and AI features for Bangladesh | ReckonERP": "বাংলাদেশের জন্য ইআরপি, সিআরএম ও AI ফিচার | ReckonERP",
    "Every ReckonERP feature: cloud ERP signup, separate company workspaces, plans and billing, Bangla support, AI assistant, CRM and integrations.": "ReckonERP-এর সব ফিচার: ক্লাউড ইআরপি সাইন আপ, আলাদা কোম্পানি ওয়ার্কস্পেস, প্ল্যান ও বিলিং, বাংলা সাপোর্ট, AI অ্যাসিস্ট্যান্ট, সিআরএম ও ইন্টিগ্রেশন।",
    "Everything the ReckonERP platform does": "ReckonERP প্ল্যাটফর্ম যা যা করে",
    "ERP modules in Bangladesh: Accounts, CRM, HRMS, AI": "বাংলাদেশে ইআরপি মডিউল: অ্যাকাউন্টস, সিআরএম, এইচআরএমএস, AI",
    "Cloud ERP modules you can subscribe to: distribution, accounting, CRM, HR and payroll and a sales AI agent, each with its own plans and private workspace.": "সাবস্ক্রাইব করার মতো ক্লাউড ইআরপি মডিউল: ডিস্ট্রিবিউশন, অ্যাকাউন্টিং, সিআরএম, এইচআর ও পে-রোল এবং সেলস AI এজেন্ট — প্রতিটির নিজস্ব প্ল্যান ও আলাদা ওয়ার্কস্পেস।",
    "Choose the modules your business needs": "আপনার ব্যবসার প্রয়োজনীয় মডিউল বেছে নিন",
    "Cloud ERP pricing in Bangladesh: plans per module": "বাংলাদেশে ক্লাউড ইআরপি মূল্য: মডিউলভিত্তিক প্ল্যান",
    "ERP, CRM, HR and payroll and accounting subscription plans in BDT, USD, EUR or INR, with trial days and what each includes. Sign up online in minutes.": "ইআরপি, সিআরএম, এইচআর ও পে-রোল এবং অ্যাকাউন্টিং সাবস্ক্রিপশন প্ল্যান BDT, USD, EUR বা INR-এ, ট্রায়ালের দিন ও অন্তর্ভুক্ত বিষয়সহ। কয়েক মিনিটে অনলাইনে সাইন আপ করুন।",
    "ReckonERP plans and pricing": "ReckonERP প্ল্যান ও মূল্য",
    "ERP FAQ: pricing, deployment, AI and support | ReckonERP": "ইআরপি সাধারণ জিজ্ঞাসা: মূল্য, ডেপ্লয়মেন্ট, AI ও সাপোর্ট | ReckonERP",
    "Answers about ReckonERP pricing, implementation cost, dedicated cloud and on-premises deployment, licences, AI and integration charges, and support.": "ReckonERP-এর মূল্য, ইমপ্লিমেন্টেশন খরচ, ডেডিকেটেড ক্লাউড ও অন-প্রিমিসেস ডেপ্লয়মেন্ট, লাইসেন্স, AI ও ইন্টিগ্রেশন চার্জ এবং সাপোর্ট সম্পর্কে উত্তর।",
    "Frequently asked questions about ReckonERP": "ReckonERP সম্পর্কে সচরাচর জিজ্ঞাসা",
    "Business automation and AI integration | ReckonERP": "ব্যবসায়িক অটোমেশন ও AI ইন্টিগ্রেশন | ReckonERP",
    "Connect WhatsApp, Messenger, Instagram, LinkedIn, SMS gateways, email services, Google and AI providers to your ERP and CRM for business automation.": "ব্যবসায়িক অটোমেশনের জন্য আপনার ইআরপি ও সিআরএমের সাথে হোয়াটসঅ্যাপ, মেসেঞ্জার, ইনস্টাগ্রাম, লিংকডইন, এসএমএস গেটওয়ে, ইমেইল সার্ভিস, গুগল ও AI প্রোভাইডার যুক্ত করুন।",
    "Channels and services you can connect": "যেসব চ্যানেল ও সার্ভিস যুক্ত করা যায়",
    "ERP software by industry in Bangladesh | ReckonERP": "বাংলাদেশে ইন্ডাস্ট্রিভিত্তিক ইআরপি সফটওয়্যার | ReckonERP",
    "Cloud ERP for garments, textile, pharmaceutical, healthcare, manufacturing, trading and FMCG distribution businesses in Bangladesh.": "বাংলাদেশের গার্মেন্টস, টেক্সটাইল, ফার্মাসিউটিক্যাল, স্বাস্থ্যসেবা, ম্যানুফ্যাকচারিং, ট্রেডিং ও এফএমসিজি ডিস্ট্রিবিউশন ব্যবসার জন্য ক্লাউড ইআরপি।",
    "ERP software for your industry": "আপনার ইন্ডাস্ট্রির জন্য ইআরপি সফটওয়্যার",
}

# "Prefix ... | suffix" titles and "Questions about X" headings, matched when there is no exact entry.
SUFFIXES = {
    " | ReckonERP": " | ReckonERP",
    " | ReckonERP features": " | ReckonERP ফিচার",
}
PREFIXES = {
    "Questions about ERP for ": ("", "-এর জন্য ইআরপি নিয়ে প্রশ্ন"),
    "Questions about ": ("", " সম্পর্কে প্রশ্ন"),
}


CYCLES = {"month": "প্রতি মাসে", "quarter": "প্রতি ৩ মাসে", "6 months": "প্রতি ৬ মাসে", "year": "প্রতি বছরে"}
PRICE = re.compile(r"^(?P<price>\S+) per (?P<cycle>month|quarter|6 months|year)$")


def translate(text):
    """The Bangla for ``text``, or ``text`` itself when there is none."""
    if not isinstance(text, str) or not text:
        return text
    hit = BN.get(text)
    if hit is not None:
        return hit
    price = PRICE.match(text)
    if price:
        return f"{CYCLES[price.group('cycle')]} {price.group('price')}"
    for tail, bn_tail in SUFFIXES.items():
        if text.endswith(tail):
            head = text[: -len(tail)]
            if head in BN:
                return BN[head] + bn_tail
    for head, (lead, tail) in PREFIXES.items():
        if text.startswith(head) and len(text) > len(head):
            return lead + text[len(head):] + tail
    return text


def deep(value):
    """Translate every string inside nested dicts, lists and tuples; other values pass through."""
    if isinstance(value, str):
        return translate(value)
    if isinstance(value, dict):
        return {key: deep(item) if key not in ("url", "slug", "key", "path", "icon", "src", "image") else item for key, item in value.items()}
    if isinstance(value, list):
        return [deep(item) for item in value]
    if isinstance(value, tuple):
        return tuple(deep(item) for item in value)
    return value


def is_translatable(path: str) -> bool:
    """True for paths that have a Bangla twin under ``/bn``."""
    path = (path or "").split("?")[0].split("#")[0]
    if path in ("", "/"):
        return True
    parts = [p for p in path.split("/") if p]
    return bool(parts) and parts[0] in ROOTS


def bn_path(path: str) -> str:
    """``/pricing`` -> ``/bn/pricing`` and ``/`` -> ``/bn``; anything without a twin is returned unchanged."""
    if not is_translatable(path):
        return path
    clean = (path or "/").split("#")[0]
    if clean in ("", "/"):
        return PREFIX
    return PREFIX + clean


def make_url_filter(lang: str):
    """``u(path)``: the link to use for ``path`` on a page in ``lang``."""
    if lang != LANG:
        return lambda path: path

    def link(path):
        if not isinstance(path, str) or not path.startswith("/") or path.startswith(PREFIX + "/") or path == PREFIX:
            return path
        if path.split("?")[0] == "/reckonerp-signup":
            return path + ("&" if "?" in path else "?") + "lang=bn"
        return bn_path(path)

    return link


def make_translator(lang: str):
    """``tr(text)`` for templates."""
    if lang != LANG:
        return lambda text: text
    return translate
