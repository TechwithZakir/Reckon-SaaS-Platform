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
    "Skip to content": "মূল কনটেন্টে যান",
    "ReckonERP": "ReckonERP",
    "ReckonERP home": "ReckonERP হোমপেজ",
    "ReckonERP logo": "ReckonERP লোগো",
    "Main": "প্রধান মেনু",
    "Home": "হোম",
    "Features": "ফিচার",
    "Modules": "মডিউল",
    "Industries": "ইন্ডাস্ট্রি",
    "Pricing": "মূল্য",
    "Integrations": "ইন্টিগ্রেশন",
    "Blog": "ব্লগ",
    "FAQ": "জিজ্ঞাসা",
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
    "Breadcrumb": "আপনি এখানে আছেন",
    "Summary": "সারসংক্ষেপ",
    # --- footer and company ---
    "Cloud ERP with built-in AI for growing businesses, built on ERPNext.": "বর্ধনশীল ব্যবসার জন্য AI সহ Cloud ERP, ERPNext-এর ওপর তৈরি।",
    "Company": "কোম্পানি",
    "About us": "আমাদের সম্পর্কে",
    "Popular solutions": "জনপ্রিয় সলিউশন",
    "Cloud ERP software in Bangladesh": "বাংলাদেশে Cloud ERP সফটওয়্যার",
    "ERP software by industry": "ইন্ডাস্ট্রি অনুযায়ী ERP সফটওয়্যার",
    "ERP and AI automation guides": "ERP ও AI Automation গাইড",
    "AI agent development and automation": "AI Agent ডেভেলপমেন্ট ও Automation",
    "Website:": "ওয়েবসাইট:",
    "Mail Address:": "ইমেইল:",
    "Email:": "ইমেইল:",
    "WhatsApp / Cell:": "WhatsApp / মোবাইল:",
    "WhatsApp:": "WhatsApp:",
    "Address:": "ঠিকানা:",
    "Social profile:": "সোশ্যাল প্রোফাইল:",
    "ReckonERP by Reckon Technologies Ltd.": "ReckonERP by Reckon Technologies Ltd.",
    "Our services": "আমাদের সেবা",
    "We solve it best with our expertise": "আমাদের অভিজ্ঞতা দিয়ে আমরা আপনার সমস্যার সমাধান করি",
    "Ask about these on WhatsApp": "এসব বিষয়ে WhatsApp-এ জিজ্ঞাসা করুন",
    "Ask us for a quote on WhatsApp": "কোটেশনের জন্য WhatsApp-এ আমাদের জানান",
    "Ask us on WhatsApp": "WhatsApp-এ আমাদের জিজ্ঞাসা করুন",
    "More from Reckon, on request": "Reckon-এর আরও সলিউশন, অনুরোধে",
    # --- chat and cookie notice ---
    "Chat": "চ্যাট",
    "Chat with ReckonERP": "ReckonERP-এর সাথে চ্যাট করুন",
    "Ask about modules, pricing, deployment or AI. We reply on WhatsApp.": "মডিউল, মূল্য, Deployment বা AI নিয়ে জানতে চান? আমরা WhatsApp-এ উত্তর দিই।",
    "Your name": "আপনার নাম",
    "Message": "আপনার বার্তা",
    "Continue on WhatsApp": "WhatsApp-এ চালিয়ে যান",
    "Nothing is sent until you press the button; WhatsApp then opens with your message ready. Prefer email?": "বোতামে চাপ না দেওয়া পর্যন্ত কিছু পাঠানো হয় না; চাপলে WhatsApp-এ আপনার বার্তা তৈরি অবস্থায় খুলবে। ইমেইল করতে চাইলে:",
    "Cookie notice": "কুকি নোটিশ",
    "We use cookies for analytics and advertising measurement. Accept to allow them, or decline to browse without them.": "সাইটের ব্যবহার বিশ্লেষণ ও বিজ্ঞাপনের ফলাফল মাপতে আমরা কুকি ব্যবহার করি। অনুমতি দিতে ‘গ্রহণ করুন’ চাপুন; না চাইলে ‘প্রত্যাখ্যান করুন’—কুকি ছাড়াই সাইট ব্যবহার করতে পারবেন।",
    "Accept": "গ্রহণ করুন",
    "Decline": "প্রত্যাখ্যান করুন",
    # --- common words and sentence templates ---
    "AI": "AI",
    "ERP": "ERP",
    "CRM": "CRM",
    "Automation": "Automation",
    "Read": "পড়ুন",
    "Learn more": "বিস্তারিত দেখুন",
    "See {name}": "{name} দেখুন",
    "about {name}": "{name} সম্পর্কে",
    "About {name}": "{name} সম্পর্কে জানুন",
    "Choose": "বেছে নিন",
    "Start here": "এখান থেকে শুরু করুন",
    "Verify": "যাচাই করুন",
    "Work": "কাজ শুরু করুন",
    "Included": "অন্তর্ভুক্ত",
    "Not included": "অন্তর্ভুক্ত নয়",
    "Feature": "ফিচার",
    "Industry": "ইন্ডাস্ট্রি",
    "ERP module": "ERP Module",
    "In short": "সংক্ষেপে",
    "Pause scrolling": "স্ক্রল থামান",
    "Play scrolling": "স্ক্রল চালু করুন",
    "&copy;": "&copy;",
    "&nbsp;&middot;": "&nbsp;&middot;",
    "{n}-day free trial": "{n} দিনের ফ্রি ট্রায়াল",
    "Choose {name}": "{name} বেছে নিন",
    "Sign up for {name}": "{name}-এর জন্য সাইন আপ করুন",
    "What is inside {name}": "{name}-এর ভেতরে যা আছে",
    "Who uses {name}": "{name} কারা ব্যবহার করেন",
    "Guides for {name}": "{name} নিয়ে গাইড",
    "{name} plans and pricing": "{name}-এর Plan ও মূল্য",
    "See all plans": "সব Plan দেখুন",
    # --- home page ---
    "Your ERP, now with": "আপনার ERP, এখন",
    "an AI that reads every ledger.": "সব লেজার পড়তে পারে এমন AI-এর সাথে।",
    "Invoices, orders, stock and people &mdash; one calm, glass-clear workspace.": "ইনভয়েস, অর্ডার, স্টক আর মানুষের হিসাব &mdash; সবই এক পরিচ্ছন্ন, স্বচ্ছ Workspace-এ।",
    "AI built into ERP, CRM and automation": "ERP, CRM ও Automation-এর ভেতরেই AI",
    "Private workspace for every company, in Bangla or English": "প্রতিটি কোম্পানির জন্য আলাদা Workspace, বাংলা বা ইংরেজিতে ব্যবহার করুন",
    "Start online, or deploy on a dedicated cloud or on-premises": "অনলাইনে শুরু করুন, কিংবা নিজস্ব Dedicated Cloud বা On-premises সার্ভারে চালান",
    "Explore modules": "মডিউল দেখুন",
    "ReckonERP accounts dashboard, campaign studio, integrations and AI assistant screens": "ReckonERP-এর Accounts ড্যাশবোর্ড, ক্যাম্পেইন স্টুডিও, Integration ও AI অ্যাসিস্ট্যান্টের স্ক্রিন",
    "Reckon AI inside every module": "প্রতিটি মডিউলে Reckon AI",
    "AI that works on your own records, with a person in charge": "আপনার নিজের রেকর্ড নিয়ে কাজ করে AI, তবে নিয়ন্ত্রণ থাকে মানুষের হাতে",
    "Meet Reckon AI": "Reckon AI-কে জানুন",
    "AI assistant drafting a reply that waits for a person to approve": "AI অ্যাসিস্ট্যান্ট একটি উত্তরের খসড়া করছে, যা মানুষের অনুমোদনের অপেক্ষায় আছে",
    "ERP, CRM, automation and AI working together": "ERP, CRM, Automation আর AI—সব একসাথে",
    "One platform instead of four tools that never quite talk to each other.": "চারটি আলাদা টুলের বদলে একটি প্ল্যাটফর্ম, যেখানে সবকিছু একে অপরের সাথে মিলে কাজ করে।",
    "Connects the channels your customers use": "আপনার গ্রাহকরা যেসব চ্যানেল ব্যবহার করেন, সেগুলোর সাথেই যুক্ত",
    "WhatsApp, social, SMS, voice, email and AI services.": "WhatsApp, সোশ্যাল মিডিয়া, SMS, ভয়েস, ইমেইল ও AI সার্ভিস।",
    "See every integration": "সব Integration দেখুন",
    "ERP modules": "ERP Module",
    "Subscribe to one module or several. Each runs in your own company workspace.": "একটি বা একাধিক মডিউল সাবস্ক্রাইব করুন। প্রতিটি আপনার নিজস্ব কোম্পানি Workspace-এ চলে।",
    "From the blog": "ব্লগ থেকে",
    "Guides, tutorials and weekly updates.": "গাইড, টিউটোরিয়াল ও সাপ্তাহিক আপডেট।",
    "All articles": "সব লেখা দেখুন",
    "Deploy it your way": "আপনার মতো করে Deploy করুন",
    "Start on the shared cloud today. Move to a dedicated cloud or your own servers when you need to.": "আজই Shared Cloud-এ শুরু করুন। প্রয়োজন হলে পরে Dedicated Cloud বা নিজস্ব সার্ভারে নিয়ে যান।",
    "Customisation, implementation, data migration, AI and integration tools are additional.": "Customization, Implementation, Data migration এবং AI ও Integration টুলের জন্য আলাদা চার্জ প্রযোজ্য।",
    "Multi-currency, multi-language and easy to customise for enterprise packages.": "Multi-currency, Multi-language এবং Enterprise প্যাকেজের জন্য সহজে Customize করার সুবিধা।",
    "What the platform gives you": "প্ল্যাটফর্মে আপনি যা যা পাবেন",
    "Each feature has its own page.": "প্রতিটি ফিচারের জন্য আলাদা পেজ আছে।",
    "Start in three steps": "তিনটি ধাপে শুরু করুন",
    "Pick a module and a plan that fits your company.": "আপনার কোম্পানির জন্য উপযুক্ত মডিউল ও Plan বেছে নিন।",
    "Confirm your email and phone number so only real owners get a workspace.": "ইমেইল ও ফোন নম্বর যাচাই করুন, যাতে শুধু আসল মালিকরাই Workspace পান।",
    "Your workspace is set up with starting data and opens in your browser.": "শুরুর ডেটাসহ আপনার Workspace তৈরি হয়ে ব্রাউজারেই খুলে যাবে।",
    "Frequently asked questions": "সচরাচর জিজ্ঞাসা",
    "Ready to run on ReckonERP?": "ReckonERP-এ ব্যবসা চালাতে প্রস্তুত?",
    "Create your company workspace in minutes.": "কয়েক মিনিটেই আপনার কোম্পানির Workspace তৈরি করুন।",
    # --- pricing, modules, features, industries, faq, integrations ---
    "Each module is its own subscription with its own plan, so you pay only for what you use. Prices, billing periods and trial days are exactly what you will see at signup.": "প্রতিটি মডিউল আলাদা সাবস্ক্রিপশন ও আলাদা Plan-এ পাওয়া যায়, তাই আপনি শুধু যা ব্যবহার করবেন তার জন্যই টাকা দেবেন। সাইন আপের সময় যে মূল্য, বিলিং সময়কাল ও ট্রায়ালের দিন দেখবেন, এখানেও ঠিক তা-ই দেখানো হয়েছে।",
    "Plans are shown at signup.": "Plan-এর বিস্তারিত সাইন আপের সময় দেখানো হয়।",
    "Plans are shown when you sign up.": "Plan-এর বিস্তারিত সাইন আপের সময় দেখানো হয়।",
    "Implementation, training, customisation and on-site support are quoted separately.": "Implementation, প্রশিক্ষণ, Customization ও অন-সাইট সাপোর্টের জন্য আলাদা কোটেশন দেওয়া হয়।",
    "Implementation, data migration, training, customisation, on-site support, and AI and integration usage are quoted separately.": "Implementation, Data migration, প্রশিক্ষণ, Customization, অন-সাইট সাপোর্ট এবং AI ও Integration ব্যবহারের জন্য আলাদা কোটেশন দেওয়া হয়।",
    "Subscribe online. Your invoice arrives by email with a PDF, and a link by SMS.": "অনলাইনেই সাবস্ক্রাইব করুন। ইনভয়েসের PDF আপনার ইমেইলে আসবে, আর লিংক পাবেন SMS-এ।",
    "Every module has its own plans, roles and starting data. Subscribe to one or several.": "প্রতিটি মডিউলের নিজস্ব Plan, রোল ও শুরুর ডেটা আছে। এক বা একাধিক মডিউল সাবস্ক্রাইব করতে পারেন।",
    "Module details": "মডিউলের বিবরণ",
    "Built for": "যাদের জন্য তৈরি",
    "What you can do": "আপনি যা করতে পারবেন",
    "Other modules": "অন্যান্য মডিউল",
    "More features": "আরও ফিচার",
    "One page for each thing the platform does, from signup to integrations.": "সাইন আপ থেকে Integration পর্যন্ত, প্ল্যাটফর্মের প্রতিটি কাজের জন্য আলাদা পেজ আছে।",
    "The same cloud ERP, with the parts each sector needs. Standard modules are ready now; sector-specific steps are set up with you.": "একই Cloud ERP, তবে প্রতিটি খাতের প্রয়োজন অনুযায়ী। Standard মডিউল এখনই ব্যবহার করা যায়; আপনার খাতের বিশেষ ধাপগুলো আমরা আপনার সাথে বসে সাজিয়ে দিই।",
    "Ready in the standard modules": "Standard মডিউলে যা প্রস্তুত আছে",
    "Set up for you on request": "অনুরোধে আপনার জন্য যা সাজিয়ে দেওয়া হয়",
    "These parts are customisation after a requirement analysis, quoted separately.": "এই অংশগুলো প্রয়োজন বুঝে Customization-এর মাধ্যমে করা হয়, আলাদা কোটেশনে।",
    "Modules that fit": "যে মডিউল আপনার কাজে আসবে",
    "Other industries": "অন্যান্য ইন্ডাস্ট্রি",
    "Pricing, deployment, implementation, licences, AI and support, answered in one place.": "মূল্য, Deployment, Implementation, লাইসেন্স, AI ও সাপোর্ট—সব প্রশ্নের উত্তর এক জায়গায়।",
    "Read the FAQ": "FAQ পড়ুন",
    "Messaging, social, SMS, voice, email, AI and research services connect from one Integrations page, and each business keeps its own keys.": "মেসেজিং, সোশ্যাল মিডিয়া, SMS, ভয়েস, ইমেইল, AI ও রিসার্চ সার্ভিস এক Integrations পেজ থেকেই যুক্ত করা যায়, আর প্রতিটি ব্যবসা নিজের কী নিজের কাছেই রাখে।",
    "Tell us about your business": "আপনার ব্যবসার কথা আমাদের জানান",
    "Start online or message us for a requirement analysis.": "অনলাইনে শুরু করুন, অথবা আপনার প্রয়োজন বুঝে নিতে আমাদের বার্তা পাঠান।",
    "Pricing questions": "মূল্য নিয়ে প্রশ্ন",
    "Pick a plan and start": "Plan বেছে শুরু করুন",
    "Sign up, verify, and you will receive your invoice by email and SMS.": "সাইন আপ ও যাচাই করুন, তারপর ইনভয়েস পাবেন ইমেইল ও SMS-এ।",
    "Start now": "এখনই শুরু করুন",
    "Try it with your company": "আপনার কোম্পানিতেই ব্যবহার করে দেখুন",
    "Sign up and your workspace is ready after verification.": "সাইন আপ করুন; যাচাইয়ের পর আপনার Workspace তৈরি হয়ে যাবে।",
    # --- feature titles and summaries ---
    "Self-serve signup": "নিজে নিজেই সাইন আপ",
    "Create a verified company workspace on your own, in minutes.": "কয়েক মিনিটেই নিজে নিজে যাচাইকৃত কোম্পানি Workspace তৈরি করুন।",
    "Separate company workspaces": "আলাদা কোম্পানি Workspace",
    "Every customer works inside its own Company, apart from all others.": "প্রতিটি গ্রাহক নিজের Company-র ভেতরে কাজ করেন, অন্য সবার থেকে সম্পূর্ণ আলাদা।",
    "Plans, trials and billing": "Plan, ট্রায়াল ও বিলিং",
    "Plans per module, trial days, billing cycles and verified payments.": "প্রতিটি মডিউলের আলাদা Plan, ট্রায়ালের দিন, বিলিং সাইকেল আর যাচাইকৃত পেমেন্ট।",
    "Modular ERP": "Modular ERP",
    "Start with the module you need and add others on the same platform.": "যে মডিউল দরকার তা দিয়ে শুরু করুন, পরে একই প্ল্যাটফর্মে আরও মডিউল যোগ করুন।",
    "Bangla and English": "বাংলা ও ইংরেজি",
    "Signup in Bangla or English, with Bangla-first workflows for field teams.": "বাংলা বা ইংরেজিতে সাইন আপ করুন; মাঠ পর্যায়ের দলের জন্য আছে বাংলা-আগে Workflow।",
    "Roles and security": "রোল ও নিরাপত্তা",
    "Role-based access, verified owners and guarded sign-in.": "রোল অনুযায়ী অ্যাক্সেস, যাচাইকৃত মালিক এবং সুরক্ষিত সাইন-ইন।",
    "Integrations and channels": "Integration ও চ্যানেল",
    "WhatsApp, social, SMS, voice and email channels in one place.": "WhatsApp, সোশ্যাল মিডিয়া, SMS, ভয়েস ও ইমেইল—সব চ্যানেল এক জায়গায়।",
    "Reckon AI assistant": "Reckon AI অ্যাসিস্ট্যান্ট",
    "Ask questions about your own records and approve the actions it suggests.": "নিজের রেকর্ড নিয়ে প্রশ্ন করুন, আর AI-এর প্রস্তাব করা কাজগুলো আপনি অনুমোদন করুন।",
    "Field sales visits": "মাঠ পর্যায়ের সেলস ভিজিট",
    "Schedule customer visits, check in with GPS and keep a history of every visit.": "গ্রাহক ভিজিটের সময় ঠিক করুন, GPS দিয়ে চেক-ইন করুন এবং প্রতিটি ভিজিটের ইতিহাস রাখুন।",
    "Custom AI agents, assistants and workflow automation, built around your ERP and CRM data.": "আপনার ERP ও CRM ডেটাকে ঘিরে তৈরি Custom AI Agent, অ্যাসিস্ট্যান্ট ও Workflow Automation।",
    "AI-assisted selling": "AI-সহায়তায় বিক্রি",
    "Find, research and qualify customers, with a person approving every message.": "গ্রাহক খুঁজুন, যাচাই করুন ও বাছাই করুন; প্রতিটি বার্তা পাঠানোর আগে অনুমোদন দেন একজন মানুষ।",
    # --- services, deployment, showcase, AI points ---
    "Cloud ERP modules": "Cloud ERP মডিউল",
    "Distribution, Accounts, HRMS, CRM and Sales AI, each in a private company workspace.": "Distribution, Accounts, HRMS, CRM ও Sales AI—প্রতিটি আপনার কোম্পানির আলাদা Workspace-এ।",
    "Multi-currency": "Multi-currency",
    "Quote, invoice and keep books in more than one currency, with plans priced in BDT, USD, EUR or INR.": "একাধিক মুদ্রায় কোটেশন, ইনভয়েস ও হিসাব রাখুন; Plan-এর মূল্য BDT, USD, EUR বা INR-এ।",
    "Multi-language": "Multi-language",
    "Screens in English and Bangla today, and more languages through translation on request.": "এখন ইংরেজি ও বাংলায় ব্যবহার করা যায়; অনুরোধে অনুবাদ করে আরও ভাষা যোগ করা সম্ভব।",
    "Easy to customise": "সহজে Customize করা যায়",
    "The enterprise package shapes fields, workflows, reports, print formats and integrations to how you work.": "Enterprise প্যাকেজে ফিল্ড, Workflow, রিপোর্ট, প্রিন্ট ফরম্যাট ও Integration আপনার কাজের ধরন অনুযায়ী সাজিয়ে দেওয়া হয়।",
    "Dedicated cloud or on-premises": "Dedicated Cloud বা On-premises",
    "Your own server or ours, with your release schedule, backups and access rules.": "আপনার নিজের বা আমাদের সার্ভারে, আপনার পছন্দমতো রিলিজ সময়সূচি, ব্যাকআপ ও অ্যাক্সেস নিয়মসহ।",
    "Reckon AI and integrations": "Reckon AI ও Integration",
    "AI that works on your own records with approval, plus WhatsApp, SMS and email channels. Usage is billed separately.": "অনুমোদন নিয়ে আপনার নিজের রেকর্ডে কাজ করা AI, সাথে WhatsApp, SMS ও ইমেইল চ্যানেল। ব্যবহারের চার্জ আলাদা।",
    "Implementation and training": "Implementation ও প্রশিক্ষণ",
    "Requirement analysis, data migration, setup and team training, quoted for your business.": "প্রয়োজন বিশ্লেষণ, Data migration, সেটআপ ও দলের প্রশিক্ষণ—আপনার ব্যবসা অনুযায়ী কোটেশন।",
    "Support": "সাপোর্ট",
    "Help by email and WhatsApp, with faster or dedicated support available on request.": "ইমেইল ও WhatsApp-এ সহায়তা পাবেন; অনুরোধে আরও দ্রুত বা ডেডিকেটেড সাপোর্টও পাওয়া যায়।",
    "Reckon AI reads and summarises invoices, orders, stock and customer records so people find answers faster": "Reckon AI ইনভয়েস, অর্ডার, স্টক ও গ্রাহকের রেকর্ড পড়ে সারসংক্ষেপ দেয়, ফলে দরকারি উত্তর দ্রুত পাওয়া যায়",
    "Researches leads from their own websites and keeps the evidence next to every claim": "লিডের নিজস্ব ওয়েবসাইট ঘেঁটে তথ্য সংগ্রহ করে এবং প্রতিটি দাবির পাশে প্রমাণ রাখে",
    "Drafts replies and follow-ups; a person approves before anything is sent": "উত্তর ও ফলো-আপের খসড়া তৈরি করে; কিছু পাঠানোর আগে একজন মানুষ অনুমোদন দেন",
    "Scores leads with fixed rules you can read, then syncs them to your CRM": "আপনি পড়ে বুঝতে পারেন এমন নির্দিষ্ট নিয়মে লিড স্কোর করে, তারপর CRM-এ সিঙ্ক করে",
    "AI and integration tools are billed separately from the module subscription.": "AI ও Integration টুলের চার্জ মডিউল সাবস্ক্রিপশন থেকে আলাদা।",
    "Shared cloud": "Shared Cloud",
    "Sign up online from anywhere and start in your own private company workspace. Fastest way to begin.": "যেকোনো জায়গা থেকে অনলাইনে সাইন আপ করে নিজের আলাদা কোম্পানি Workspace-এ শুরু করুন। শুরু করার দ্রুততম উপায়।",
    "Dedicated cloud": "Dedicated Cloud",
    "Your own cloud server for isolation and your own release schedule. Customisation and set-up are quoted separately.": "সম্পূর্ণ আলাদা থাকার জন্য এবং নিজের মতো রিলিজ সময়সূচির জন্য আপনার নিজস্ব Cloud সার্ভার। Customization ও সেটআপের জন্য আলাদা কোটেশন।",
    "On-premises": "On-premises",
    "Installed on your own infrastructure with customisation and support. Quoted to your requirements.": "আপনার নিজস্ব অবকাঠামোতে Customization ও সাপোর্টসহ ইনস্টল করা হয়। প্রয়োজন অনুযায়ী কোটেশন।",
    "Sales, stock, collections and books for your company, in one place.": "বিক্রি, স্টক, আদায় আর হিসাব—আপনার কোম্পানির সবকিছু এক জায়গায়।",
    "Leads and customers move through a pipeline your whole team can see.": "লিড ও গ্রাহক এমন একটি Pipeline দিয়ে এগোয়, যা আপনার পুরো দল দেখতে পায়।",
    "Triggers hand work to steps that draft, route and sync for you.": "ট্রিগার কাজ তুলে দেয় পরের ধাপে, যা আপনার হয়ে খসড়া করে, সঠিক জায়গায় পাঠায় আর সিঙ্ক করে।",
    "AI assistance": "AI সহায়তা",
    "AI drafts and researches; a person approves before anything is sent.": "AI খসড়া ও রিসার্চ করে; কিছু পাঠানোর আগে অনুমোদন দেন একজন মানুষ।",
    # --- module taglines and titles ---
    "Routes, deliveries, collections and stock for FMCG distributors.": "FMCG ডিস্ট্রিবিউটরদের জন্য রুট, ডেলিভারি, আদায় ও স্টকের হিসাব।",
    "Invoices, bills, stock and Tally-style books for a small business.": "ছোট ব্যবসার জন্য ইনভয়েস, বিল, স্টক ও ট্যালি-ধাঁচের হিসাব।",
    "Find, research and follow up B2B customers, with approval before any send.": "B2B গ্রাহক খুঁজুন, যাচাই করুন ও ফলো-আপ করুন; কিছু পাঠানোর আগে থাকে অনুমোদন।",
    "Employees, attendance, leave and payroll in one private workspace per company.": "প্রতিটি কোম্পানির আলাদা Workspace-এ কর্মী, উপস্থিতি, ছুটি ও বেতনের ব্যবস্থাপনা।",
    "Leads, deals and organizations for sales teams, in a private workspace.": "সেলস টিমের জন্য লিড, ডিল ও প্রতিষ্ঠানের তথ্য, আলাদা Workspace-এ।",
    "Distribution management software in Bangladesh": "বাংলাদেশে Distribution Management সফটওয়্যার",
    "Accounting and inventory software in Bangladesh": "বাংলাদেশে Accounting ও Inventory সফটওয়্যার",
    "AI sales agent for B2B lead generation": "B2B লিড জেনারেশনের জন্য AI Sales Agent",
    "HR and payroll software in Bangladesh": "বাংলাদেশে HR ও Payroll সফটওয়্যার",
    "CRM software in Bangladesh for leads and deals": "বাংলাদেশে লিড ও ডিলের জন্য CRM সফটওয়্যার",
    # --- industries ---
    "Garments and RMG": "গার্মেন্টস ও RMG",
    "Textile": "টেক্সটাইল",
    "Pharmaceutical": "ফার্মাসিউটিক্যালস",
    "Healthcare": "স্বাস্থ্যসেবা",
    "Manufacturing": "ম্যানুফ্যাকচারিং",
    "Trading and wholesale": "ট্রেডিং ও পাইকারি ব্যবসা",
    "FMCG distribution": "FMCG ডিস্ট্রিবিউশন",
    "Garments ERP software in Bangladesh": "বাংলাদেশে গার্মেন্টস ব্যবসার ERP সফটওয়্যার",
    "Textile ERP software in Bangladesh": "বাংলাদেশে টেক্সটাইল ব্যবসার ERP সফটওয়্যার",
    "Pharmaceutical ERP software in Bangladesh": "বাংলাদেশে ফার্মাসিউটিক্যালস ব্যবসার ERP সফটওয়্যার",
    "Healthcare ERP software in Bangladesh": "বাংলাদেশে স্বাস্থ্যসেবা প্রতিষ্ঠানের ERP সফটওয়্যার",
    "Manufacturing ERP software in Bangladesh": "বাংলাদেশে ম্যানুফ্যাকচারিং ব্যবসার ERP সফটওয়্যার",
    "Trading business ERP software in Bangladesh": "বাংলাদেশে ট্রেডিং ব্যবসার ERP সফটওয়্যার",
    "FMCG distribution software in Bangladesh": "বাংলাদেশে FMCG ডিস্ট্রিবিউশন সফটওয়্যার",
    # --- page titles, descriptions and headings ---
    "ReckonERP: Cloud ERP, CRM and AI Agents in Bangladesh": "ReckonERP: বাংলাদেশে Cloud ERP, CRM ও AI Agent",
    "Cloud ERP, CRM, HR and payroll, distribution management and AI agent automation for growing businesses in Bangladesh and worldwide. Start online today.": "বাংলাদেশ ও বিশ্বজুড়ে বর্ধনশীল ব্যবসার জন্য Cloud ERP, CRM, HR ও Payroll, Distribution Management এবং AI Agent Automation। আজই অনলাইনে শুরু করুন।",
    "ERP, CRM and AI features for Bangladesh | ReckonERP": "বাংলাদেশের জন্য ERP, CRM ও AI ফিচার | ReckonERP",
    "Every ReckonERP feature: cloud ERP signup, separate company workspaces, plans and billing, Bangla support, AI assistant, CRM and integrations.": "ReckonERP-এর সব ফিচার: Cloud ERP সাইন আপ, আলাদা কোম্পানি Workspace, Plan ও বিলিং, বাংলা সাপোর্ট, AI অ্যাসিস্ট্যান্ট, CRM ও Integration।",
    "Everything the ReckonERP platform does": "ReckonERP প্ল্যাটফর্ম যা যা করতে পারে",
    "ERP modules in Bangladesh: Accounts, CRM, HRMS, AI": "বাংলাদেশে ERP মডিউল: Accounts, CRM, HRMS, AI",
    "Cloud ERP modules you can subscribe to: distribution, accounting, CRM, HR and payroll and a sales AI agent, each with its own plans and private workspace.": "সাবস্ক্রাইব করার মতো Cloud ERP মডিউল: Distribution, Accounting, CRM, HR ও Payroll এবং Sales AI Agent—প্রতিটির নিজস্ব Plan ও আলাদা Workspace।",
    "Choose the modules your business needs": "আপনার ব্যবসার প্রয়োজন অনুযায়ী মডিউল বেছে নিন",
    "Cloud ERP pricing in Bangladesh: plans per module": "বাংলাদেশে Cloud ERP-এর মূল্য: মডিউল অনুযায়ী Plan",
    "ERP, CRM, HR and payroll and accounting subscription plans in BDT, USD, EUR or INR, with trial days and what each includes. Sign up online in minutes.": "ERP, CRM, HR ও Payroll এবং Accounting-এর সাবস্ক্রিপশন Plan BDT, USD, EUR বা INR-এ—ট্রায়ালের দিন ও কী কী অন্তর্ভুক্ত তা সহ। কয়েক মিনিটে অনলাইনে সাইন আপ করুন।",
    "ReckonERP plans and pricing": "ReckonERP Plan ও মূল্য",
    "ERP FAQ: pricing, deployment, AI and support | ReckonERP": "ERP নিয়ে জিজ্ঞাসা: মূল্য, Deployment, AI ও সাপোর্ট | ReckonERP",
    "Answers about ReckonERP pricing, implementation cost, dedicated cloud and on-premises deployment, licences, AI and integration charges, and support.": "ReckonERP-এর মূল্য, Implementation খরচ, Dedicated Cloud ও On-premises Deployment, লাইসেন্স, AI ও Integration চার্জ এবং সাপোর্ট নিয়ে উত্তর।",
    "Frequently asked questions about ReckonERP": "ReckonERP সম্পর্কে সচরাচর জিজ্ঞাসা",
    "Business automation and AI integration | ReckonERP": "Business Automation ও AI Integration | ReckonERP",
    "Connect WhatsApp, Messenger, Instagram, LinkedIn, SMS gateways, email services, Google and AI providers to your ERP and CRM for business automation.": "Business Automation-এর জন্য আপনার ERP ও CRM-এর সাথে WhatsApp, Messenger, Instagram, LinkedIn, SMS গেটওয়ে, ইমেইল সার্ভিস, Google ও AI প্রোভাইডার যুক্ত করুন।",
    "Channels and services you can connect": "যেসব চ্যানেল ও সার্ভিস যুক্ত করা যায়",
    "ERP software by industry in Bangladesh | ReckonERP": "বাংলাদেশে ইন্ডাস্ট্রি অনুযায়ী ERP সফটওয়্যার | ReckonERP",
    "Cloud ERP for garments, textile, pharmaceutical, healthcare, manufacturing, trading and FMCG distribution businesses in Bangladesh.": "বাংলাদেশের গার্মেন্টস, টেক্সটাইল, ফার্মাসিউটিক্যালস, স্বাস্থ্যসেবা, ম্যানুফ্যাকচারিং, ট্রেডিং ও FMCG ডিস্ট্রিবিউশন ব্যবসার জন্য Cloud ERP।",
    "ERP software for your industry": "আপনার ইন্ডাস্ট্রির জন্য ERP সফটওয়্যার",
}


