"""Header banners for module pages.

The five modules the platform ships have a drawn picture (``scripts/make_module_banners.py``).
Any other module gets a generated SVG that is unique to its key, so a newly installed module
never shows a blank header or borrows another module's picture.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

IMAGE_DIR = "/assets/reckon_saas_platform/images/banners"
FILES = Path(__file__).parent / "public" / "images" / "banners"
KEY = re.compile(r"[a-z][a-z0-9_]{1,59}")
SIZE = (1600, 480)


def drawn(key: str) -> bool:
    return bool(KEY.fullmatch(key or "")) and (FILES / f"{key}.webp").exists()


def banner(key: str, name: str) -> dict:
    """``{src, og, alt, width, height}`` for a module page header."""
    if drawn(key):
        return {
            "src": f"{IMAGE_DIR}/{key}.webp",
            "og": f"{IMAGE_DIR}/{key}-og.png" if (FILES / f"{key}-og.png").exists() else "",
            "alt": f"{name} module illustration",
            "width": SIZE[0],
            "height": SIZE[1],
        }
    return {
        "src": "data:image/svg+xml;charset=utf-8," + quote(banner_svg(key), safe="/:=,;()' "),
        "og": "",
        "alt": f"{name} module illustration",
        "width": SIZE[0],
        "height": SIZE[1],
    }


def _hues(key: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return digest[0] * 360 // 256, digest[1] % 40 + 20, digest[2]


def banner_svg(key: str) -> str:
    """A banner that is the same every time for ``key`` and different from every other key."""
    key = key if KEY.fullmatch(key or "") else "module"
    hue, spread, seed = _hues(key)
    h2 = (hue + spread + 25) % 360
    digest = hashlib.sha256(("shapes:" + key).encode("utf-8")).digest()
    shapes = []
    for i in range(7):
        cx = 760 + digest[i * 3] * 3
        cy = 40 + digest[i * 3 + 1] * 1.5
        r = 28 + digest[i * 3 + 2] % 70
        opacity = 0.10 + (digest[i * 3 + 2] % 20) / 100
        if i % 2:
            shapes.append(f'<rect x="{cx - r:.0f}" y="{cy - r:.0f}" width="{r * 2}" height="{r * 1.3:.0f}" rx="18" fill="#fff" fill-opacity="{opacity:.2f}"/>')
        else:
            shapes.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="#fff" fill-opacity="{opacity:.2f}"/>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE[0]} {SIZE[1]}" width="{SIZE[0]}" height="{SIZE[1]}" role="img" '
        f'aria-label="{escape(key)} module illustration"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="hsl({hue} 70% 28%)"/><stop offset="1" stop-color="hsl({h2} 75% 45%)"/></linearGradient></defs>'
        f'<rect width="{SIZE[0]}" height="{SIZE[1]}" fill="url(#g)"/>{"".join(shapes)}'
        f'<path d="M0 {400 - seed % 60} Q 400 {300 + seed % 80} 800 {390 - seed % 40} T 1600 {360 - seed % 70} V480 H0Z" fill="#fff" fill-opacity=".08"/></svg>'
    )
