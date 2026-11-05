"""The SEO agent's writer: article, tutorial, feature-guide and weekly-update drafts.

Drafts are **SEO Article** records in status *Draft*. The agent never publishes. Each
draft also carries an off-page promotion kit (LinkedIn and Facebook posts and an
outreach pitch) that a person copies and sends; the agent posts nothing anywhere.

Facts: product claims may only come from the site's own text and from the vendor's
"Blog Notes" in SaaS Platform Settings. The model has no browsing, so it is told not
to state news, statistics, dates, versions or competitor claims.
"""

from __future__ import annotations

import re

import frappe

from reckon_saas_platform import blog, marketing, seo_agent

MAX_ARTICLES_PER_RUN = 3
MIN_WORDS, MAX_WORDS = 350, 2200
# Narrower than the page-text rule: "best practices" is fine in an article, "the best ERP" is not.
FORBIDDEN_ARTICLE = re.compile(r"(\bthe best\b|\bbest in\b|\bnumber one\b|#1\b|\bguaranteed?\b|\bcheapest\b|frappe|<script)", re.I)
# Phrases that make text read as machine-written. A draft with these gets one clean-up pass.
AI_CLICHES = re.compile(
    r"(in today's (?:fast-paced|digital|competitive)|in the ever-(?:changing|evolving)|\bdelve\w*|\btapestry\b|"
    r"\bleverag(?:e|es|ed|ing)\b|\bunlock(?:s|ed|ing)?\b|\bseamless(?:ly)?\b|\brobust\b|game[- ]chang\w+|"
    r"\blandscape\b|it(?:'s| is) important to (?:note|remember)|in conclusion|\bembark\b|\bholistic\b|"
    r"\bcutting-edge\b|\brevolutioni[sz]e\w*|\bmoreover\b|\bfurthermore\b|\bin summary\b|\bstreamline\w*)",
    re.I,
)
STYLE = (
    "Voice: plain, warm and direct, like an experienced consultant explaining something to a business owner. "
    "Write in the first person plural ('we') where it is natural and use contractions. Mix short and long sentences. "
    "Open with a concrete situation or a question the reader really has, never a definition. Use one realistic example, "
    "clearly framed as an example (say 'imagine a distributor who...'). Do not invent customers, quotes, case studies or "
    "statistics. Say what does not work or what to watch out for. No filler or cliches: never write 'in today's fast-paced "
    "world', 'delve', 'leverage', 'unlock', 'seamless', 'robust', 'game-changer', 'landscape', 'it's important to note', "
    "'in conclusion', 'furthermore' or 'moreover'. No emojis. Use commas or full stops, not em dashes. "
    "End with one practical next step, not a summary."
)
MARKERS = ("TITLE", "SUMMARY", "KEYWORDS", "BODY", "LINKEDIN", "FACEBOOK", "PITCH")

CATEGORY_BRIEF = {
    "Tutorial": "a step-by-step how-to for a task in one of the ReckonERP modules",
    "Feature Guide": "an in-depth explanation of one product feature: what it does, who it is for, how to start",
    "Article": "an educational article on an ERP, distribution, accounting or AI-for-business topic, tied to what ReckonERP offers",
    "Weekly Update": "a short weekly update: this week's notes from the vendor when given, otherwise practical tips for using ReckonERP",
}


def categories_for_run(count: int, week: int) -> list[str]:
    """Rotate through the four kinds so the blog stays varied from week to week."""
    return [blog.CATEGORIES[(week + i) % len(blog.CATEGORIES)] for i in range(count)]


def parse_sections(text: str) -> dict[str, str]:
    """Split a reply written with ``###NAME###`` markers into its parts."""
    found = {}
    pattern = r"###(" + "|".join(MARKERS) + r")###\s*(.*?)(?=###(?:" + "|".join(MARKERS) + r")###|\Z)"
    for name, value in re.findall(pattern, text or "", flags=re.S):
        found[name] = value.strip()
    return found


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", blog.plain_text(text)))


def valid_article(title: str, summary: str, body: str) -> str:
    """Empty when publishable, otherwise the reason it was rejected."""
    if not 20 <= len(title) <= 58:
        return "title must be 20-58 characters"
    if not seo_agent.valid_description(summary):
        return "summary must be 70-160 characters without superlatives"
    if not MIN_WORDS <= word_count(body) <= MAX_WORDS:
        return f"body must be {MIN_WORDS}-{MAX_WORDS} words"
    if FORBIDDEN_ARTICLE.search(title + " " + summary + " " + body):
        return "contains an unverifiable claim, script or the framework name"
    if len(re.findall(r"(?m)^##\s+\S", body)) < 2:
        return "needs at least two ## sections"
    if re.search(r"\]\(http://", body):
        return "links must be https or site-relative"
    if not re.search(r"\]\(/[a-z]", body):
        return "needs at least one internal link"
    return ""


