"""Server side of the SEO Agent chat page: one text box, plain replies, and cards you act on.

The page (``seo_agent_studio/page/seo_agent``) sends what the vendor types to :func:`ask`.
Simple requests (what is waiting, keyword gaps) cost nothing; requests that need the AI
(page text, FAQs, visibility, a blog draft) use the same monthly call limit and the same
checks as the weekly run. Approving, rejecting or publishing goes through :func:`decide`,
which saves the record, so every rule on the record still applies.
"""

from __future__ import annotations

import re

import frappe

from reckon_saas_platform import blog, blog_agent, marketing, seo, seo_agent

SUGGESTION = seo_agent.SUGGESTION
ARTICLE = blog.DOCTYPE
MAX_CARDS = 10

HELP_CHIPS = [
    "What needs my approval?",
    "Find keyword gaps",
    "Improve page titles",
    "Suggest new FAQs",
    "Write a blog article about ",
    "Check if AI assistants mention us",
]
WRITE = re.compile(r"\b(write|create|draft|compose)\b")
ARTICLE_WORDS = re.compile(r"\b(blog|article|post|tutorial|guide|update)\b")
LEADING = re.compile(
    r"^(please\s+)?(can you\s+)?(write|create|draft|compose)\s+(me\s+)?(a|an|the)?\s*(new\s+)?"
    r"((blog|feature)(\s+(post|article|guide))?|article|tutorial|guide|post|(weekly\s+)?update)?\s*(about|on|for|regarding)?\s*",
    re.I,
)


def detect_intent(message: str) -> dict:
    """What the vendor is asking for. Pure text rules, so nothing is spent working it out."""
    text = (message or "").strip()
    low = text.lower()
    if not low or re.fullmatch(r"(hi|hello|hey|help|\?|what can you do\??)", low):
        return {"intent": "help"}
    if (WRITE.search(low) and ARTICLE_WORDS.search(low)) or re.match(r"(blog|article|tutorial)\s+(about|on)\b", low):
        topic = LEADING.sub("", text).strip(" .?!")
        if re.search(r"\btutorial\b|\bhow to\b|step[- ]by[- ]step", low):
            category = "Tutorial"
        elif re.search(r"\bfeature\b", low):
            category = "Feature Guide"
        elif re.search(r"\bweekly\b|\bthis week\b|\bupdate\b", low):
            category = "Weekly Update"
        else:
            category = "Article"
        return {"intent": "article", "topic": topic, "category": category}
    if re.search(r"\b(pending|approve|approval|waiting|review|to do|what needs|drafts?|status)\b", low):
        return {"intent": "pending"}
    if re.search(r"\b(gaps?|keywords?|coverage|missing topics?)\b", low):
        return {"intent": "gaps"}
    if re.search(r"\b(titles?|descriptions?|meta|snippets?)\b", low):
        return {"intent": "titles"}
    if re.search(r"\b(faqs?|questions?)\b", low):
        return {"intent": "faqs"}
    if re.search(r"visib|chatgpt|claude|perplexity|mention|ai answers?|ai assistants?", low):
        return {"intent": "visibility"}
    return {"intent": "help"}


# --- cards ----------------------------------------------------------------------------
def suggestion_card(row) -> dict:
    kind = row.get("kind")
    if kind == "Title and Description":
        current = f"{row.get('current_title') or ''}\n{row.get('current_description') or ''}".strip()
        proposed = f"{row.get('proposed_title') or ''}\n{row.get('proposed_description') or ''}".strip()
    elif kind == "FAQ":
        current, proposed = "", f"{row.get('question') or ''}\n{row.get('answer') or ''}".strip()
    else:
        current, proposed = "", row.get("question") or ""
    return {
        "type": "suggestion",
        "doctype": SUGGESTION,
        "name": row.get("name"),
        "kind": kind,
        "page": row.get("page_path") or "",
        "current": current,
        "proposed": proposed,
        "reason": row.get("reason") or "",
        "status": row.get("status") or "Pending",
    }


def article_card(row) -> dict:
    return {
        "type": "article",
        "doctype": ARTICLE,
        "name": row.get("name"),
        "title": row.get("title") or "",
        "category": row.get("category") or "Article",
        "summary": row.get("summary") or "",
        "cover": row.get("cover_image") or "",
        "status": row.get("status") or "Draft",
    }


