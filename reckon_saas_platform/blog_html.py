"""Safe HTML for rich-text blog posts.

The article editor stores HTML. Whatever is stored, the website only ever outputs
what this allow-list lets through: headings, paragraphs, lists, links, images,
code, quotes and simple tables, with no scripts, no event handlers and no
``javascript:`` links. Older posts written as plain Markdown still render.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

ALLOWED = frozenset(
    "p h2 h3 h4 ul ol li strong em u a code pre blockquote br hr img table thead tbody tr th td figure figcaption".split()
)
RENAMED = {"b": "strong", "i": "em", "h1": "h2", "h5": "h4", "h6": "h4", "dl": "ul", "dt": "li", "dd": "li"}
UNWRAP = frozenset("div span section article font small big center label".split())
DROP_WITH_CONTENT = frozenset("script style iframe object embed form input button textarea select noscript svg math template".split())
VOID = frozenset({"br", "hr", "img"})
SAFE_LINK = re.compile(r"(/(?!/)[^\s]*|https://[^\s]+)")
SAFE_IMAGE = re.compile(r"(/files/[^\s]+|/assets/[^\s]+|https://[^\s]+)")
NUMBER = re.compile(r"\d{1,4}")
LOOKS_LIKE_HTML = re.compile(r"<\s*(p|h[1-6]|ul|ol|li|div|br|blockquote|table|img|pre)\b", re.I)


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.open: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        tag = RENAMED.get(tag, tag)
        if tag in DROP_WITH_CONTENT or tag in {"svg", "math"}:
            self.skip += 1
            return
        if self.skip or tag in UNWRAP or tag not in ALLOWED:
            return
        attributes = self._attributes(tag, dict(attrs))
        self.out.append(f"<{tag}{attributes}>")
        if tag not in VOID:
            self.open.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = RENAMED.get(tag, tag)
        if tag in DROP_WITH_CONTENT or tag in {"svg", "math"}:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag not in self.open:
            return
        while self.open:
            top = self.open.pop()
            self.out.append(f"</{top}>")
            if top == tag:
                break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))

    @staticmethod
    def _attributes(tag: str, attrs: dict) -> str:
        parts = []
        if tag == "a":
            href = (attrs.get("href") or "").strip()
            if SAFE_LINK.fullmatch(href):
                parts.append(f'href="{html.escape(href, quote=True)}"')
                if href.startswith("https://"):
                    parts.append('rel="nofollow noopener" target="_blank"')
        elif tag == "img":
            src = (attrs.get("src") or "").strip()
            if not SAFE_IMAGE.fullmatch(src):
                return ' data-removed="1"'
            parts.append(f'src="{html.escape(src, quote=True)}"')
            parts.append(f'alt="{html.escape(attrs.get("alt") or "", quote=True)}"')
            for name in ("width", "height"):
                if NUMBER.fullmatch(str(attrs.get(name) or "")):
                    parts.append(f'{name}="{attrs[name]}"')
            parts.append('loading="lazy" decoding="async"')
        elif tag in {"td", "th"}:
            for name in ("colspan", "rowspan"):
                if NUMBER.fullmatch(str(attrs.get(name) or "")):
                    parts.append(f'{name}="{attrs[name]}"')
        return (" " + " ".join(parts)) if parts else ""


def sanitize_html(text: str) -> str:
    """The allow-listed HTML for ``text``; everything else is removed or escaped."""
    cleaner = _Cleaner()
    cleaner.feed(str(text or ""))
    cleaner.close()
    while cleaner.open:
        cleaner.out.append(f"</{cleaner.open.pop()}>")
    result = "".join(cleaner.out)
    return re.sub(r"<img data-removed=\"1\">", "", result)


def plain_text(text: str) -> str:
    """The words of a post with any HTML tags taken out."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", str(text or "")))).strip()


def is_html(text: str) -> bool:
    return bool(LOOKS_LIKE_HTML.search(str(text or "")))
