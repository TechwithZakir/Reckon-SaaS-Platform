"""The public blog: articles, tutorials, feature guides and weekly updates.

Posts are **SEO Article** records. The SEO agent writes drafts; only a vendor user
turns a draft into a published post. Pages, RSS, the sitemap, ``llms.txt`` and
structured data all read the published posts, so publishing needs no other step.
"""

from __future__ import annotations

import html
import json
import re
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

import frappe

from reckon_saas_platform import marketing

DOCTYPE = "SEO Article"
BLOG = "/blog"
RSS = "/blog/rss.xml"
CACHE_KEY = "reckon_saas_blog_articles"
CATEGORIES = ("Article", "Tutorial", "Feature Guide", "Weekly Update")
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{2,78}")
LIST_FIELDS = ["name", "title", "summary", "category", "published_on", "modified", "related_module", "keywords"]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:78].strip("-")


def article_url(slug: str) -> str:
    return f"{BLOG}/{quote(slug)}"


def _date(value) -> str:
    text = str(value or "")[:10]
    return text if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else ""


def _row(row) -> dict:
    return {
        "slug": row.get("name"),
        "title": row.get("title") or "",
        "summary": row.get("summary") or "",
        "category": row.get("category") or "Article",
        "published": _date(row.get("published_on")) or _date(row.get("modified")),
        "modified": _date(row.get("modified")),
        "module": row.get("related_module") or "",
        "keywords": row.get("keywords") or "",
        "url": article_url(row.get("name") or ""),
    }


def get_articles(limit: int | None = None) -> list[dict]:
    """Published posts, newest first, without their text. Cached until a post is saved."""
    cached = frappe.cache.get_value(CACHE_KEY)
    if cached is None:
        cached = []
        try:
            if frappe.db.exists("DocType", DOCTYPE):
                rows = frappe.get_all(
                    DOCTYPE,
                    filters={"status": "Published"},
                    fields=LIST_FIELDS,
                    order_by="published_on desc, modified desc",
                    ignore_permissions=True,
                )
                cached = [_row(row) for row in rows if SLUG.fullmatch(row.get("name") or "")]
        except Exception:
            cached = []
        frappe.cache.set_value(CACHE_KEY, cached, expires_in_sec=600)
    return list(cached[:limit] if limit else cached)


def get_article(slug: str) -> dict | None:
    if not SLUG.fullmatch(slug or ""):
        return None
    try:
        rows = frappe.get_all(
            DOCTYPE,
            filters={"name": slug, "status": "Published"},
            fields=[*LIST_FIELDS, "body"],
            limit=1,
            ignore_permissions=True,
        )
    except Exception:
        return None
    if not rows:
        return None
    article = _row(rows[0])
    article["body"] = rows[0].get("body") or ""
    return article


def read_minutes(body: str) -> int:
    return max(1, round(len(re.findall(r"\w+", body or "")) / 200))


# --- Markdown, reduced to what an article needs and made safe ------------------------
_LINK = re.compile(r"\[([^\]\n]+)\]\((/[^\s)]*|https://[^\s)]+)\)")


def _inline(text: str) -> str:
    out = html.escape(text, quote=True)

    def link(match):
        label, url = match.group(1), match.group(2)
        if url.startswith("/"):
            return f'<a href="{url}">{label}</a>'
        return f'<a href="{url}" rel="nofollow noopener" target="_blank">{label}</a>'

    out = _LINK.sub(link, out)
    out = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", out)
    return re.sub(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])", r"<em>\1</em>", out)