SUGGESTION_FIELDS = ["name", "kind", "page_path", "current_title", "current_description", "proposed_title", "proposed_description", "question", "answer", "reason", "status"]
ARTICLE_FIELDS = ["name", "title", "category", "summary", "cover_image", "status"]


def pending_cards(limit: int = MAX_CARDS) -> list[dict]:
    suggestions = frappe.get_all(SUGGESTION, filters={"status": "Pending"}, fields=SUGGESTION_FIELDS, order_by="creation desc", limit=limit, ignore_permissions=True)
    articles = frappe.get_all(ARTICLE, filters={"status": "Draft"}, fields=ARTICLE_FIELDS, order_by="creation desc", limit=limit, ignore_permissions=True)
    return [article_card(a) for a in articles] + [suggestion_card(s) for s in suggestions]


def latest_suggestions(kind: str, count: int) -> list[dict]:
    if count <= 0:
        return []
    rows = frappe.get_all(SUGGESTION, filters={"status": "Pending", "kind": kind}, fields=SUGGESTION_FIELDS, order_by="creation desc", limit=count, ignore_permissions=True)
    return [suggestion_card(r) for r in rows]


def counts() -> dict:
    return {
        "suggestions": frappe.db.count(SUGGESTION, {"status": "Pending"}),
        "drafts": frappe.db.count(ARTICLE, {"status": "Draft"}),
    }


# --- access, settings and status ------------------------------------------------------
def _require_vendor() -> None:
    from reckon_saas_platform.api import check_app_permission

    if not check_app_permission():
        frappe.throw(frappe._("Not permitted"), frappe.PermissionError)


def _ready(settings) -> str:
    """Empty when the agent can use the AI, otherwise what to do first."""
    if not frappe.utils.cint(settings.get("seo_agent_enabled")):
        return "The SEO agent is switched off. Turn on **Enable SEO Agent** in SEO Agent Settings."
    if not settings.get_password("seo_agent_api_key", raise_exception=False) or not str(settings.get("seo_agent_model") or "").strip():
        return "I need an AI key and model first. Add them in SEO Agent Settings."
    return ""


@frappe.whitelist()
def status() -> dict:
    _require_vendor()
    settings = frappe.get_cached_doc(seo.SETTINGS)
    month = str(frappe.utils.nowdate())[:7]
    used = frappe.utils.cint(seo._setting("seo_agent_calls")) if seo._setting("seo_agent_month") == month else 0
    return {
        **counts(),
        "calls_used": used,
        "calls_cap": frappe.utils.cint(settings.get("seo_agent_monthly_call_cap") or 40),
        "setup": _ready(settings),
    }


# --- the conversation -----------------------------------------------------------------
def _reply(text: str, cards=None, chips=None) -> dict:
    return {"reply": text, "cards": cards or [], "chips": chips or []}


def _site(settings):
    base = marketing.site_base()
    modules = marketing.get_modules()
    pages = seo.collect_pages(base, modules, marketing.get_integrations(), marketing.get_profiles())
    return base, modules, pages


@frappe.whitelist()
def ask(message: str) -> dict:
    """Answer one line from the vendor. Returns ``{reply, cards, chips}``."""
    _require_vendor()
    message = re.sub(r"\s+", " ", str(message or "")).strip()[:600]
    request = detect_intent(message)
    intent = request["intent"]
    if intent == "help":
        return _reply(
            "I can look after your website's SEO. Tell me what you need, for example: show what is waiting for approval, "
            "find keyword gaps, improve page titles, suggest FAQs, or write a blog article about a topic. "
            "Nothing goes live until you approve or publish it.",
            chips=HELP_CHIPS,
        )
    if intent == "pending":
        cards = pending_cards()
        if not cards:
            return _reply("Nothing is waiting for you. Ask me to write something or find ideas.", chips=HELP_CHIPS[1:])
        total = counts()
        return _reply(
            f"You have {total['suggestions']} suggestion(s) and {total['drafts']} blog draft(s) waiting. Here are the newest:",
            cards=cards,
        )
    settings = frappe.get_cached_doc(seo.SETTINGS)
    if intent == "gaps":
        return _gaps(settings)
    setup = _ready(settings)
    if setup:
        return _reply(setup)
    try:
        base, modules, pages = _site(settings)
        keywords = seo_agent._lines(settings.get("seo_target_keywords"))
        if intent == "titles":
            made = seo_agent.draft_pages(settings, pages, keywords)
            return _reply(
                f"I drafted new text for {made} page(s). Approve the ones you like:" if made else "I found nothing worth changing right now.",
                cards=latest_suggestions("Title and Description", made),
            )
        if intent == "faqs":
            existing = [q for g in marketing.faq_groups(modules) for q, _a in g["faqs"]]
            made = seo_agent.draft_faqs(settings, pages, existing, keywords)
            return _reply(
                f"I wrote {made} new FAQ answer(s) from facts already on your site:" if made else "I have no new FAQ ideas that your site can support yet.",
                cards=latest_suggestions("FAQ", made),
            )
        if intent == "visibility":
            return _visibility(settings)
        return _article(settings, request, pages, modules, base)
    except seo_agent.AgentLimit as exc:
        return _reply(f"I stopped: {exc}. You can raise the Monthly AI Call Limit in SEO Agent Settings.")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SEO agent chat")
        return _reply("Something went wrong while asking the AI. It is logged; please try again in a moment.")


