"""
Shared design kit for every book: fonts, colours, page size, drawing helpers,
bubble letters, the company logo, footer/frame and the common front-matter pages.
"""
import math
import os

from PIL import Image
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ..config import AUTHOR, BRAND, BRAND_DIR, BRAND_TAGLINE, COPYRIGHT_LINE, YEAR

PAGE_W, PAGE_H = 8.5 * 72, 11 * 72      # interior trim in points (8.5 x 11 in)
BLEED = 0.125 * 72
SAFE = 0.375 * 72                       # KDP: keep content this far from the trim edge

INK = HexColor("#000000")
WHITE = white
GREY = HexColor("#555555")
RAINBOW = [HexColor(h) for h in ("#FF595E", "#FFCA3A", "#8AC926", "#1982C4", "#6A4C93", "#FF924C")]

FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
for _name, _file in (("Bubble", "ARLRDBD.TTF"), ("Body", "arial.ttf"), ("BodyBold", "arialbd.ttf"),
                     ("Fun", "comicbd.ttf"), ("Tagline", "segoeui.ttf")):
    pdfmetrics.registerFont(TTFont(_name, os.path.join(FONT_DIR, _file)))


# --------------------------------------------------------------------------
# Drawing helpers. Pictures are drawn in a 200 x 200 local box.
# F(colour) returns the colour on the cover and white in the interior.
# --------------------------------------------------------------------------
class Fill:
    def __init__(self, color=False, bg=WHITE):
        self.color = color
        self.bg = bg
        self.lw = 1.0

    def __call__(self, hexcol):
        return HexColor(hexcol) if self.color else WHITE


def fp(c, F, p, col):
    c.setFillColor(F(col))
    c.drawPath(p, stroke=1, fill=1)


def circ(c, F, x, y, r, col):
    c.setFillColor(F(col))
    c.circle(x, y, r, stroke=1, fill=1)


def ell(c, F, x1, y1, x2, y2, col):
    c.setFillColor(F(col))
    c.ellipse(x1, y1, x2, y2, stroke=1, fill=1)


def rect(c, F, x, y, w, h, col, r=0):
    c.setFillColor(F(col))
    if r:
        c.roundRect(x, y, w, h, r, stroke=1, fill=1)
    else:
        c.rect(x, y, w, h, stroke=1, fill=1)


def poly(c, F, pts, col):
    p = c.beginPath()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    fp(c, F, p, col)


def polyline(c, pts):
    p = c.beginPath()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    c.drawPath(p, stroke=1, fill=0)


def solid(c, x, y, r):
    c.setFillColor(INK)
    c.circle(x, y, r, stroke=0, fill=1)


def shine(c, x, y, r):
    c.setFillColor(WHITE)
    c.circle(x, y, r, stroke=0, fill=1)


def thin(c, F, k=0.6):
    c.setLineWidth(F.lw * k)


def normal(c, F):
    c.setLineWidth(F.lw)


def tube(c, F, build, w, col):
    """Stroke a path as an outlined 'tube' (good for sticks, handles)."""
    p = c.beginPath()
    build(p)
    c.saveState()
    c.setLineCap(1)
    c.setLineJoin(1)
    c.setLineWidth(w + 2 * F.lw)
    c.setStrokeColor(INK)
    c.drawPath(p, stroke=1, fill=0)
    c.setLineWidth(w)
    c.setStrokeColor(F(col))
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def tube_line(c, F, x1, y1, x2, y2, w, col):
    def b(p):
        p.moveTo(x1, y1)
        p.lineTo(x2, y2)
    tube(c, F, b, w, col)


def star(c, F, cx, cy, r, col, ri=0.45):
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * ri
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    poly(c, F, pts, col)


def heart(c, F, cx, cy, s, col):
    p = c.beginPath()
    p.moveTo(cx, cy - 0.9 * s)
    p.curveTo(cx - 1.4 * s, cy + 0.1 * s, cx - 0.6 * s, cy + 1.1 * s, cx, cy + 0.45 * s)
    p.curveTo(cx + 0.6 * s, cy + 1.1 * s, cx + 1.4 * s, cy + 0.1 * s, cx, cy - 0.9 * s)
    p.close()
    fp(c, F, p, col)


