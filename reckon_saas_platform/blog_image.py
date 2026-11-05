"""Cover images for blog posts, drawn by the platform itself.

Claude and the other text models cannot paint pictures, so each cover is drawn
here with Pillow: a branded gradient, the title, the post's kind and a small
illustration that fits it (steps for a tutorial, a grid for a feature guide, a
page for an article, bars for a weekly update). It costs no AI call, looks the
same every time, and is saved as a normal public File on the post.
"""

from __future__ import annotations

import io
from pathlib import Path

import frappe

from reckon_saas_platform import blog

SIZE = (1200, 630)
LOGO_PATH = Path(__file__).parent / "public" / "images" / "reckonerp-logo.webp"
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "/Library/Fonts/Arial Bold.ttf",
)
THEMES = {
    "Tutorial": ((11, 120, 171), (19, 155, 217)),
    "Feature Guide": ((76, 29, 149), (19, 155, 217)),
    "Article": ((11, 31, 58), (14, 116, 144)),
    "Weekly Update": ((11, 100, 80), (19, 155, 217)),
}


def _font(size: int):
    from PIL import ImageFont

    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _wrap(draw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return [*lines, line] if line else lines


def _fit_title(draw, title: str, width: int, max_lines: int = 4):
    for size in (74, 66, 58, 52, 46, 40):
        font = _font(size)
        lines = _wrap(draw, title, font, width)
        if len(lines) <= max_lines:
            return font, lines, size
    return font, lines[:max_lines], size


def _motif(draw, kind: str, x: int, y: int) -> None:
    """A simple illustration in translucent white, about 360 by 360."""
    ink, soft = (255, 255, 255, 230), (255, 255, 255, 70)
    if kind == "Tutorial":
        for i in range(3):
            top = y + 250 - i * 90
            draw.rounded_rectangle((x + i * 120, top, x + i * 120 + 100, y + 340), 18, fill=soft)
            draw.ellipse((x + i * 120 + 25, top - 34, x + i * 120 + 75, top + 16), fill=ink)
    elif kind == "Feature Guide":
        for r in range(2):
            for c in range(2):
                fill = (107, 220, 58, 235) if (r, c) == (0, 1) else soft
                draw.rounded_rectangle((x + c * 170, y + 40 + r * 170, x + c * 170 + 150, y + 40 + r * 170 + 150), 28, fill=fill)
    elif kind == "Weekly Update":
        for i, h in enumerate((90, 160, 120, 230, 190)):
            draw.rounded_rectangle((x + i * 72, y + 340 - h, x + i * 72 + 50, y + 340), 12, fill=ink if i == 3 else soft)
        draw.rounded_rectangle((x, y, x + 340, y + 56), 14, fill=soft)
    else:
        draw.rounded_rectangle((x + 40, y, x + 300, y + 340), 26, fill=soft)
        for i in range(5):
            width = 190 if i % 2 == 0 else 140
            draw.rounded_rectangle((x + 75, y + 50 + i * 54, x + 75 + width, y + 68 + i * 54), 9, fill=ink if i == 0 else (255, 255, 255, 150))


def make_cover(title: str, category: str) -> bytes:
    """The cover as WebP bytes (1200 by 630)."""
    from PIL import Image, ImageDraw

    start, end = THEMES.get(category, THEMES["Article"])
    width, height = SIZE
    base = Image.new("RGB", SIZE, start)
    pixels = base.load()
    for yy in range(height):
        for xx in range(width):
            t = (xx / width) * 0.7 + (yy / height) * 0.3
            pixels[xx, yy] = tuple(int(start[i] + (end[i] - start[i]) * t) for i in range(3))
    canvas = base.convert("RGBA")
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    glow = ImageDraw.Draw(layer)
    glow.ellipse((860, -140, 1340, 340), fill=(255, 255, 255, 26))
    glow.ellipse((-160, 420, 300, 820), fill=(255, 255, 255, 20))
    canvas.alpha_composite(layer)

    art = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    _motif(ImageDraw.Draw(art), category, 800, 130)
    canvas.alpha_composite(art)

    draw = ImageDraw.Draw(canvas)
    label = (category or "Article").upper()
    label_font = _font(26)
    label_w = int(draw.textlength(label, font=label_font))
    draw.rounded_rectangle((70, 70, 70 + label_w + 44, 124), 27, fill=(255, 255, 255, 235))
    draw.text((92, 80), label, font=label_font, fill=(11, 31, 58, 255))
    font, lines, size = _fit_title(draw, title.strip(), 640)
    y = 168
    for line in lines:
        draw.text((70, y), line, font=font, fill="white")
        y += int(size * 1.18)
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo = logo.resize((round(logo.width * 70 / logo.height), 70))
        draw.rounded_rectangle((60, 520, 60 + logo.width + 36, 600), 20, fill=(255, 255, 255, 240))
        canvas.alpha_composite(logo, (78, 525))
    except OSError:
        pass
    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="WEBP", quality=86, method=6)
    return out.getvalue()


def attach_cover(slug: str, title: str, category: str) -> str:
    """Draw the cover, save it as a public File on the post and return its URL."""
    content = make_cover(title, category)
    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": f"{slug}-cover.webp",
            "content": content,
            "is_private": 0,
            "attached_to_doctype": blog.DOCTYPE,
            "attached_to_name": slug,
            "attached_to_field": "cover_image",
        }
    )
    file_doc.insert(ignore_permissions=True)
    url = str(file_doc.file_url or "")
    return url if blog.COVER_FILE.fullmatch(url) else ""


@frappe.whitelist()
def generate_cover(name: str) -> str:
    """Button on SEO Article: draw (or redraw) the cover for this post."""
    if not frappe.has_permission(blog.DOCTYPE, "write"):
        frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
    doc = frappe.get_doc(blog.DOCTYPE, name)
    url = attach_cover(doc.name, doc.title, doc.category)
    if url:
        doc.db_set("cover_image", url)
        frappe.cache.delete_value(blog.CACHE_KEY)
    return url
