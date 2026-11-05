"""AI assistant for the public site's SEO: it proposes, a person approves.

Each run (weekly, or on demand) does three things:

1. **Coverage check** (no AI): compares the vendor's target keywords with the
   pages' titles and headings and lists keywords no page answers.
2. **Drafts** (AI): proposes better titles and descriptions for the weakest pages
   and new FAQ answers, written only from facts the site already states.
3. **AI-answer visibility** (AI): asks the model the vendor's target questions
   and records whether ReckonERP is mentioned. The model answers from its own
   knowledge, without browsing, so this is a signal and not a ranking.

Everything the agent writes is a **SEO Suggestion** in status *Pending*. Nothing
changes on the website until a vendor user approves it, and every call counts
against a monthly cap. The agent is off until it is enabled and given an API key.
"""

from __future__ import annotations

import json
import re

import frappe

from reckon_saas_platform import marketing, seo

SETTINGS = seo.SETTINGS
SUGGESTION = "SEO Suggestion"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MAX_PAGES_PER_DRAFT = 8
MAX_FAQ_PER_RUN = 3
MAX_VISIBILITY_QUESTIONS = 5

# Claims a search or AI engine cannot verify, and the framework name, never go on the site.
FORBIDDEN = re.compile(r"\b(best|number one|no\.? ?1|#1|guaranteed?|cheapest|frappe)\b", re.I)


class AgentLimit(Exception):
    """The monthly call cap is reached or the agent is not configured."""


# --- validation of what the model returns -----------------------------------------
def _clean(text, limit: int) -> str:
    text = re.sub(r"<[^>]*>", "", str(text or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def valid_title(text: str) -> bool:
    return 20 <= len(text) <= 70 and not FORBIDDEN.search(text)


def valid_description(text: str) -> bool:
    return 70 <= len(text) <= 160 and not FORBIDDEN.search(text)


def valid_faq(question: str, answer: str) -> bool:
    return (
        10 <= len(question) <= 160
        and question.endswith("?")
        and 40 <= len(answer) <= 600
        and not FORBIDDEN.search(question + " " + answer)
    )


def parse_json_list(text: str) -> list[dict]:
    """The first JSON array in a model reply, as dicts; anything else is ignored."""
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except ValueError:
        return []
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


# --- settings, cap and model calls ----------------------------------------------
def _settings():
    return frappe.get_cached_doc(SETTINGS)


def _lines(text) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _month() -> str:
    return str(frappe.utils.nowdate())[:7]


def _spend_call(settings) -> None:
    cap = frappe.utils.cint(settings.get("seo_agent_monthly_call_cap") or 40)
    month = _month()
    used = frappe.utils.cint(seo._setting("seo_agent_calls")) if seo._setting("seo_agent_month") == month else 0
    if used >= cap:
        raise AgentLimit(f"Monthly call cap of {cap} reached")
    seo._store(seo_agent_month=month, seo_agent_calls=used + 1)


def call_model(settings, prompt: str, max_tokens: int = 1500) -> str:
    """One request to the configured AI provider. Raises AgentLimit when not allowed."""
    key = settings.get_password("seo_agent_api_key", raise_exception=False)
    model = str(settings.get("seo_agent_model") or "").strip()
    if not key or not model:
        raise AgentLimit("AI key or model not set")
    _spend_call(settings)
    import requests

    if (settings.get("seo_agent_provider") or "Anthropic") == "Anthropic":
        response = requests.post(
            ANTHROPIC_URL,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]},
            timeout=90,
        )
        response.raise_for_status()
        return "".join(part.get("text", "") for part in response.json().get("content", []))
    base = str(settings.get("seo_agent_base_url") or "https://api.openai.com/v1").rstrip("/")
    if not base.startswith("https://") and not base.startswith("http://localhost"):
        raise AgentLimit("The AI address must be https")
    response = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]},
        timeout=90,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# --- steps ----------------------------------------------------------------------
def keyword_gaps(keywords: list[str], pages: list[dict]) -> list[str]:
    """Target keywords whose words never appear together in any page title or heading."""
    gaps = []
    for keyword in keywords:
        words = [w for w in re.findall(r"[a-z0-9]+", keyword.lower()) if len(w) > 2]
        if not words:
            continue
        covered = any(
            all(w in (page["title"] + " " + page["h1"] + " " + page["description"]).lower() for w in words)
            for page in pages
        )
        if not covered:
            gaps.append(keyword)
    return gaps


def _site_facts(pages: list[dict]) -> str:
    lines = []
    for page in pages:
        lines.append(f"- {page['path']}: {page['title']} | {page['description']}")
    return "\n".join(lines)


def _draft_prompt(pages: list[dict], keywords: list[str]) -> str:
    return (
        "You improve search titles and meta descriptions for the public website of ReckonERP, "
        "a cloud ERP with built-in AI. Write for people first and search engines second.\n"
        f"Target keywords:\n{chr(10).join('- ' + k for k in keywords) or '- (none given)'}\n\n"
        f"Current pages (path: title | description):\n{_site_facts(pages)}\n\n"
        f"Pick up to {MAX_PAGES_PER_DRAFT} pages that would gain most and rewrite their title "
        "(20-70 characters) and description (70-160 characters). Use only what the pages already "
        "say. Do not claim anything is the best, number one, cheapest or guaranteed. Never mention "
        "the Frappe framework. Keep the ReckonERP name. Reply with ONLY a JSON array of objects: "
        '[{"path": "/modules", "title": "...", "description": "...", "reason": "one sentence"}]'
    )


