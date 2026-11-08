# Reckon SaaS Platform

Reusable parent SaaS platform for Reckon ERP apps on Frappe/ERPNext v15 and v16+.

This app owns tenant identity, subscription plans, registration, payment
verification, provisioning jobs, tenant assignment, route gates, and public SaaS
pages. Business modules such as `reckon_distribution` plug into it through the
`reckon_saas_modules` hook.

Install before product modules:

```bash
bench get-app reckon_saas_platform <platform-repo-url>
bench --site distribution.reckon.tech install-app reckon_saas_platform
```

Then install a product module such as `reckon_distribution`.

## Signup verification

Public signup creates no Company or User until the owner has verified both the
email link and, by default, an SMS one-time code. Configure it in
**SaaS Platform Settings** (`/app/saas-platform-settings`, vendor only):

- **BulkSMSBD API Key / Sender ID**: from your bulksmsbd.net account. Codes are
  sent in English, so use a non-masking sender ID (BulkSMSBD requires Bengali
  text for masking senders).
- **reCAPTCHA Type / Site Key / Secret Key**: create a key at
  https://www.google.com/recaptcha/admin and restrict it to the signup domain.
  **v2 Checkbox** shows "I'm not a robot"; **v3 Invisible** needs no click and
  refuses signups below **reCAPTCHA v3 Minimum Score** (default 0.5). The key's
  type in Google's console must match the type selected here.
- **Require Email Verification** (on by default) applies only when the site has
  an outgoing Email Account. When it is off, or there is no Email Account, the
  site sends no email at all: the typed address is trusted, the signup form asks
  for a password, and the owner signs in with it as soon as the workspace is
  ready. With both email and phone checks off, provisioning starts immediately,
  leaving only captcha and rate limits in front of Company creation.
- **Require Phone Verification / Require Captcha** are on by default. While
  either is on without credentials, signup answers 503 "temporarily
  unavailable", so configure the keys right after deploying.
- **Signup Rate Limits**: attempts per IP address per hour (signup 5 and
  verification 20 by default; failed attempts count). 0 falls back to the
  `reckon_saas_signup_rate_limit` / `reckon_saas_verify_rate_limit` site config,
  then the defaults. **Reset Rate Limits** on the form clears the current counters.

Failed provisioning jobs show on `/reckon-saas-admin` with a **Retry
Provisioning** button.

## Public marketing website

The site root `/` is a server-rendered marketing website (`www/index`), with
`/features` and `/features/<slug>`, `/modules` and `/modules/<key>`,
`/integrations`, `/sitemap.xml`, `/robots.txt` and `/llms.txt`. Sign up goes to
`/reckonerp-signup` and log in to `/login`.

- Module pages come from the `reckon_saas_modules` registry, so a module appears
  when its app is installed and **Available for Sale** is ticked. Marketing text
  for a module key lives in `MODULE_COPY` in `marketing.py`; a module without
  written copy still gets a page from its registry description.
- Feature pages and the integrations/channels icon list are data in
  `marketing.py`; templates are in `templates/marketing/`.
- Every address is relative or built from the domain serving the page
  (`frappe.utils.get_url()`); no domain is written in the code.
- Website Settings > Home Page overrides the app's `home_page` hook. On migrate,
  a value of `login`, `index` or `home` is cleared so the root shows this site;
  any other value is left alone.

## SEO, Google and Meta tracking

Open **SaaS Platform Settings** (`/app/saas-platform-settings`), section
**Website SEO and Tracking**. Nothing is added to any page until an ID is entered.

- **Google Tag Manager ID** (`GTM-XXXXXXX`): recommended. Manage Google Analytics,
  Google Ads and the Meta Pixel from Tag Manager.
- **Google Analytics 4 Measurement ID** (`G-XXXXXXXXXX`): loads Analytics directly
  when no Tag Manager ID is set. Leave empty if Analytics lives in Tag Manager.
- **Meta Pixel ID**: loads the Meta Pixel with a PageView; clicks to signup send
  `Lead` and the WhatsApp chat sends `Contact`. The same moments are pushed to the
  Tag Manager `dataLayer` as `signup_click` and `whatsapp_chat`.
- **Tracking Consent**: *Ask visitors first* (default) shows an Accept / Decline
  notice and loads the tags only after Accept; *Load immediately* skips the notice.
- **Search Console, Bing and Meta domain verification**: paste only the content
  value of each verification tag; it is added to the home page head.

After saving, submit `/sitemap.xml` in Google Search Console and Bing Webmaster
Tools. IDs are checked against their expected format before they reach a page.

### SEO stays current by itself