# Module pages: headline, description, audience, benefits, and what every subscription includes or excludes.
BN.update(
    {
        ".": "।",
        "FMCG distribution software for route sales, collections and stock": "রুট সেলস, আদায় ও স্টকের জন্য FMCG ডিস্ট্রিবিউশন সফটওয়্যার",
        "Accounting and inventory software for growing small businesses": "বর্ধনশীল ছোট ব্যবসার জন্য Accounting ও Inventory সফটওয়্যার",
        "AI sales agent for finding and following up B2B customers": "B2B গ্রাহক খুঁজে বের করা ও ফলো-আপের জন্য AI Sales Agent",
        "HR, attendance, leave and payroll software for small businesses": "ছোট ব্যবসার জন্য HR, উপস্থিতি, ছুটি ও Payroll সফটওয়্যার",
        "CRM software for leads, deals and sales teams": "লিড, ডিল ও সেলস টিমের জন্য CRM সফটওয়্যার",
        "Bangla-first SR/DSR distribution for FMCG businesses: routes, deliveries, collections and stock in one place.": "FMCG ব্যবসার জন্য বাংলা-আগে SR/DSR ডিস্ট্রিবিউশন: রুট, ডেলিভারি, আদায় ও স্টক এক জায়গায়।",
        "Sales, purchase, stock and accounting for any small business: invoices, bills, payments, inventory and Tally-style books in Bangla and English.": "যেকোনো ছোট ব্যবসার জন্য বিক্রি, ক্রয়, স্টক ও হিসাব: ইনভয়েস, বিল, পেমেন্ট, ইনভেন্টরি আর ট্যালি-ধাঁচের খাতা—বাংলা ও ইংরেজিতে।",
        "Find, research and qualify B2B customers in Bangladesh, then follow them up from CRM, with human approval before any message is sent.": "বাংলাদেশের B2B গ্রাহক খুঁজুন, যাচাই করুন ও বাছাই করুন, তারপর CRM থেকে ফলো-আপ করুন; কোনো বার্তা পাঠানোর আগে থাকে মানুষের অনুমোদন।",
        "Compact HR and payroll for small businesses: employees, attendance and shifts, leave and payroll, one Company per tenant.": "ছোট ব্যবসার জন্য সহজ HR ও Payroll: কর্মী, উপস্থিতি ও শিফট, ছুটি এবং বেতন—প্রতি গ্রাহকের জন্য একটি আলাদা Company।",
        "Leads, deals and organizations for sales teams, one Company per tenant.": "সেলস টিমের জন্য লিড, ডিল ও প্রতিষ্ঠান—প্রতি গ্রাহকের জন্য একটি আলাদা Company।",
        "FMCG distributors, wholesalers and van-sales teams": "FMCG ডিস্ট্রিবিউটর, পাইকারি ব্যবসায়ী ও ভ্যান-সেলস টিম",
        "Shops, traders and small companies that need clean books": "দোকান, ট্রেডার ও ছোট কোম্পানি, যাদের পরিচ্ছন্ন হিসাব দরকার",
        "B2B sales teams, with strong coverage of Bangladesh": "B2B সেলস টিম, বাংলাদেশের জন্য বিশেষ সহায়তাসহ",
        "Small and growing companies that run HR from spreadsheets": "যেসব ছোট ও বর্ধনশীল কোম্পানি স্প্রেডশিটে HR চালায়",
        "Sales teams that track leads in spreadsheets or chat threads": "যেসব সেলস টিম স্প্রেডশিট বা চ্যাটে লিডের হিসাব রাখে",
        "Plan SR and DSR routes and see what each team delivered": "SR ও DSR-এর রুট সাজান এবং দেখুন প্রতিটি দল কী ডেলিভারি দিল",
        "Track retailer dues and collect against them in the field": "রিটেইলারের বকেয়া হিসাব রাখুন এবং মাঠেই আদায় করুন",
        "Know the cash each DSR is carrying, to the taka": "প্রতিটি DSR-এর কাছে কত নগদ টাকা আছে, টাকায় টাকায় জানুন",
        "Handle goods supplied by principals alongside your own stock": "প্রিন্সিপালের সরবরাহ করা পণ্য নিজের স্টকের পাশাপাশি সামলান",
        "Raise sales invoices and quotations, and record purchase bills and orders": "বিক্রয় ইনভয়েস ও কোটেশন তৈরি করুন, আর ক্রয়ের বিল ও অর্ডার লিখে রাখুন",
        "Keep stock and warehouses in step with what you buy and sell": "যা কিনছেন ও বিক্রি করছেন, স্টক ও গুদামের হিসাব তার সাথে মিলিয়ে রাখুন",
        "Record cash, bank and payments in one place": "নগদ, ব্যাংক ও পেমেন্ট এক জায়গায় লিখুন",
        "Read the books in a Tally-style view, in Bangla or English": "ট্যালি-ধাঁচের ভিউতে বাংলা বা ইংরেজিতে হিসাবের খাতা দেখুন",
        "Run discovery campaigns to find businesses worth contacting": "যোগাযোগের উপযুক্ত ব্যবসা খুঁজে পেতে Discovery ক্যাম্পেইন চালান",
        "Research each lead from its website and keep the evidence": "প্রতিটি লিডের ওয়েবসাইট থেকে তথ্য খুঁজুন এবং প্রমাণ সংরক্ষণ করুন",
        "Score leads with fixed rules, then sync them to your CRM": "নির্দিষ্ট নিয়মে লিড স্কোর করুন, তারপর CRM-এ সিঙ্ক করুন",
        "Send email, SMS and WhatsApp follow-ups only after a person approves": "ইমেইল, SMS ও WhatsApp ফলো-আপ পাঠান শুধু একজন মানুষ অনুমোদন দেওয়ার পরে",
        "Keep one record per employee": "প্রতিটি কর্মীর জন্য একটি রেকর্ড রাখুন",
        "Record attendance and organise shifts": "উপস্থিতি লিখুন ও শিফট সাজান",
        "Let employees request leave and managers approve it": "কর্মীরা ছুটির আবেদন করবেন, ম্যানেজাররা অনুমোদন দেবেন",
        "Run payroll from the attendance and leave you recorded": "রেকর্ড করা উপস্থিতি ও ছুটি থেকেই Payroll চালান",
        "Capture and track every lead": "প্রতিটি লিড সংগ্রহ করুন ও অনুসরণ করুন",
        "Move deals through your pipeline": "আপনার Pipeline-এ ডিলগুলো এগিয়ে নিন",
        "Keep organizations and contacts together": "প্রতিষ্ঠান ও যোগাযোগের তথ্য একসাথে রাখুন",
        "Give owners and the team the access each needs": "মালিক ও দলের প্রত্যেককে যতটুকু অ্যাক্সেস দরকার তা-ই দিন",
        "Your own private company workspace, separate from every other customer": "অন্য সব গ্রাহক থেকে আলাদা, শুধু আপনার নিজের কোম্পানির Workspace",
        "Use in English or Bangla where the screens are translated": "যেসব স্ক্রিন অনুবাদ করা আছে সেগুলো ইংরেজি বা বাংলায় ব্যবহার করা যায়",
        "Roles so each team member sees only what they need": "রোলের মাধ্যমে প্রত্যেকে শুধু প্রয়োজনীয় তথ্যই দেখতে পান",
        "Hosted, backed-up cloud service with software updates": "হোস্টেড ও ব্যাকআপসহ Cloud সার্ভিস, সফটওয়্যার আপডেটসহ",
        "Basic help by email and WhatsApp on how to use the module": "মডিউল কীভাবে ব্যবহার করবেন তা নিয়ে ইমেইল ও WhatsApp-এ প্রাথমিক সহায়তা",
        "Data migration from spreadsheets or other software (quoted separately)": "স্প্রেডশিট বা অন্য সফটওয়্যার থেকে Data migration (আলাদা কোটেশনে)",
        "Custom screens, reports, print formats and workflows beyond the standard module": "Standard মডিউলের বাইরে কাস্টম স্ক্রিন, রিপোর্ট, প্রিন্ট ফরম্যাট ও Workflow",
        "Training sessions, on-site visits and requirement workshops (paid services)": "প্রশিক্ষণ সেশন, অন-সাইট ভিজিট ও প্রয়োজন বিশ্লেষণ ওয়ার্কশপ (সশুল্ক সেবা)",
        "Third-party charges such as SMS, WhatsApp, email or AI provider usage": "SMS, WhatsApp, ইমেইল বা AI প্রোভাইডার ব্যবহারের মতো তৃতীয় পক্ষের চার্জ",
        "Hardware and devices such as printers, scanners and phones": "প্রিন্টার, স্ক্যানার ও ফোনের মতো হার্ডওয়্যার ও ডিভাইস",
    }
)

from reckon_saas_platform import marketing_bn_faq as _faq  # noqa: E402
from reckon_saas_platform import marketing_bn_modules as _modules  # noqa: E402
from reckon_saas_platform import marketing_bn_pages as _pages  # noqa: E402

BN.update(_modules.MODULES)
BN.update(_pages.FEATURES)
BN.update(_pages.INDUSTRIES)
BN.update(_faq.HOME_FAQS)
BN.update(_faq.SITE)

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
    for pattern, build in _modules.PATTERNS:
        found = pattern.match(text)
        if found:
            return build(found, translate)
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