def cliches(text: str) -> list[str]:
    return sorted({match.group(0).lower() for match in AI_CLICHES.finditer(text or "")})


def tidy(text: str) -> str:
    """Small mechanical clean-ups that make a draft read less machine-made."""
    return text.replace(" \u2014 ", ", ").replace("\u2014", ", ").replace(" \u2013 ", ", ").strip()


def _humanise_prompt(body: str, found: list[str]) -> str:
    return (
        "Edit this blog draft so it reads as if an experienced person wrote it. Keep every fact, every heading, every link "
        "and the Markdown structure. Do not add facts. Rewrite the sentences that use these stock phrases: "
        f"{', '.join(found)}. Vary sentence length, use contractions, put the point first and cut filler. "
        "Return ONLY the revised Markdown body.\n\n" + body
    )


def humanise(settings, body: str) -> tuple[str, list[str]]:
    """One clean-up call when stock phrases are found. Returns the body and any phrases still left."""
    found = cliches(body)
    if not found:
        return body, []
    try:
        revised = tidy(re.sub(r"<[^>]*>", "", seo_agent.call_model(settings, _humanise_prompt(body, found), 3500)))
    except seo_agent.AgentLimit:
        return body, found
    if MIN_WORDS <= word_count(revised) <= MAX_WORDS and len(re.findall(r"\]\(/", revised)) >= 1:
        body = revised
    return body, cliches(body)


def unique_slug(title: str) -> str:
    base = blog.slugify(title) or "post"
    slug, n = base, 2
    while frappe.db.exists(blog.DOCTYPE, slug):
        slug = f"{base[:74]}-{n}"
        n += 1
    return slug


def _plan_prompt(categories, pages, keywords, titles, notes) -> str:
    wanted = "\n".join(f"- {c}: {CATEGORY_BRIEF[c]}" for c in categories)
    return (
        "You plan blog posts for ReckonERP, a cloud ERP with built-in AI. Pick one topic per kind below "
        "that people search for and that the facts support.\n"
        f"Kinds wanted:\n{wanted}\n\n"
        f"Target keywords:\n{chr(10).join('- ' + k for k in keywords) or '- (none given)'}\n\n"
        f"Existing posts (do not repeat):\n{chr(10).join('- ' + t for t in titles) or '- none yet'}\n\n"
        f"Vendor notes for this week (may be empty):\n{notes or '(none)'}\n\n"
        f"Facts (page: title | description):\n{seo_agent._site_facts(pages)}\n\n"
        "Reply with ONLY a JSON array: "
        '[{"category": "Tutorial", "title": "working title", "keyword": "main search phrase", "outline": "3-6 section names"}]'
    )


def _write_prompt(topic, pages, paths, notes) -> str:
    kind = topic["category"]
    return (
        f"Write {CATEGORY_BRIEF[kind]} for the ReckonERP blog.\n"
        f"Working title: {topic['title']}\nMain search phrase: {topic.get('keyword', '')}\nOutline: {topic.get('outline', '')}\n\n"
        f"Facts about ReckonERP you may use (page: title | description):\n{seo_agent._site_facts(pages)}\n"
        f"Vendor notes (may be empty): {notes or '(none)'}\n\n"
        f"{STYLE}\n\n"
        "Rules: use only the facts above for anything about ReckonERP. Do not state news, statistics, dates, "
        "version numbers, prices or claims about competitors. Never say 'the best', 'number one', 'guaranteed' or "
        "'cheapest'. Never mention the Frappe framework. Write plainly for business owners.\n"
        f"Body: Markdown, {MIN_WORDS + 50}-1200 words, at least two '## ' sections, a short intro, and at least two links to "
        f"these site pages written like [text](/modules): {', '.join(paths)}.\n\n"
        "Reply using exactly these markers, each on its own line, nothing else:\n"
        "###TITLE### (20-58 characters)\n###SUMMARY### (70-160 characters, no superlatives)\n"
        "###KEYWORDS### (comma separated, up to 6)\n###BODY### (the article)\n"
        "###LINKEDIN### (a post of 40-80 words ending with {LINK})\n"
        "###FACEBOOK### (a post of 30-60 words ending with {LINK})\n"
        "###PITCH### (a 60-100 word email a person can send to a relevant blog or directory asking them to read or link to the "
        "article, ending with {LINK})"
    )