Titles, descriptions, `sitemap.xml`, `llms.txt`, `llms-full.txt` and structured data
are built from the live module registry on every request, so a new or renamed
module needs no SEO work. On top of that, `reckon_saas_platform.seo.refresh_seo`
runs **after every migrate** (so after each release of this app or of the theme)
and **once a day**: it checks every public page, stores the result in SaaS
Platform Settings > SEO Health, clears the website cache when content changed, and,
if **Notify Search Engines** is ticked, sends one IndexNow notice (Bing and
partners). **Check SEO Now** runs it on demand. CI also fails if titles or
descriptions repeat or run too long.

### SEO agent (AI)

**SaaS Platform Settings > SEO Agent (AI)**: tick **Enable SEO Agent**, choose the
provider and model, paste an API key, list **Target Keywords** and **Questions to Ask
AI Assistants**, and set the **Monthly AI Call Limit**. It runs weekly, or with the
**Run SEO Agent** button, and does three things: lists target keywords no page
covers, drafts better titles, descriptions and FAQ answers from facts the site
already states, and asks the model your questions to see whether it names
ReckonERP (model knowledge only, no browsing, so a signal, not a ranking).

Everything it writes is an **SEO Suggestion** (`/app/seo-suggestion`) in *Pending*.
Edit it if you like, then **Approve** or **Reject**. Only approved text reaches the
site, after the same length and wording checks (no "best", "guaranteed", ...); the SEO
check then re-runs and, if enabled, search engines are notified. It does nothing
until enabled and keyed, and stops at the monthly limit.

### SEO Agent (a chat page inside SaaS Admin)

Open **SaaS Admin > SEO Agent Studio > SEO Agent** (`/desk/seo-agent`, vendor users only). It is
one text box, like a chat: type "What needs my approval?", "Find keyword gaps", "Improve page
titles", "Suggest new FAQs", "Check if AI assistants mention us" or "Write a blog article about
route planning". Replies are plain sentences, and anything it proposes appears as a card you
**Approve**, **Reject**, **Publish** or open to edit, right in the conversation. Pending and
keyword-gap questions cost nothing; the rest use the monthly AI call limit and the same checks as
the weekly run. It stays in one window, and nothing goes live until you act on a card. Settings
(enable, AI key, model, keywords, limits) are in **SaaS Platform Settings > SEO Agent (AI)**. The
module **SEO Agent Studio** owns the SEO Suggestion and SEO Article doctypes, still reachable from
the page's **All suggestions** and **All articles** buttons. After deploying run `bench build`,
`bench migrate` and `bench restart`.

### Blog and the agent that writes for it

The landing page, header and footer link to **/blog**: articles, tutorials, feature
guides and weekly updates, each at `/blog/<slug>`, with an RSS feed at
`/blog/rss.xml`. Posts are **SEO Article** records (`/app/seo-article`) written in a **rich-text editor**; the website outputs only an allow-list of the HTML (headings, lists, links, images, code, quotes, tables), never scripts or event handlers. Published
posts feed the sitemap (with `lastmod`), `llms.txt`, BlogPosting structured data, the
landing page's "From the blog" section and the related module page. An empty blog is
`noindex` and stays out of the sitemap.

To have the agent write: in **SaaS Platform Settings > SEO Agent (AI)** enable the agent,
tick **Write Blog Drafts**, set **Articles per Run** (1-3), **Blog Frequency** (Monthly by default) and, for the weekly update,
paste this week's release notes or news into **Blog Notes**. Monthly means a scheduled run writes only if no AI draft exists yet this month; **Run SEO Agent** always writes. Each run rotates through
tutorial, feature guide, article and weekly update, and saves **drafts**. Read one,
edit it, then **Publish**. The agent has no internet access and is told not to state
news, statistics, dates or competitor claims; it may only describe ReckonERP from the
site's own text and your notes. Each draft also carries an **Off-page Promotion Kit**:
a LinkedIn post, a Facebook post and an outreach pitch for blogs and directories. Each draft also gets a **cover image** drawn by the platform (a branded 1200x630 picture with the title and a
illustration for its kind); **Draw Cover** redraws it. The cover is used on the post, the cards and the social preview.
Drafts are written in a plain, human voice and get one clean-up call when stock AI phrases slip in. A
person copies and sends the promotion kit; nothing is posted or emailed automatically.

Off-page checklist (the agent cannot do these for you): publish the LinkedIn and Facebook
posts from the kit, send the pitch to relevant blogs, directories and partners, ask
customers for reviews, and list the company on Google Business Profile, G2, Capterra and
Crunchbase, then add those links under **Official Profile Links**.

## Module pages, pricing, invoices and adding modules

