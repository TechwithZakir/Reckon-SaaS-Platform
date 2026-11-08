"""Topic illustrations and colours for blog covers.

Each style is a small drawing, about 360 by 360, that says what the post is about (a cloud over a server,
a spreadsheet growing into modules, a delivery route, three ways to host, ...) and its own colour pair, so
ten posts on ten topics do not look alike. Drawn with Pillow primitives; no fonts needed except the currency
glyphs on the globe.
"""

from __future__ import annotations

INK = (255, 255, 255, 235)
SOFT = (255, 255, 255, 80)
MID = (255, 255, 255, 150)
GREEN = (107, 220, 58, 240)
AMBER = (250, 204, 21, 240)


def _rr(d, box, fill, r=16):
    d.rounded_rectangle(box, r, fill=fill)


def cloud(d, x, y):
    for cx, cy, r in ((110, 95, 52), (185, 70, 68), (255, 100, 48)):
        d.ellipse((x + cx - r, y + cy - r, x + cx + r, y + cy + r), fill=MID)
    _rr(d, (x + 60, y + 100, x + 305, y + 150), MID, 24)
    for gx in (150, 210):
        for gy in range(160, 205, 14):
            d.rounded_rectangle((x + gx, gy + y, x + gx + 6, gy + y + 8), 3, fill=SOFT)
    _rr(d, (x + 90, y + 215, x + 270, y + 345), SOFT, 22)
    for i in range(3):
        _rr(d, (x + 112, y + 235 + i * 36, x + 248, y + 257 + i * 36), INK if i == 0 else MID, 8)
        d.ellipse((x + 226, y + 240 + i * 36, x + 238, y + 252 + i * 36), fill=GREEN if i == 0 else SOFT)


def spreadsheet(d, x, y):
    for r in range(3):
        for c in range(3):
            _rr(d, (x + c * 36, y + 150 + r * 36, x + c * 36 + 30, y + 150 + r * 36 + 30), SOFT if (r + c) % 2 else MID, 5)
    d.polygon([(x + 118, y + 215), (x + 136, y + 232), (x + 118, y + 250)], fill=INK)
    _rr(d, (x + 145, y + 95, x + 245, y + 330), MID, 16)
    for i in range(6):
        _rr(d, (x + 160, y + 120 + i * 32, x + 230 - (i % 3) * 22, y + 132 + i * 32), INK if i == 0 else SOFT, 5)
    d.polygon([(x + 255, y + 215), (x + 273, y + 232), (x + 255, y + 250)], fill=INK)
    for r in range(2):
        for c in range(2):
            _rr(d, (x + 285 + c * 38, y + 175 + r * 38, x + 285 + c * 38 + 32, y + 175 + r * 38 + 32), GREEN if (r, c) == (0, 1) else INK, 8)


def route(d, x, y):
    pts = [(20, 300), (110, 220), (200, 260), (290, 140), (340, 60)]
    d.line([(x + a, y + b) for a, b in pts], fill=MID, width=9, joint="curve")
    for i, (a, b) in enumerate(pts):
        d.ellipse((x + a - 20, y + b - 20, x + a + 20, y + b + 20), fill=GREEN if i == len(pts) - 1 else INK)
        d.ellipse((x + a - 8, y + b - 8, x + a + 8, y + b + 8), fill=(20, 60, 90, 255))
    _rr(d, (x + 120, y + 300, x + 250, y + 350), INK, 10)
    _rr(d, (x + 250, y + 318, x + 300, y + 350), MID, 10)
    for wx in (150, 270):
        d.ellipse((x + wx - 16, y + 335, x + wx + 16, y + 367), fill=(20, 60, 90, 255), outline=INK, width=4)
    _rr(d, (x + 30, y + 20, x + 190, y + 100), SOFT, 16)
    _rr(d, (x + 48, y + 40, x + 150, y + 52), INK, 5)
    _rr(d, (x + 48, y + 66, x + 120, y + 78), MID, 5)


def servers(d, x, y):
    for i in range(3):
        _rr(d, (x + 0, y + 190 + i * 50, x + 100, y + 232 + i * 50), MID, 10)
        d.ellipse((x + 76, y + 204 + i * 50, x + 88, y + 216 + i * 50), fill=GREEN if i == 0 else SOFT)
    _rr(d, (x + 125, y + 90, x + 235, y + 340), INK, 18)
    for i in range(5):
        _rr(d, (x + 142, y + 115 + i * 46, x + 218, y + 135 + i * 46), (20, 60, 90, 120), 6)
    d.ellipse((x + 196, y + 120, x + 208, y + 132), fill=GREEN)
    d.polygon([(x + 255, y + 190), (x + 305, y + 130), (x + 355, y + 190)], fill=MID)
    _rr(d, (x + 265, y + 190, x + 345, y + 340), SOFT, 6)
    _rr(d, (x + 292, y + 270, x + 318, y + 340), INK, 6)


def people(d, x, y):
    for i, cx in enumerate((70, 170, 270)):
        d.ellipse((x + cx - 40, y + 70, x + cx + 40, y + 150), fill=INK if i == 1 else MID)
        d.pieslice((x + cx - 62, y + 165, x + cx + 62, y + 290), 180, 360, fill=INK if i == 1 else MID)
    _rr(d, (x + 20, y + 300, x + 190, y + 350), SOFT, 14)
    _rr(d, (x + 36, y + 316, x + 130, y + 328), INK, 5)
    for c in range(4):
        _rr(d, (x + 215 + c * 36, y + 305, x + 215 + c * 36 + 26, y + 327), GREEN if c == 2 else MID, 5)
    d.ellipse((x + 300, y + 20, x + 350, y + 70), fill=AMBER)