def drop(c, F, x, y, s, col):
    p = c.beginPath()
    p.moveTo(x, y + 1.6 * s)
    p.curveTo(x + 0.25 * s, y + 1.0 * s, x + s, y + 0.4 * s, x + s, y - 0.2 * s)
    p.curveTo(x + s, y - 1.1 * s, x - s, y - 1.1 * s, x - s, y - 0.2 * s)
    p.curveTo(x - s, y + 0.4 * s, x - 0.25 * s, y + 1.0 * s, x, y + 1.6 * s)
    p.close()
    fp(c, F, p, col)


def cloud_path(c, cx, cy, rx, ry, n=10, bulge=1.3, off=0.0):
    p = c.beginPath()
    step = 2 * math.pi / n
    ang = [off + i * step for i in range(n + 1)]
    pt = lambda a, k=1.0: (cx + rx * k * math.cos(a), cy + ry * k * math.sin(a))
    p.moveTo(*pt(ang[0]))
    for i in range(n):
        a, b = ang[i], ang[i + 1]
        c1 = pt(a + step * 0.15, bulge)
        c2 = pt(b - step * 0.15, bulge)
        p.curveTo(c1[0], c1[1], c2[0], c2[1], *pt(b))
    p.close()
    return p


def draw_picture(c, fn, x, y, size, F, lw=3.2):
    s = size / 200.0
    c.saveState()
    c.translate(x, y)
    c.scale(s, s)
    F.lw = lw / s
    c.setLineWidth(F.lw)
    c.setLineJoin(1)
    c.setLineCap(1)
    c.setStrokeColor(INK)
    fn(c, F)
    c.restoreState()


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------
def bubble_text(c, txt, x, y, size, fills=None, outline=3.0, halo=None, centered=True, font="Bubble"):
    """Fat 'bubble' letters: an ink outline around a fill (white = colourable)."""
    halo = halo if halo is not None else max(5.0, size * 0.055)
    w = pdfmetrics.stringWidth(txt, font, size)
    if centered:
        x -= w / 2
    fills = fills or [WHITE]
    c.saveState()
    c.setLineJoin(1)
    c.setLineCap(1)
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setTextRenderMode(2)
    c.setStrokeColor(INK)
    c.setFillColor(INK)
    c.setLineWidth(halo + 2 * outline)
    t.textOut(txt)
    c.drawText(t)
    cx = x
    for i, ch in enumerate(txt):
        col = fills[i % len(fills)]
        t = c.beginText(cx, y)
        t.setFont(font, size)
        t.setTextRenderMode(2)
        c.setStrokeColor(col)
        c.setFillColor(col)
        c.setLineWidth(halo)
        t.textOut(ch)
        c.drawText(t)
        cx += pdfmetrics.stringWidth(ch, font, size)
    c.restoreState()
    return w


def fit_size(txt, max_w, max_size, font="Bubble", pad=0.12):
    size = max_size
    while size > 10 and pdfmetrics.stringWidth(txt, font, size) * (1 + pad) > max_w:
        size -= 1
    return size


def trace_text(c, txt, x, y, size, font="Bubble"):
    """Dashed outline letters for tracing practice."""
    c.saveState()
    c.setDash(2.5, 3.5)
    c.setLineWidth(1.4)
    c.setStrokeColor(GREY)
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setTextRenderMode(1)
    t.textOut(txt)
    c.drawText(t)
    c.restoreState()


_BRAND_CACHE = {}


def brand_images(color):
    """Company logo (MJ mark) + 'mahiMJ' wordmark from assets/brand,
    cropped to their visible pixels. Grey versions are used in the B&W interior."""
    key = "color" if color else "grey"
    if key not in _BRAND_CACHE:
        imgs = []
        for name in ("logo.png", "name.png"):
            im = Image.open(os.path.join(BRAND_DIR, name)).convert("RGBA")
            box = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
            im = im.crop(box)
            # Flatten onto white (the logo always sits on white) so the PDF has no
            # transparency - KDP asks for flattened print files.
            flat = Image.new("RGB", im.size, (255, 255, 255))
            flat.paste(im, mask=im.getchannel("A"))
            if not color:
                flat = flat.convert("L").point(lambda v: int(v * 0.8) if v < 250 else 255)  # darker for print
            imgs.append((ImageReader(flat), im.size[0] / im.size[1]))
        _BRAND_CACHE[key] = imgs
    return _BRAND_CACHE[key]