- **Module pages** (`/modules/<key>`): overview, what is inside, who uses it, plans and prices, what is
  included and not, and a long FAQ (price, trial, support, paid training, on-site help, requirement
  analysis, customisation, data migration, adding modules, how to pay). Text for the shipped modules is in
  `module_content.py`; a module without written text still gets a complete page from its registry entry.
  Prices are read from the enabled **SaaS Plan** records (never written in the copy) and also appear as
  schema.org Offers and on `/pricing`.
- **Header banners:** each shipped module has its own drawn picture
  (`python scripts/make_module_banners.py` regenerates them); any later module gets a generated SVG that is
  unique to its key. Add a motif in the script to give a new module a drawn one.
- **Invoices:** after signup an **SaaS Invoice** is created in the background and emailed to the owner with a
  PDF (needs an outgoing Email Account and `wkhtmltopdf`, as ERPNext prints do); a link is texted by
  SMS when BulkSMSBD is set up. Both can be switched off, and a payment instruction text set, under **SaaS
  Platform Settings > Invoices and Payment**. The invoice is public at `/invoice/<key>` (the key is random),
  with a PDF download, a WhatsApp share link and a link to report the payment. A verified payment marks it
  paid and emails a receipt. Vendor users can **Send Again** or open WhatsApp to the customer from the invoice.
  WhatsApp is a link, not an automatic send: free-text WhatsApp messages to new customers need an approved
  template from a WhatsApp provider.
- **Renewals:** a daily job issues the next period's invoice **7 days before** a paid period ends (change
  **Renewal Invoice Lead Days** in the settings; 0 turns it off) and sends it by email and SMS like the first
  one. Only Active, Due and Grace subscriptions with a paid-until date are renewed, one invoice per period, and a
  verified payment settles the oldest unpaid invoice first.
- **Reminders:** unpaid invoices get an email and SMS on a schedule counted from the due date, by default 2
  days before, then 1 and 7 days after (**Payment Reminder Schedule** in the settings; empty turns reminders
  off). Each step is sent once; after missed days only one reminder goes out; paid or cancelled invoices and
  invoices of cancelled, suspended or expired subscriptions are skipped.
- **Paying:** the owner pays by bKash, Nagad, Rocket or bank transfer and reports the transaction reference on
  `/reckonerp-subscription`; a vendor user verifies it, which unlocks the module.
- **Adding a module later:** on the Subscription page the company admin sees **Add a module** with every
  module on sale that the company does not hold. Subscribing creates a separate subscription, payment and
  invoice, seeds the module's starting data and refreshes the team's roles; a verified payment refreshes
  them again.

## Modules and plans

Each product app declares its module in the `reckon_saas_modules` hook. On
install and on every migrate the platform creates a **SaaS Module** record for
it (`/app/saas-module`). Every **SaaS Plan** belongs to one module, and
registrations and subscriptions record the module they were bought for.

- Untick **Available for Sale** on a module to stop new signups for its plans.
- `/reckonerp-signup?module=<key>` shows only that module's plans; without the
  parameter, plans are grouped by module.
- A company keeps Desk access while any of its module subscriptions is active.
  `is_subscription_active(company, saas_module=...)` checks a single module.

The vendor **Dashboard** (`/app/saas-dashboard`) is the first item in the SaaS
Platform sidebar.

## Installing and updating apps safely

`bench get-app <url>` clones into a folder named after the repository
(`Reckon-SaaS-Platform`) and then renames it to the app name
(`reckon_saas_platform`). When that rename fails, because the app is already
installed or an old folder is in the way, the bench can keep a repo-named folder
and `sites/apps.txt` can list a name Python cannot import. Every later
`bench build` and `bench migrate` then crashes with
`ModuleNotFoundError: No module named 'Reckon-…'`.

Use `scripts/reckon_bench.py` from the bench directory instead of calling
`bench get-app` directly:

```bash
# Install a new app. If it is already installed, it is updated (git pull) instead.
python apps/reckon_saas_platform/scripts/reckon_bench.py get-app https://github.com/TechwithZakir/Reckon-Accounts-SaaS

# Update installed apps
python apps/reckon_saas_platform/scripts/reckon_bench.py update reckon_saas_platform reckon_distribution reckon_accounts_saas

# Check, then repair, sites/apps.txt and leftover folders
python apps/reckon_saas_platform/scripts/reckon_bench.py doctor
python apps/reckon_saas_platform/scripts/reckon_bench.py doctor --apply
```

`get-app` repairs the registry before and after calling bench, so a failed
install never leaves bench unable to build. `doctor --apply` backs up
`sites/apps.txt` under `sites/.app-registry-backups/` and moves leftover
repo-named folders to `archived/apps/`. It uses only the Python standard library,
so it works even when bench itself cannot start, and it never changes a site's
database.