def _faq_prompt(pages: list[dict], questions: list[str], keywords: list[str]) -> str:
    return (
        "Suggest new FAQ entries for the ReckonERP website that match what buyers search for. "
        "Answer ONLY with facts stated in the page list below; if a fact is not there, do not "
        "write that question.\n"
        f"Target keywords:\n{chr(10).join('- ' + k for k in keywords) or '- (none given)'}\n\n"
        f"Existing questions (do not repeat):\n{chr(10).join('- ' + q for q in questions)}\n\n"
        f"Facts (page: title | description):\n{_site_facts(pages)}\n\n"
        f"Reply with ONLY a JSON array of up to {MAX_FAQ_PER_RUN} objects "
        '[{"question": "... ?", "answer": "40-600 characters", "reason": "one sentence"}]. '
        "No prices, no claims of being the best, never mention the Frappe framework."
    )


def _exists(**filters) -> bool:
    return bool(frappe.db.exists(SUGGESTION, filters))


def _add(**values):
    doc = frappe.get_doc({"doctype": SUGGESTION, "status": "Pending", "source": "AI", **values})
    doc.insert(ignore_permissions=True)
    return doc


def draft_pages(settings, pages: list[dict], keywords: list[str]) -> int:
    known = {page["path"]: page for page in pages}
    created = 0
    for row in parse_json_list(call_model(settings, _draft_prompt(pages, keywords), 1800))[:MAX_PAGES_PER_DRAFT]:
        path = str(row.get("path") or "")
        title, description = _clean(row.get("title"), 80), _clean(row.get("description"), 200)
        if path not in known or path == marketing.SIGNUP or not (valid_title(title) and valid_description(description)):
            continue
        if title == known[path]["title"] and description == known[path]["description"]:
            continue
        if _exists(kind="Title and Description", page_path=path, proposed_title=title, status=["in", ["Pending", "Approved"]]):
            continue
        _add(
            kind="Title and Description",
            page_path=path,
            current_title=known[path]["title"],
            current_description=known[path]["description"],
            proposed_title=title,
            proposed_description=description,
            reason=_clean(row.get("reason"), 300),
        )
        created += 1
    return created


def draft_faqs(settings, pages: list[dict], questions: list[str], keywords: list[str]) -> int:
    created = 0
    asked = {q.lower() for q in questions}
    for row in parse_json_list(call_model(settings, _faq_prompt(pages, questions, keywords), 1500))[:MAX_FAQ_PER_RUN]:
        question, answer = _clean(row.get("question"), 200), _clean(row.get("answer"), 700)
        if not valid_faq(question, answer) or question.lower() in asked or _exists(kind="FAQ", question=question):
            continue
        _add(kind="FAQ", page_path=marketing.FAQ, question=question, answer=answer, reason=_clean(row.get("reason"), 300))
        created += 1
    return created


def check_visibility(settings, questions: list[str]) -> list[tuple[str, bool]]:
    results = []
    for question in questions[:MAX_VISIBILITY_QUESTIONS]:
        answer = call_model(settings, f"{question}\nAnswer in under 150 words and name specific products.", 400)
        results.append((question, "reckonerp" in re.sub(r"[^a-z]", "", answer.lower())))
    return results


def run_agent(trigger: str = "weekly") -> dict:
    """Run one pass. Never raises; the outcome is written to SaaS Platform Settings."""
    try:
        if not frappe.db.exists("DocType", SETTINGS):
            return {}
        settings = _settings()
        if not frappe.utils.cint(settings.get("seo_agent_enabled")):
            return {"skipped": "disabled"}
        base = marketing.site_base()
        modules = marketing.get_modules()
        pages = seo.collect_pages(base, modules, marketing.get_integrations(), marketing.get_profiles())
        keywords = _lines(settings.get("seo_target_keywords"))
        questions = _lines(settings.get("seo_visibility_questions"))
        report = [f"Run ({trigger}), {len(pages)} pages."]

        gaps = keyword_gaps(keywords, pages)
        for keyword in gaps:
            if not _exists(kind="Content Idea", question=keyword, status=["in", ["Pending", "Approved"]]):
                _add(kind="Content Idea", source="Audit", page_path=marketing.HOME, question=keyword,
                     reason="No page title, heading or description contains these words together.")
        report.append(f"Keywords with no matching page: {', '.join(gaps) if gaps else 'none'}.")

        try:
            drafted = draft_pages(settings, pages, keywords)
            existing = [q for g in marketing.faq_groups(modules) for q, _a in g["faqs"]]
            faqs = draft_faqs(settings, pages, existing, keywords)
            report.append(f"New suggestions waiting for approval: {drafted} page text, {faqs} FAQ.")
            if questions:
                seen = check_visibility(settings, questions)
                hits = sum(1 for _q, ok in seen if ok)
                report.append(f"AI-answer check (model knowledge, no browsing): ReckonERP named in {hits} of {len(seen)} answers.")
                report += [f"  {'yes' if ok else 'no '}: {q}" for q, ok in seen]
        except AgentLimit as exc:
            report.append(f"Stopped: {exc}.")
        seo._store(seo_agent_last_run=frappe.utils.now_datetime(), seo_agent_report="\n".join(report))
        return {"report": report}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SEO agent")
        return {}


def run_agent_weekly() -> None:
    run_agent("weekly")


@frappe.whitelist()
def run_agent_now() -> dict:
    """Button on SaaS Platform Settings."""
    if not frappe.has_permission(SETTINGS, "write"):
        frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
    return {"report": (run_agent("manual") or {}).get("report", [])}