def logo_size(scale=1.0):
    H = 26 * scale
    (_, icon_ar), (_, wm_ar) = brand_images(True)
    tag_w = pdfmetrics.stringWidth(BRAND_TAGLINE, "Tagline", 0.27 * H)
    return icon_ar * H + 0.18 * H + max(wm_ar * 0.56 * H, tag_w), H


def draw_logo(c, x, y, scale=1.0, color=False, align="left"):
    """Company lockup: [MJ mark] mahiMJ / Books. y = old text baseline."""
    (icon, icon_ar), (wm, wm_ar) = brand_images(color)
    total, H = logo_size(scale)
    if align == "right":
        x -= total
    elif align == "center":
        x -= total / 2
    bottom = y - 6 * scale
    iw = icon_ar * H
    c.drawImage(icon, x, bottom, iw, H)
    wx = x + iw + 0.18 * H
    wh = 0.56 * H
    c.drawImage(wm, wx, bottom + 0.38 * H, wm_ar * wh, wh)
    c.saveState()
    c.setFillColor(HexColor("#3A3A3A"))
    c.setFont("Tagline", 0.27 * H)
    c.drawString(wx + 0.02 * H, bottom + 0.08 * H, BRAND_TAGLINE)
    c.restoreState()
    return total


def footer(c):
    c.saveState()
    c.setFont("Body", 8.5)
    c.setFillColor(GREY)
    c.drawString(54, 40, COPYRIGHT_LINE)
    c.restoreState()
    draw_logo(c, PAGE_W - 54, 38, scale=0.8, align="right")


def frame(c):
    c.saveState()
    c.setStrokeColor(HexColor("#999999"))
    c.setLineWidth(1)
    c.roundRect(40, 60, PAGE_W - 80, PAGE_H - 100, 18, stroke=1, fill=0)
    c.restoreState()


# --------------------------------------------------------------------------
# Front-matter pages shared by all books
# --------------------------------------------------------------------------
def page_copyright(c, title, subtitle):
    c.setFillColor(INK)
    y = 330
    lines = [
        ("BodyBold", 12, title),
        ("Body", 10.5, subtitle),
        ("Body", 10.5, ""),
        ("Body", 10.5, f"Copyright \u00a9 {YEAR} {BRAND}. All rights reserved."),
        ("Body", 10.5, f"Published by {BRAND}."),
        ("Body", 10.5, f"Written and illustrated by {AUTHOR}."),
        ("Body", 10.5, ""),
    ]
    for font, size, txt in lines:
        c.setFont(font, size)
        c.drawCentredString(PAGE_W / 2, y, txt)
        y -= size + 7
    body = ("No part of this book may be reproduced, stored in a retrieval system, or transmitted "
            "in any form or by any means - electronic, mechanical, photocopying, recording or "
            "otherwise - without the prior written permission of the publisher, except by the "
            "purchaser for personal, non-commercial colouring use.")
    c.setFont("Body", 9.5)
    for ln in simpleSplit(body, "Body", 9.5, 400):
        c.drawCentredString(PAGE_W / 2, y, ln)
        y -= 14
    y -= 10
    c.drawCentredString(PAGE_W / 2, y, f"First edition {YEAR}")
    draw_logo(c, PAGE_W / 2, y - 50, scale=1.2, align="center")


def page_belongs(c):
    F = Fill()
    frame(c)
    c.setFillColor(INK)
    c.setFont("Fun", 36)
    c.drawCentredString(PAGE_W / 2, 600, "This book belongs to")
    c.setLineWidth(1.5)
    c.setStrokeColor(INK)
    c.line(130, 520, PAGE_W - 130, 520)
    c.setFont("Fun", 16)
    c.drawString(130, 440, "My age:")
    c.line(205, 440, 290, 440)
    c.drawString(320, 440, "My favourite colour:")
    c.line(130, 400, PAGE_W - 130, 400)
    for (x, y, r) in ((110, 680, 26), (500, 690, 20), (300, 690, 14), (150, 250, 22), (470, 260, 30), (300, 200, 18)):
        c.saveState()
        c.setLineWidth(3)
        F.lw = 3
        star(c, F, x, y, r, "#FFD166")
        c.restoreState()
    footer(c)