def render_markdown(text: str) -> str:
    """Headings (# to ####, shown as h2 to h4), paragraphs, lists, code, bold, italic, links.

    Everything is escaped first, so stored text can never add markup of its own.
    Links may only be site-relative or https.
    """
    lines = str(text or "").replace("\r", "").split("\n")
    out: list[str] = []
    paragraph: list[str] = []
    items: list[str] = []
    list_tag = ""
    code: list[str] | None = None

    def flush_paragraph():
        if paragraph:
            out.append("<p>" + _inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def flush_list():
        nonlocal list_tag
        if items:
            out.append(f"<{list_tag}>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + f"</{list_tag}>")
            items.clear()
        list_tag = ""

    for line in lines:
        if line.strip().startswith("```"):
            if code is None:
                flush_paragraph()
                flush_list()
                code = []
            else:
                out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        heading = re.match(r"(#{1,4})\s+(.+)", line)
        bullet = re.match(r"\s*[-*]\s+(.+)", line)
        number = re.match(r"\s*\d+[.)]\s+(.+)", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(max(len(heading.group(1)), 2), 4)
            out.append(f"<h{level}>{_inline(heading.group(2).strip())}</h{level}>")
        elif bullet or number:
            flush_paragraph()
            tag = "ul" if bullet else "ol"
            if list_tag and list_tag != tag:
                flush_list()
            list_tag = tag
            items.append((bullet or number).group(1).strip())
        elif not line.strip():
            flush_paragraph()
            flush_list()
        else:
            flush_list()
            paragraph.append(line.strip())
    if code is not None:
        out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
    flush_paragraph()
    flush_list()
    return "\n".join(out)


# --- pages ---------------------------------------------------------------------------
def article_ld(base: str, article: dict) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": article["title"],
        "description": article["summary"],
        "url": f"{base}{article['url']}",
        "mainEntityOfPage": f"{base}{article['url']}",
        "datePublished": article["published"],
        "dateModified": article["modified"] or article["published"],
        "articleSection": article["category"],
        "inLanguage": "en",
        "image": f"{base}{marketing.LOGO_SOCIAL}",
        "author": {"@type": "Organization", "name": marketing.SITE_NAME},
        "publisher": {
            "@type": "Organization",
            "name": marketing.SITE_NAME,
            "logo": {"@type": "ImageObject", "url": f"{base}{marketing.LOGO_SOCIAL}"},
        },
    }
    if article["keywords"]:
        data["keywords"] = article["keywords"]
    return data


def blog_page(base: str, articles: list[dict]) -> dict:
    items = [
        {"@type": "BlogPosting", "headline": a["title"], "url": f"{base}{a['url']}", "datePublished": a["published"]}
        for a in articles[:20]
    ]
    page = marketing.make_page(
        base,
        path=BLOG,
        title="ReckonERP blog: ERP guides, tutorials and weekly updates",
        description="Practical ERP and AI guides, tutorials, feature explainers and weekly updates "
        "from ReckonERP for distributors, accountants and sales teams.",
        h1="ReckonERP blog",
        trail=[("Home", marketing.HOME), ("Blog", BLOG)],
        articles=articles,
        categories=[c for c in CATEGORIES if any(a["category"] == c for a in articles)],
        noindex=not articles,
        extra_ld=[{"@context": "https://schema.org", "@type": "Blog", "name": "ReckonERP blog", "url": f"{base}{BLOG}", "blogPost": items}],
    )
    return page


def article_page(base: str, article: dict, articles: list[dict]) -> dict:
    related = [a for a in articles if a["slug"] != article["slug"]]
    same = [a for a in related if a["module"] and a["module"] == article["module"]] or related
    return marketing.make_page(
        base,
        path=article["url"],
        title=f"{article['title']} | ReckonERP",
        description=article["summary"],
        h1=article["title"],
        trail=[("Home", marketing.HOME), ("Blog", BLOG), (article["title"], article["url"])],
        extra_ld=[article_ld(base, article)],
        article=article,
        article_html=render_markdown(article.get("body", "")),
        minutes=read_minutes(article.get("body", "")),
        related=same[:3],
    )


def rss_xml(base: str, articles: list[dict]) -> str:
    items = "".join(
        f"<item><title>{xml_escape(a['title'])}</title><link>{xml_escape(base + a['url'])}</link>"
        f"<guid isPermaLink=\"true\">{xml_escape(base + a['url'])}</guid>"
        f"<description>{xml_escape(a['summary'])}</description>"
        f"<category>{xml_escape(a['category'])}</category>"
        + (f"<pubDate>{_rfc822(a['published'])}</pubDate>" if a["published"] else "")
        + "</item>"
        for a in articles[:30]
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
        f"<title>{xml_escape(marketing.SITE_NAME)} blog</title><link>{xml_escape(base + BLOG)}</link>"
        "<description>ERP guides, tutorials, feature explainers and weekly updates.</description>"
        f"<language>en</language>{items}</channel></rss>\n"
    )


def _rfc822(day: str) -> str:
    from datetime import date

    try:
        year, month, dom = (int(part) for part in day.split("-"))
        return date(year, month, dom).strftime("%a, %d %b %Y 00:00:00 +0000")
    except ValueError:
        return ""


def dumps(data) -> str:
    return json.dumps(data, ensure_ascii=False)