def crm(d, x, y):
    _rr(d, (x + 0, y + 70, x + 150, y + 290), MID, 20)
    d.ellipse((x + 20, y + 90, x + 62, y + 132), fill=INK)
    for i in range(4):
        _rr(d, (x + 20, y + 160 + i * 30, x + 130 - (i % 2) * 30, y + 172 + i * 30), INK if i == 0 else SOFT, 5)
    _rr(d, (x + 210, y + 70, x + 360, y + 290), MID, 20)
    d.ellipse((x + 300, y + 90, x + 342, y + 132), fill=GREEN)
    d.line([(x + 312, y + 112), (x + 320, y + 122), (x + 334, y + 100)], fill=(10, 50, 20, 255), width=5)
    for i in range(4):
        _rr(d, (x + 230, y + 160 + i * 30, x + 340 - (i % 2) * 30, y + 172 + i * 30), INK if i == 0 else SOFT, 5)
    d.line([(x + 150, y + 180), (x + 210, y + 180)], fill=INK, width=8)
    for cx in (165, 195):
        d.ellipse((x + cx - 10, y + 170, x + cx + 10, y + 190), fill=AMBER)


def stack(d, x, y):
    for col, (cx, layers) in enumerate(((10, 5), (130, 4), (250, 3))):
        for i in range(layers):
            lit = col == 1 and i == layers - 1
            _rr(d, (x + cx, y + 340 - (i + 1) * 58, x + cx + 100, y + 340 - i * 58 - 8), GREEN if lit else (MID if i % 2 else SOFT), 12)
        d.ellipse((x + cx + 36, y + 340 - layers * 58 - 44, x + cx + 64, y + 340 - layers * 58 - 16), fill=INK)


def ai(d, x, y):
    import math

    cx, cy = x + 180, y + 190
    nodes = []
    for i in range(6):
        ang = math.radians(60 * i - 90)
        nodes.append((cx + 135 * math.cos(ang), cy + 135 * math.sin(ang)))
    for nx, ny in nodes:
        d.line([(cx, cy), (nx, ny)], fill=MID, width=6)
    for i, (nx, ny) in enumerate(nodes):
        d.ellipse((nx - 26, ny - 26, nx + 26, ny + 26), fill=INK if i % 2 == 0 else MID)
    d.ellipse((cx - 62, cy - 62, cx + 62, cy + 62), fill=GREEN)
    d.polygon([(cx, cy - 38), (cx + 12, cy - 12), (cx + 38, cy), (cx + 12, cy + 12), (cx, cy + 38), (cx - 12, cy + 12), (cx - 38, cy), (cx - 12, cy - 12)], fill=(10, 50, 20, 255))


def privacy(d, x, y):
    d.arc((x + 120, y + 70, x + 240, y + 230), 180, 360, fill=INK, width=22)
    d.line([(x + 130, y + 150), (x + 130, y + 210)], fill=INK, width=22)
    d.line([(x + 230, y + 150), (x + 230, y + 210)], fill=INK, width=22)
    _rr(d, (x + 95, y + 190, x + 265, y + 340), INK, 24)
    d.ellipse((x + 163, y + 235, x + 197, y + 269), fill=(20, 80, 80, 255))
    _rr(d, (x + 171, y + 262, x + 189, y + 304), (20, 80, 80, 255), 6)
    for cx, cy, r in ((20, 90, 24), (50, 78, 32), (82, 92, 22)):
        d.ellipse((x + cx - r, y + cy - r, x + cx + r, y + cy + r), fill=MID)
    _rr(d, (x + 290, y + 250, x + 355, y + 340), SOFT, 10)
    d.ellipse((x + 312, y + 268, x + 324, y + 280), fill=GREEN)


def globe(d, x, y):
    cx, cy, r = x + 180, y + 185, 125
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=INK, width=8)
    d.ellipse((cx - 55, cy - r, cx + 55, cy + r), outline=MID, width=6)
    d.line([(cx - r, cy), (cx + r, cy)], fill=MID, width=6)
    d.arc((cx - r, cy - 60, cx + r, cy + 60), 0, 180, fill=SOFT, width=5)
    from reckon_saas_platform.blog_image import _font

    font = _font(44)
    for (gx, gy), glyph, fill in (((20, 40), "$", INK), ((300, 70), "€", AMBER), ((310, 280), "A", GREEN)):
        d.ellipse((x + gx - 6, y + gy - 6, x + gx + 66, y + gy + 66), fill=fill)
        d.text((x + gx + 14, y + gy + 4), glyph, font=font, fill=(20, 40, 70, 255))


# style -> (gradient start, gradient end, drawing)
STYLES = {
    "cloud": ((14, 116, 144), (56, 189, 248), cloud),
    "spreadsheet": ((22, 101, 52), (132, 204, 22), spreadsheet),
    "route": ((30, 64, 175), (14, 165, 233), route),
    "servers": ((67, 56, 202), (139, 92, 246), servers),
    "people": ((154, 52, 18), (245, 158, 11), people),
    "crm": ((15, 23, 42), (79, 70, 229), crm),
    "stack": ((88, 28, 135), (219, 39, 119), stack),
    "ai": ((30, 27, 75), (124, 58, 237), ai),
    "privacy": ((6, 78, 59), (20, 184, 166), privacy),
    "globe": ((146, 64, 14), (2, 132, 199), globe),
}