def _gaps(settings) -> dict:
    keywords = seo_agent._lines(settings.get("seo_target_keywords"))
    if not keywords:
        return _reply("Add your Target Keywords in SEO Agent Settings, one per line, and I will check them against your pages.")
    _base, _modules, pages = _site(settings)
    gaps = seo_agent.keyword_gaps(keywords, pages)
    if not gaps:
        return _reply(f"Good news: every one of your {len(keywords)} target keywords appears in a page title, heading or description.")
    return _reply(
        "No page covers these keywords yet:\n" + "\n".join(f"• {g}" for g in gaps),
        chips=[f"Write a blog article about {g}" for g in gaps[:3]],
    )


def _visibility(settings) -> dict:
    questions = seo_agent._lines(settings.get("seo_visibility_questions"))[:3]
    if not questions:
        return _reply("Add a few Questions to Ask AI Assistants in SEO Agent Settings, such as the questions your buyers type.")
    results = seo_agent.check_visibility(settings, questions)
    named = sum(1 for _q, ok in results if ok)
    lines = [f"{'Yes' if ok else 'No'}: {q}" for q, ok in results]
    return _reply(
        f"ReckonERP was named in {named} of {len(results)} answers (from the model's own knowledge, no web search):\n" + "\n".join(lines)
    )


def _article(settings, request: dict, pages, modules, base) -> dict:
    topic = request.get("topic") or ""
    if len(topic) < 6:
        return _reply("What should the article be about? For example: Write a blog article about planning delivery routes.")
    notes = str(settings.get("seo_blog_notes") or "").strip()[:2000]
    title, problem = blog_agent.draft_topic(
        settings,
        {"category": request["category"], "title": topic[:120], "keyword": topic[:80], "outline": ""},
        pages,
        modules,
        blog_agent.site_paths(modules),
        notes,
        base,
    )
    if not title:
        return _reply(f"I could not write a draft that passes my checks ({problem}). Try rephrasing the topic or make it more specific.")
    slug = frappe.get_all(ARTICLE, filters={"title": title}, fields=ARTICLE_FIELDS, limit=1, ignore_permissions=True)
    return _reply(
        f"Your {request['category'].lower()} is ready as a draft. Read it, then publish when you are happy. "
        "A promotion kit for LinkedIn, Facebook and outreach is saved on it.",
        cards=[article_card(slug[0])] if slug else [],
    )


# --- acting on a card -----------------------------------------------------------------
@frappe.whitelist()
def decide(doctype: str, name: str, action: str) -> dict:
    """Approve or reject a suggestion; publish or reject a blog draft."""
    _require_vendor()
    targets = {
        (SUGGESTION, "approve"): "Approved",
        (SUGGESTION, "reject"): "Rejected",
        (ARTICLE, "publish"): "Published",
        (ARTICLE, "reject"): "Rejected",
    }
    status = targets.get((doctype, action))
    if not status:
        frappe.throw(frappe._("Unknown action"))
    doc = frappe.get_doc(doctype, name)
    doc.status = status
    try:
        doc.save(ignore_permissions=True)
    except frappe.ValidationError as exc:
        return {"ok": False, "message": re.sub(r"<[^>]*>", "", str(exc))}
    done = {"Approved": "Approved. It is on the website now.", "Rejected": "Rejected.", "Published": "Published. It is on your blog now."}[status]
    if status == "Approved" and getattr(doc, "kind", "") == "Content Idea":
        done = "Saved as an approved idea. Ask me to write it when you are ready."
    return {"ok": True, "message": done, "status": status}
