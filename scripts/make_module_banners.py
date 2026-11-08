"""Draws one unique header banner per module (run by hand; the images are committed).

    python scripts/make_module_banners.py

Writes ``reckon_saas_platform/public/images/banners/<key>.webp`` (1600x480, for the page)
and ``<key>-og.png`` (1200x630, for social previews). The pictures carry no text, so the page's
own headings stay the searchable content. A module with no picture here gets a generated SVG

"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "reckon_saas_platform" / "public" / "images" / "banners"
SS = 2  # draw at twice the size, then shrink for smooth edges

THEMES = {
    "distribution": ((11, 120, 171), (19, 155, 217), (60, 212, 0)),
    "accounts": ((6, 78, 59), (13, 148, 136), (250, 204, 21)),
    "sales_agent": ((76, 29, 149), (99, 102, 241), (244, 114, 182)),
    "hrms": ((154, 52, 18), (234, 88, 12), (253, 224, 71)),
    "crm": ((15, 23, 42), (30, 64, 175), (56, 189, 248)),
}
WHITE = (255, 255, 255)


def gradient(size, start, end):
    w, h = size
    img = Image.new("RGB", size, start)
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (x / w) * 0.75 + (y / h) * 0.25
            px[x, y] = tuple(int(start[i] + (end[i] - start[i]) * t) for i in range(3))
    return img.convert("RGBA")


class Pen:
    """Draws in a 700x400 design box placed anywhere on the canvas."""

    def __init__(self, canvas, ox, oy, scale):
        self.layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.layer)
        self.ox, self.oy, self.k = ox, oy, scale

    def p(self, x, y):
        return (self.ox + x * self.k, self.oy + y * self.k)

    def box(self, x0, y0, x1, y1):
        return (*self.p(x0, y0), *self.p(x1, y1))

    def rect(self, x0, y0, x1, y1, fill, r=14):
        self.d.rounded_rectangle(self.box(x0, y0, x1, y1), r * self.k, fill=fill)

    def circle(self, cx, cy, rad, fill):
        self.d.ellipse(self.box(cx - rad, cy - rad, cx + rad, cy + rad), fill=fill)

    def line(self, pts, fill, width):
        self.d.line([self.p(*q) for q in pts], fill=fill, width=int(width * self.k), joint="curve")

    def poly(self, pts, fill):
        self.d.polygon([self.p(*q) for q in pts], fill=fill)


def soft(a):
    return (255, 255, 255, a)


def distribution(pen, accent):
    pen.line([(40, 320), (150, 250), (260, 290), (380, 170), (500, 210), (640, 90)], soft(150), 7)
    for i, (x, y) in enumerate([(40, 320), (150, 250), (260, 290), (380, 170), (500, 210), (640, 90)]):
        pen.circle(x, y, 22, (*accent, 255) if i == 5 else soft(235))
        pen.circle(x, y, 9, (20, 60, 90, 255))
    pen.rect(90, 40, 330, 130, soft(70), 20)
    pen.rect(105, 58, 215, 70, soft(200), 6)
    pen.rect(105, 84, 290, 96, soft(120), 6)
    pen.rect(105, 108, 250, 118, soft(90), 5)
    pen.rect(470, 280, 660, 360, soft(70), 18)
    pen.rect(485, 296, 560, 330, (*accent, 255), 8)
    pen.circle(600, 345, 16, soft(220))
    pen.circle(520, 345, 16, soft(220))


def accounts(pen, accent):
    pen.rect(40, 50, 330, 360, soft(60), 24)
    for i in range(6):
        pen.rect(70, 90 + i * 44, 300 - (i % 3) * 50, 104 + i * 44, soft(210 if i == 0 else 120), 7)
    heights = (90, 150, 120, 210, 170, 250)
    for i, h in enumerate(heights):
        pen.rect(380 + i * 52, 360 - h, 420 + i * 52, 360, (*accent, 255) if i == 5 else soft(150), 10)
    pen.circle(610, 100, 52, (*accent, 255))
    pen.circle(610, 100, 36, (180, 130, 10, 255))
    pen.line([(594, 100), (606, 114), (630, 84)], soft(255), 8)


def sales_agent(pen, accent):
    for i, (w, y) in enumerate([(300, 40), (230, 120), (160, 200), (90, 280)]):
        x0 = 40 + (300 - w) / 2
        pen.rect(x0, y, x0 + w, y + 64, soft(200 - i * 35), 14)
    pen.circle(200, 372, 20, (*accent, 255))
    pen.poly([(530, 70), (548, 124), (604, 142), (548, 160), (530, 214), (512, 160), (456, 142), (512, 124)], (*accent, 255))
    pen.rect(400, 250, 660, 350, soft(80), 24)
    pen.rect(425, 274, 600, 288, soft(220), 7)
    pen.rect(425, 302, 540, 316, soft(130), 7)
    pen.circle(640, 60, 16, soft(180))


def hrms(pen, accent):
    for i, x in enumerate((110, 260, 410)):
        pen.circle(x, 120, 44, soft(230 if i == 1 else 150))
        pen.d.pieslice(pen.box(x - 70, 170, x + 70, 330), 180, 360, fill=soft(230 if i == 1 else 150))
    pen.rect(480, 40, 670, 250, soft(70), 20)
    for r in range(4):
        for c in range(5):
            on = (r, c) in {(1, 2), (2, 3)}
            pen.rect(498 + c * 34, 90 + r * 36, 522 + c * 34, 112 + r * 36, (*accent, 255) if on else soft(120), 6)
    pen.rect(500, 280, 660, 370, soft(90), 16)
    pen.rect(516, 298, 600, 310, soft(220), 6)
    pen.rect(516, 326, 640, 338, (*accent, 255), 6)


def crm(pen, accent):
    for i, x in enumerate((30, 250, 470)):
        pen.rect(x, 30, x + 190, 380, soft(50), 20)
        for j in range(3 - i % 2):
            lit = (i, j) == (1, 0)
            pen.rect(x + 16, 60 + j * 104, x + 174, 140 + j * 104, (*accent, 255) if lit else soft(190), 14)
            pen.circle(x + 40, 84 + j * 104, 12, soft(255) if not lit else (20, 60, 90, 255))
            pen.rect(x + 62, 76 + j * 104, x + 150, 88 + j * 104, (20, 60, 90, 150) if not lit else soft(240), 5)
            pen.rect(x + 62, 100 + j * 104, x + 124, 110 + j * 104, (20, 60, 90, 100) if not lit else soft(180), 5)


MOTIFS = {"distribution": distribution, "accounts": accounts, "sales_agent": sales_agent, "hrms": hrms, "crm": crm}


def draw(key, width, height):
    start, end, accent = THEMES[key]
    w, h = width * SS, height * SS
    canvas = gradient((w, h), start, end)
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((w * 0.62, -h * 0.5, w * 1.1, h * 0.55), fill=(255, 255, 255, 28))
    g.ellipse((-w * 0.1, h * 0.55, w * 0.3, h * 1.4), fill=(255, 255, 255, 22))
    canvas.alpha_composite(glow)
    scale = min(w * 0.5 / 700, h * 0.82 / 400)
    pen = Pen(canvas, w - 700 * scale - w * 0.04, (h - 400 * scale) / 2, scale)
    MOTIFS[key](pen, accent)
    canvas.alpha_composite(pen.layer)
    return canvas.convert("RGB").resize((width, height), Image.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key in MOTIFS:
        draw(key, 1600, 480).save(OUT / f"{key}.webp", quality=84, method=6)
        draw(key, 1200, 630).save(OUT / f"{key}-og.png", optimize=True)
        print(key, (OUT / f"{key}.webp").stat().st_size)


if __name__ == "__main__":
    main()