def _module_for(topic_text: str, modules: list[dict]) -> str:
    lowered = topic_text.lower()
    for module in modules:
        if module["name"].lower() in lowered or module["key"].replace("_", " ") in lowered:
            return module["key"]
    return ""


def draft_topic(settings, topic: dict, pages: list[dict], modules: list[dict], paths: list[str], notes: str, base: str):
    """Write, check, clean up and save one draft. Returns ``(title, "")`` or ``(None, reason)``."""
    category = topic["category"]
    working = topic["title"]
    reply = seo_agent.call_model(settings, _write_prompt(topic, pages, paths, notes), 3500)
    parts = parse_sections(reply)
    title = seo_agent._clean(parts.get("TITLE"), 80)
    summary = seo_agent._clean(parts.get("SUMMARY"), 200)
    body = tidy(re.sub(r"<[^>]*>", "", parts.get("BODY", "")))
    problem = valid_article(title, summary, body)
    if problem:
        return None, problem
    body, left = humanise(settings, body)
    problem = valid_article(title, summary, body)
    if len(left) >= 4 or problem:
        return None, problem or "the draft still reads like stock AI text"
    slug = unique_slug(title)
    link = f"{base}{blog.article_url(slug)}"
    promo = "\n\n".join(
        f"{label}:\n{parts.get(key, '').replace('{LINK}', link).strip()}"
        for label, key in (("LinkedIn post", "LINKEDIN"), ("Facebook post", "FACEBOOK"), ("Outreach pitch", "PITCH"))
        if parts.get(key)
    )
    doc = frappe.get_doc(
        {
            "doctype": blog.DOCTYPE,
            "slug": slug,
            "title": title,
            "category": category,
            "status": "Draft",
            "source": "AI",
            "summary": summary,
            "body": blog.render_markdown(body),  # stored as HTML so the rich-text editor shows it formatted
            "keywords": seo_agent._clean(parts.get("KEYWORDS"), 140),
            "related_module": _module_for(title + " " + working + " " + str(topic.get("keyword") or ""), modules),
            "promo_kit": promo,
        }
    )
    doc.insert(ignore_permissions=True)
    try:
        from reckon_saas_platform import blog_image

        cover = blog_image.attach_cover(slug, title, category)
        if cover:
            frappe.db.set_value(blog.DOCTYPE, slug, "cover_image", cover)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Blog cover image")  # the post is still saved without a cover
    return title, ""


def site_paths(modules: list[dict]) -> list[str]:
    return [marketing.MODULES, marketing.FEATURES, marketing.INTEGRATIONS, marketing.FAQ, marketing.SIGNUP] + [m["url"] for m in modules]


def already_wrote_this_month() -> bool:
    first = str(frappe.utils.nowdate())[:7] + "-01"
    return bool(
        frappe.get_all(blog.DOCTYPE, filters={"source": "AI", "creation": [">=", first]}, pluck="name", limit=1, ignore_permissions=True)
    )


def write_articles(
    settings, pages: list[dict], modules: list[dict], keywords: list[str], week: int, force: bool = False
) -> list[str]:
    """Draft up to ``articles per run`` posts. Returns the titles written.

    With **Blog Frequency** set to Monthly (the default) a scheduled run writes only when no
    AI draft exists yet this month; the Run SEO Agent button always writes (``force``).
    """
    if not frappe.utils.cint(settings.get("seo_blog_enabled")):
        return []
    if (settings.get("seo_blog_frequency") or "Monthly") == "Monthly" and not force and already_wrote_this_month():
        return []
    count = min(max(frappe.utils.cint(settings.get("seo_agent_articles_per_run") or 1), 1), MAX_ARTICLES_PER_RUN)
    categories = categories_for_run(count, week)
    notes = str(settings.get("seo_blog_notes") or "").strip()[:2000]
    keyword_list = seo_agent._lines(settings.get("seo_target_keywords"))
    titles = frappe.get_all(blog.DOCTYPE, pluck="title", ignore_permissions=True)
    plan = seo_agent.parse_json_list(seo_agent.call_model(settings, _plan_prompt(categories, pages, keyword_list, titles, notes), 900))
    paths = site_paths(modules)
    base = marketing.site_base()
    written = []
    for topic in plan[:count]:
        category = str(topic.get("category") or "")
        working = seo_agent._clean(topic.get("title"), 120)
        if category not in categories or not working:
            continue
        title, _reason = draft_topic(settings, {**topic, "category": category, "title": working}, pages, modules, paths, notes, base)
        if title:
            written.append(title)
    return written
