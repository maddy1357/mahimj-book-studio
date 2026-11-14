"""
mahimj-books :: Alphabet Colouring Book generator
Builds a KDP-ready paperback:
  - interior.pdf  (8.5 x 11 in, no bleed, black & white, fonts embedded)
  - cover.pdf     (full wrap: back + spine + front, 0.125 in bleed, colour)
  - kdp-listing.json (title, description, keywords ... for the upload step)
  - preview/*.png (thumbnails for review before upload)

All illustrations are original vector drawings defined in this file.

Usage:  python build_alphabet_book.py [output_dir]
"""
import json
import re
import math
import os
import sys

from reportlab.lib.colors import HexColor, white
from PIL import Image
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# --------------------------------------------------------------------------
# Brand / book settings
# --------------------------------------------------------------------------
BRAND = "mahimj-books"            # imprint + copyright holder
BRAND_TAGLINE = "Books"           # shown under the mahiMJ wordmark
AUTHOR = "Madhavan J"
YEAR = 2026
COPYRIGHT_LINE = f"© {YEAR} {BRAND}. All rights reserved."
LOGO_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "company-logo"))
TITLE = "Alphabet Colouring Book"
SUBTITLE = "Trace, Learn & Colour from A to Z"   # must match the text on the cover (KDP rule)

# KDP Rights & Pricing table for this book (58 pages, B&W, 8.5x11) - printing costs as KDP shows them.
# Since June 2025 KDP pays 60% only at/above each store's threshold, 50% below it.
# (store, currency, price to enter, printing cost, 60% threshold, action)
MARKET_PRICES = [
    ("Amazon.com", "USD", "9.99", 2.84, 9.99, "type"),
    ("Amazon.ca", "CAD", "14.26", 3.53, 13.99, "keep"),
    ("Amazon.co.jp", "JPY", "1595", 550, 1000, "keep"),
    ("Amazon.co.uk", "GBP", "7.99", 2.15, 7.99, "type"),
    ("Amazon.com.au", "AUD", "14.75", 5.28, 13.99, "keep"),
    ("Amazon.com.be", "EUR", "9.99", 2.48, 9.99, "type"),
    ("Amazon.de", "EUR", "9.99", 2.48, 9.99, "type"),
    ("Amazon.es", "EUR", "9.99", 2.48, 9.99, "type"),
    ("Amazon.fr", "EUR", "9.99", 2.48, 9.99, "type"),
    ("Amazon.ie", "EUR", "9.99", 2.48, 9.99, "type"),
    ("Amazon.it", "EUR", "9.99", 2.48, 9.99, "type"),
    ("Amazon.nl", "EUR", "9.99", 2.48, 9.99, "type"),
    ("Amazon.pl", "PLN", "40.00", 11.61, 40.00, "type"),
    ("Amazon.se", "SEK", "110.00", 27.67, 110.00, "type"),
]

SINGLE_SIDED = True                           # blank back behind every colouring page
SAFE = 0.375 * 72                             # KDP: keep content this far from trim edges
PAGE_W, PAGE_H = 8.5 * 72, 11 * 72          # trim size in points
BLEED = 0.125 * 72
SPINE_PER_PAGE_IN = 0.002252                  # KDP white paper

INK = HexColor("#000000")
WHITE = white
GREY = HexColor("#555555")
BRAND_ORANGE = HexColor("#FF6B35")
BRAND_TEAL = HexColor("#00A6A6")

FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
pdfmetrics.registerFont(TTFont("Bubble", os.path.join(FONT_DIR, "ARLRDBD.TTF")))
pdfmetrics.registerFont(TTFont("Body", os.path.join(FONT_DIR, "arial.ttf")))
pdfmetrics.registerFont(TTFont("BodyBold", os.path.join(FONT_DIR, "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Fun", os.path.join(FONT_DIR, "comicbd.ttf")))
pdfmetrics.registerFont(TTFont("Tagline", os.path.join(FONT_DIR, "segoeui.ttf")))


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


# --------------------------------------------------------------------------
# A - Z pictures (original artwork)
# --------------------------------------------------------------------------
def d_apple(c, F):
    ell(c, F, 25, 6, 175, 34, "#BFE3B4")
    p = c.beginPath()
    p.moveTo(100, 150)
    p.curveTo(130, 178, 186, 160, 180, 98)
    p.curveTo(176, 48, 140, 18, 118, 24)
    p.curveTo(108, 28, 92, 28, 82, 24)
    p.curveTo(60, 18, 24, 48, 20, 98)
    p.curveTo(14, 160, 70, 178, 100, 150)
    p.close()
    fp(c, F, p, "#E8453C")
    p = c.beginPath()
    p.moveTo(96, 148)
    p.curveTo(98, 165, 101, 180, 106, 194)
    p.lineTo(115, 191)
    p.curveTo(109, 177, 106, 162, 106, 146)
    p.close()
    fp(c, F, p, "#8B5A2B")
    p = c.beginPath()
    p.moveTo(108, 170)
    p.curveTo(125, 198, 160, 196, 180, 186)
    p.curveTo(160, 164, 128, 156, 108, 170)
    p.close()
    fp(c, F, p, "#4CAF50")
    thin(c, F)
    c.bezier(112, 171, 130, 177, 150, 181, 172, 184)
    c.arc(40, 60, 120, 140, 120, 50)
    normal(c, F)


def d_ball(c, F):
    ell(c, F, 35, 4, 165, 26, "#BFE3B4")
    circ(c, F, 100, 105, 85, "#E8453C")
    p = c.beginPath()
    p.moveTo(100, 190)
    p.curveTo(50, 160, 50, 50, 100, 20)
    p.curveTo(150, 50, 150, 160, 100, 190)
    p.close()
    fp(c, F, p, "#FFD166")
    p = c.beginPath()
    p.moveTo(100, 190)
    p.curveTo(80, 150, 80, 60, 100, 20)
    p.curveTo(120, 60, 120, 150, 100, 190)
    p.close()
    fp(c, F, p, "#4D96FF")
    thin(c, F)
    c.arc(30, 35, 170, 175, 130, 35)
    normal(c, F)


def d_cat(c, F):
    poly(c, F, [(38, 115), (45, 190), (92, 150)], "#F4A940")
    poly(c, F, [(162, 115), (155, 190), (108, 150)], "#F4A940")
    poly(c, F, [(52, 138), (54, 174), (80, 152)], "#F7B6C2")
    poly(c, F, [(148, 138), (146, 174), (120, 152)], "#F7B6C2")
    ell(c, F, 25, 25, 175, 160, "#F4A940")
    for x in (70, 130):
        ell(c, F, x - 16, 88, x + 16, 126, "#FFFFFF")
        c.setFillColor(INK)
        c.ellipse(x - 7, 92, x + 7, 118, stroke=0, fill=1)
        shine(c, x + 2, 111, 3)
    poly(c, F, [(91, 82), (109, 82), (100, 71)], "#F7B6C2")
    c.bezier(100, 71, 100, 58, 88, 55, 83, 64)
    c.bezier(100, 71, 100, 58, 112, 55, 117, 64)
    thin(c, F)
    for (y1, y2) in ((76, 84), (70, 68), (64, 52)):
        c.line(72, y1, 18, y2)
        c.line(128, y1, 182, y2)
    c.line(100, 158, 100, 140)
    c.line(87, 156, 90, 142)
    c.line(113, 156, 110, 142)
    normal(c, F)
    ell(c, F, 40, 66, 58, 78, "#F7B6C2")
    ell(c, F, 142, 66, 160, 78, "#F7B6C2")


def d_drum(c, F):
    ell(c, F, 20, 6, 180, 30, "#BFE3B4")
    p = c.beginPath()
    p.moveTo(30, 150)
    p.lineTo(30, 50)
    p.curveTo(30, 18, 170, 18, 170, 50)
    p.lineTo(170, 150)
    p.close()
    fp(c, F, p, "#E8453C")
    c.bezier(30, 64, 30, 34, 170, 34, 170, 64)
    polyline(c, [(30, 132), (53, 70), (76, 132), (100, 66), (124, 132), (147, 70), (170, 132)])
    ell(c, F, 30, 130, 170, 170, "#FFF3D6")
    tube_line(c, F, 18, 192, 80, 160, 7, "#C68B59")
    tube_line(c, F, 182, 192, 120, 160, 7, "#C68B59")
    circ(c, F, 80, 160, 8, "#FFFFFF")
    circ(c, F, 120, 160, 8, "#FFFFFF")


def egg_path(c):
    p = c.beginPath()
    p.moveTo(100, 190)
    p.curveTo(140, 190, 160, 130, 160, 80)
    p.curveTo(160, 40, 135, 15, 100, 15)
    p.curveTo(65, 15, 40, 40, 40, 80)
    p.curveTo(40, 130, 60, 190, 100, 190)
    p.close()
    return p


def d_egg(c, F):
    ell(c, F, 30, 4, 170, 28, "#BFE3B4")
    fp(c, F, egg_path(c), "#FFF3B0")
    c.saveState()
    c.clipPath(egg_path(c), stroke=0, fill=0)
    p = c.beginPath()
    xs = list(range(30, 176, 16))
    p.moveTo(30, 120)
    for i, x in enumerate(xs):
        p.lineTo(x, 132 if i % 2 else 118)
    p.lineTo(175, 90)
    for i, x in enumerate(reversed(xs)):
        p.lineTo(x, 80 if i % 2 else 94)
    p.close()
    fp(c, F, p, "#7EC8E3")
    for x in (70, 100, 130):
        circ(c, F, x, 152, 7, "#F7B6C2")
    for x in (62, 88, 114, 140):
        circ(c, F, x, 55, 6, "#C77DFF")
    c.restoreState()
    c.drawPath(egg_path(c), stroke=1, fill=0)


def d_fish(c, F):
    poly(c, F, [(140, 100), (190, 148), (175, 100), (190, 52)], "#FFBF69")
    p = c.beginPath()
    p.moveTo(60, 138)
    p.curveTo(78, 178, 118, 172, 126, 132)
    p.close()
    fp(c, F, p, "#FFBF69")
    p = c.beginPath()
    p.moveTo(80, 62)
    p.curveTo(84, 36, 106, 36, 112, 64)
    p.close()
    fp(c, F, p, "#FFBF69")
    p = c.beginPath()
    p.moveTo(20, 100)
    p.curveTo(50, 165, 130, 160, 152, 100)
    p.curveTo(130, 40, 50, 35, 20, 100)
    p.close()
    fp(c, F, p, "#FF9F1C")
    circ(c, F, 50, 112, 11, "#FFFFFF")
    solid(c, 52, 112, 5.5)
    shine(c, 54, 115, 2)
    c.bezier(78, 132, 92, 116, 92, 86, 78, 70)
    thin(c, F)
    for (x, y) in ((106, 116), (106, 88), (124, 102), (90, 102), (124, 128), (124, 76)):
        c.arc(x - 9, y - 9, x + 9, y + 9, -70, 140)
    c.bezier(22, 97, 27, 91, 31, 91, 36, 94)
    normal(c, F)
    circ(c, F, 22, 138, 7, "#BDE0FE")
    circ(c, F, 14, 160, 5, "#BDE0FE")
    circ(c, F, 26, 180, 8, "#BDE0FE")


def d_gift(c, F):
    rect(c, F, 35, 20, 130, 110, "#7B61FF")
    thin(c, F)
    for (x, y) in ((55, 45), (140, 50), (60, 100), (140, 105), (50, 75), (148, 78)):
        circ(c, F, x, y, 5, "#FFD166")
    normal(c, F)
    rect(c, F, 90, 20, 20, 110, "#FFD166")
    rect(c, F, 25, 128, 150, 30, "#9D8CFF")
    rect(c, F, 90, 128, 20, 30, "#FFD166")
    for sx in (-1, 1):
        p = c.beginPath()
        p.moveTo(100, 158)
        p.curveTo(100 + sx * 40, 200, 100 + sx * 70, 178, 100, 158)
        p.close()
        fp(c, F, p, "#FF6B6B")
    ell(c, F, 89, 150, 111, 168, "#FF6B6B")


def d_house(c, F):
    ell(c, F, 8, 6, 192, 30, "#BFE3B4")
    rect(c, F, 125, 140, 20, 44, "#C0C0C0")
    circ(c, F, 146, 192, 5, "#FFFFFF")
    circ(c, F, 158, 197, 4, "#FFFFFF")
    rect(c, F, 38, 20, 124, 100, "#FFE5B4")
    poly(c, F, [(20, 118), (100, 190), (180, 118)], "#E8453C")
    circ(c, F, 100, 146, 11, "#7EC8E3")
    rect(c, F, 85, 20, 30, 56, "#A0522D", r=8)
    solid(c, 108, 48, 3)
    for x in (50, 124):
        rect(c, F, x, 66, 26, 26, "#7EC8E3")
        c.line(x + 13, 66, x + 13, 92)
        c.line(x, 79, x + 26, 79)
    for x in (24, 172):
        p = c.beginPath()
        p.moveTo(x - 8, 20)
        p.curveTo(x - 12, 50, x + 12, 50, x + 8, 20)
        p.close()
        fp(c, F, p, "#4CAF50")


def d_icecream(c, F):
    cone = [(55, 112), (100, 8), (145, 112)]
    poly(c, F, cone, "#E9B872")
    c.saveState()
    p = c.beginPath()
    p.moveTo(*cone[0]); p.lineTo(*cone[1]); p.lineTo(*cone[2]); p.close()
    c.clipPath(p, stroke=0, fill=0)
    thin(c, F)
    for k in range(-6, 8):
        x = 40 + k * 16
        c.line(x, 0, x + 110, 110)
        c.line(x + 110, 0, x, 110)
    c.restoreState()
    p = c.beginPath()
    p.moveTo(48, 110)
    p.curveTo(40, 168, 160, 168, 152, 110)
    p.curveTo(145, 92, 125, 92, 118, 108)
    p.curveTo(110, 96, 92, 96, 84, 108)
    p.curveTo(76, 92, 55, 92, 48, 110)
    p.close()
    fp(c, F, p, "#FF8FAB")
    p = c.beginPath()
    p.moveTo(62, 150)
    p.curveTo(55, 198, 145, 198, 138, 150)
    p.curveTo(120, 138, 80, 138, 62, 150)
    p.close()
    fp(c, F, p, "#A0E7E5")
    thin(c, F)
    for (x, y, dx, dy) in ((80, 165, 6, 4), (100, 178, -5, 5), (118, 163, 6, -3), (92, 155, 6, 2), (125, 175, -4, 4)):
        c.line(x, y, x + dx, y + dy)
    normal(c, F)
    c.bezier(100, 190, 102, 198, 108, 202, 114, 204)
    circ(c, F, 100, 188, 9, "#E8453C")


def d_jellyfish(c, F):
    for x in (58, 84, 112, 140):
        def b(p, x=x):
            p.moveTo(x, 110)
            p.curveTo(x - 22, 80, x + 22, 50, x, 14)
        tube(c, F, b, 7, "#E0AAFF")
    p = c.beginPath()
    p.moveTo(35, 105)
    p.curveTo(30, 196, 170, 196, 165, 105)
    pts = [165, 132.5, 100, 67.5, 35]
    for a, b2 in zip(pts, pts[1:]):
        p.curveTo(a - 8, 90, b2 + 8, 90, b2, 105)
    p.close()
    fp(c, F, p, "#C77DFF")
    solid(c, 78, 140, 6)
    solid(c, 122, 140, 6)
    shine(c, 80, 143, 2)
    shine(c, 124, 143, 2)
    c.bezier(88, 125, 94, 116, 106, 116, 112, 125)
    ell(c, F, 58, 122, 72, 130, "#F7B6C2")
    ell(c, F, 128, 122, 142, 130, "#F7B6C2")
    thin(c, F)
    for (x, y, r) in ((70, 168, 6), (100, 175, 5), (130, 166, 7), (55, 150, 4)):
        circ(c, F, x, y, r, "#E0AAFF")
    normal(c, F)


def d_kite(c, F):
    c.bezier(100, 45, 75, 25, 130, 18, 105, 0)
    for (x, y) in ((92, 34), (114, 12)):
        poly(c, F, [(x, y), (x - 11, y + 7), (x - 11, y - 7)], "#FF6B6B")
        poly(c, F, [(x, y), (x + 11, y + 7), (x + 11, y - 7)], "#FF6B6B")
    t, r, b, l, m = (100, 196), (160, 125), (100, 45), (40, 125), (100, 125)
    poly(c, F, [t, l, m], "#E8453C")
    poly(c, F, [t, r, m], "#FFD166")
    poly(c, F, [b, l, m], "#4D96FF")
    poly(c, F, [b, r, m], "#4CAF50")
    thin(c, F)
    c.bezier(160, 125, 175, 100, 168, 80, 190, 60)
    normal(c, F)


def d_leaf(c, F):
    tube_line(c, F, 100, 40, 100, 6, 7, "#8B5A2B")
    p = c.beginPath()
    p.moveTo(100, 34)
    p.curveTo(25, 60, 40, 165, 100, 196)
    p.curveTo(160, 165, 175, 60, 100, 34)
    p.close()
    fp(c, F, p, "#7CC36E")
    c.line(100, 36, 100, 186)
    thin(c, F)
    for (y, w) in ((62, 36), (92, 46), (122, 44), (152, 32)):
        c.bezier(100, y, 100 - w * 0.4, y + 6, 100 - w * 0.8, y + 14, 100 - w, y + 24)
        c.bezier(100, y, 100 + w * 0.4, y + 6, 100 + w * 0.8, y + 14, 100 + w, y + 24)
    normal(c, F)
    drop(c, F, 150, 60, 7, "#BDE0FE")


def d_moon(c, F):
    c.saveState()
    p = c.beginPath()
    p.circle(90, 100, 80 + F.lw)
    c.clipPath(p, stroke=0, fill=0)
    circ(c, F, 90, 100, 80, "#FFD166")
    c.setFillColor(F.bg)
    c.circle(125, 125, 65, stroke=1, fill=1)
    c.restoreState()
    c.bezier(42, 116, 48, 106, 58, 106, 64, 116)
    c.bezier(42, 86, 50, 74, 62, 74, 70, 84)
    ell(c, F, 30, 96, 44, 104, "#F7B6C2")
    star(c, F, 158, 178, 13, "#FFD166")
    star(c, F, 186, 74, 10, "#FFD166")
    star(c, F, 168, 26, 12, "#FFD166")
    star(c, F, 22, 186, 9, "#FFD166")


def d_nest(c, F):
    ell(c, F, 48, 70, 90, 128, "#BDE0FE")
    ell(c, F, 82, 76, 122, 138, "#FFFFFF")
    ell(c, F, 115, 70, 155, 126, "#BDE0FE")
    nest = c.beginPath()
    nest.moveTo(14, 100)
    nest.curveTo(20, 28, 180, 28, 186, 100)
    nest.curveTo(150, 84, 50, 84, 14, 100)
    nest.close()
    fp(c, F, nest, "#C68B59")
    c.saveState()
    clip = c.beginPath()
    clip.moveTo(14, 100)
    clip.curveTo(20, 28, 180, 28, 186, 100)
    clip.curveTo(150, 84, 50, 84, 14, 100)
    clip.close()
    c.clipPath(clip, stroke=0, fill=0)
    thin(c, F)
    for (a, b2, d) in ((20, 82, 0), (40, 72, 30), (30, 62, -20), (60, 55, 10), (80, 82, -10), (110, 66, 20)):
        c.bezier(a, b2, a + 40, b2 - 12 + d * 0.2, a + 80, b2 + 8, a + 130, b2 - 10)
        c.bezier(a + 140, b2 + 4, a + 90, b2 - 10, a + 50, b2 + 6, a, b2 - 14)
    c.restoreState()
    c.drawPath(clip, stroke=1, fill=0)
    p = c.beginPath()
    p.moveTo(160, 92)
    p.curveTo(175, 112, 192, 112, 196, 104)
    p.curveTo(188, 92, 172, 88, 160, 92)
    p.close()
    fp(c, F, p, "#4CAF50")


def d_owl(c, F):
    tube_line(c, F, 6, 30, 194, 30, 12, "#8B5A2B")
    p = c.beginPath()
    p.moveTo(170, 36)
    p.curveTo(178, 52, 192, 54, 196, 46)
    p.curveTo(190, 36, 178, 32, 170, 36)
    p.close()
    fp(c, F, p, "#4CAF50")
    poly(c, F, [(48, 150), (52, 196), (82, 166)], "#9D6B7A")
    poly(c, F, [(152, 150), (148, 196), (118, 166)], "#9D6B7A")
    ell(c, F, 40, 34, 160, 176, "#B5838D")
    ell(c, F, 68, 40, 132, 112, "#FFE5D9")
    thin(c, F)
    for (x, y) in ((88, 96), (112, 96), (100, 80), (82, 66), (118, 66), (100, 52)):
        c.arc(x - 7, y - 7, x + 7, y + 7, 200, 140)
    normal(c, F)
    for sx in (-1, 1):
        p = c.beginPath()
        x0 = 100 + sx * 55
        p.moveTo(x0, 130)
        p.curveTo(100 + sx * 82, 100, 100 + sx * 66, 62, 100 + sx * 40, 50)
        p.curveTo(100 + sx * 46, 80, 100 + sx * 46, 110, x0, 130)
        p.close()
        fp(c, F, p, "#9D6B7A")
    for x in (76, 124):
        circ(c, F, x, 136, 24, "#FFD166")
        circ(c, F, x, 136, 15, "#FFFFFF")
        solid(c, x, 136, 9)
        shine(c, x + 3, 140, 3)
    poly(c, F, [(91, 116), (109, 116), (100, 98)], "#FF9F1C")
    for x0 in (80, 120):
        for dx in (-8, 0, 8):
            circ(c, F, x0 + dx, 36, 4.5, "#FF9F1C")


def d_pencil(c, F):
    c.saveState()
    c.translate(100, 100)
    c.rotate(35)
    c.translate(-100, -100)
    rect(c, F, 10, 83, 26, 34, "#FF8FAB", r=8)
    rect(c, F, 30, 83, 18, 34, "#C0C0C0")
    c.line(36, 83, 36, 117)
    c.line(42, 83, 42, 117)
    rect(c, F, 48, 83, 100, 34, "#FFD166")
    c.line(48, 94.3, 148, 94.3)
    c.line(48, 105.7, 148, 105.7)
    poly(c, F, [(148, 83), (186, 100), (148, 117)], "#F2D0A4")
    c.setFillColor(INK)
    p = c.beginPath()
    p.moveTo(173, 94.2); p.lineTo(186, 100); p.lineTo(173, 105.8); p.close()
    c.drawPath(p, stroke=1, fill=1)
    c.restoreState()
    thin(c, F)
    c.bezier(30, 30, 60, 10, 90, 50, 120, 25)
    c.bezier(120, 25, 140, 10, 160, 30, 180, 20)
    normal(c, F)


def d_quilt(c, F):
    rect(c, F, 12, 12, 176, 176, "#FFFFFF", r=10)
    cols = ["#FF8FAB", "#7EC8E3", "#FFD166", "#B7E4A7"]
    for i in range(4):
        for j in range(4):
            x, y = 20 + i * 40, 20 + j * 40
            if (i + j) % 2 == 0:
                poly(c, F, [(x, y), (x + 40, y), (x, y + 40)], cols[(i + j) % 4])
                poly(c, F, [(x + 40, y), (x + 40, y + 40), (x, y + 40)], cols[(i + j + 1) % 4])
            else:
                rect(c, F, x, y, 40, 40, "#FFF3D6")
                if (i * 3 + j) % 2:
                    heart(c, F, x + 20, y + 19, 11, "#E8453C")
                else:
                    star(c, F, x + 20, y + 20, 13, "#C77DFF")
    c.saveState()
    thin(c, F, 0.5)
    c.setDash(4, 4)
    c.roundRect(16, 16, 168, 168, 8, stroke=1, fill=0)
    c.restoreState()


def d_rocket(c, F):
    p = c.beginPath()
    p.moveTo(78, 56)
    p.curveTo(72, 28, 94, 22, 100, 0)
    p.curveTo(106, 22, 128, 28, 122, 56)
    p.close()
    fp(c, F, p, "#FF9F1C")
    p = c.beginPath()
    p.moveTo(88, 56)
    p.curveTo(86, 40, 98, 34, 100, 18)
    p.curveTo(102, 34, 114, 40, 112, 56)
    p.close()
    fp(c, F, p, "#FFD166")
    poly(c, F, [(72, 100), (38, 52), (40, 40), (74, 56)], "#E8453C")
    poly(c, F, [(128, 100), (162, 52), (160, 40), (126, 56)], "#E8453C")

    def body():
        p = c.beginPath()
        p.moveTo(70, 50)
        p.lineTo(70, 130)
        p.curveTo(70, 165, 90, 185, 100, 198)
        p.curveTo(110, 185, 130, 165, 130, 130)
        p.lineTo(130, 50)
        p.close()
        return p
    fp(c, F, body(), "#DDE6F0")
    c.saveState()
    c.clipPath(body(), stroke=0, fill=0)
    rect(c, F, 60, 155, 80, 60, "#E8453C")
    rect(c, F, 60, 40, 80, 22, "#4D96FF")
    c.restoreState()
    c.drawPath(body(), stroke=1, fill=0)
    circ(c, F, 100, 118, 18, "#FFFFFF")
    circ(c, F, 100, 118, 12, "#7EC8E3")
    shine(c, 96, 122, 3)
    tube_line(c, F, 100, 62, 100, 90, 6, "#E8453C")
    for (x, y, r) in ((25, 170, 8), (175, 150, 10), (30, 110, 6), (170, 190, 6)):
        star(c, F, x, y, r, "#FFD166")


def d_sun(c, F):
    for i in range(12):
        a = i * math.pi / 6
        da = math.radians(10)
        poly(c, F, [(100 + 58 * math.cos(a - da), 100 + 58 * math.sin(a - da)),
                    (100 + 94 * math.cos(a), 100 + 94 * math.sin(a)),
                    (100 + 58 * math.cos(a + da), 100 + 58 * math.sin(a + da))], "#FF9F1C")
    circ(c, F, 100, 100, 62, "#FFD166")
    solid(c, 80, 112, 7)
    solid(c, 120, 112, 7)
    shine(c, 82, 115, 2.5)
    shine(c, 122, 115, 2.5)
    p = c.beginPath()
    p.moveTo(74, 86)
    p.curveTo(84, 60, 116, 60, 126, 86)
    p.curveTo(108, 80, 92, 80, 74, 86)
    p.close()
    fp(c, F, p, "#FF6B6B")
    ell(c, F, 58, 84, 74, 94, "#F7B6C2")
    ell(c, F, 126, 84, 142, 94, "#F7B6C2")


def d_tree(c, F):
    ell(c, F, 20, 4, 180, 28, "#BFE3B4")
    p = c.beginPath()
    p.moveTo(76, 14)
    p.curveTo(90, 24, 88, 60, 90, 110)
    p.lineTo(110, 110)
    p.curveTo(112, 60, 110, 24, 124, 14)
    p.close()
    fp(c, F, p, "#8B5A2B")
    c.setFillColor(INK)
    c.ellipse(94, 40, 106, 56, stroke=0, fill=1)
    fp(c, F, cloud_path(c, 100, 132, 72, 48, n=11, bulge=1.28, off=0.2), "#4CAF50")
    for (x, y) in ((62, 140), (100, 120), (138, 145), (80, 165), (122, 172), (150, 115), (55, 108)):
        circ(c, F, x, y, 7, "#E8453C")
    thin(c, F)
    c.bezier(45, 150, 50, 160, 58, 168, 66, 172)
    normal(c, F)


def d_umbrella(c, F):
    def handle(p):
        p.moveTo(100, 150)
        p.lineTo(100, 40)
        p.curveTo(100, 14, 70, 14, 70, 36)
    tube(c, F, handle, 9, "#8B5A2B")
    p = c.beginPath()
    p.moveTo(15, 110)
    p.curveTo(18, 196, 182, 196, 185, 110)
    pts = [185, 142.5, 100, 57.5, 15]
    for a, b2 in zip(pts, pts[1:]):
        p.curveTo(a - 8, 128, b2 + 8, 128, b2, 110)
    p.close()
    fp(c, F, p, "#E8453C")
    for x in (57.5, 100, 142.5):
        c.bezier(100, 174, (100 + x) / 2 + (x - 100) * 0.3, 160, x, 130, x, 110)
    tube_line(c, F, 100, 174, 100, 190, 5, "#8B5A2B")
    for (x, y) in ((25, 170), (178, 168), (30, 60), (168, 70), (150, 25)):
        drop(c, F, x, y, 7, "#BDE0FE")


def d_van(c, F):
    c.line(4, 16, 196, 16)
    p = c.beginPath()
    p.moveTo(15, 40)
    p.lineTo(15, 140)
    p.curveTo(15, 155, 25, 160, 40, 160)
    p.lineTo(140, 160)
    p.curveTo(155, 160, 160, 150, 165, 135)
    p.lineTo(180, 95)
    p.curveTo(185, 85, 185, 75, 185, 60)
    p.lineTo(185, 40)
    p.close()
    fp(c, F, p, "#4D96FF")
    poly(c, F, [(130, 145), (152, 145), (167, 100), (130, 100)], "#CDEFFF")
    rect(c, F, 28, 102, 40, 42, "#CDEFFF", r=6)
    rect(c, F, 78, 102, 40, 42, "#CDEFFF", r=6)
    c.line(125, 44, 125, 100)
    rect(c, F, 110, 80, 10, 5, "#C0C0C0", r=2)
    rect(c, F, 15, 64, 170, 12, "#FFD166")
    ell(c, F, 170, 80, 184, 92, "#FFF3B0")
    rect(c, F, 8, 34, 184, 12, "#C0C0C0", r=5)
    for x in (55, 145):
        circ(c, F, x, 40, 22, "#555555")
        circ(c, F, x, 40, 9, "#DDDDDD")


def d_watermelon(c, F):
    def half(r):
        p = c.beginPath()
        p.moveTo(100 - r, 125)
        p.arcTo(100 - r, 125 - r, 100 + r, 125 + r, 180, 180)
        p.close()
        return p
    fp(c, F, half(88), "#2E8B57")
    fp(c, F, half(78), "#B7E4A7")
    fp(c, F, half(68), "#FF6B6B")
    c.setFillColor(INK)
    for (x, y, a) in ((60, 105, 20), (82, 85, 5), (118, 85, -5), (140, 105, -20), (100, 108, 0), (72, 118, 10), (128, 118, -10), (100, 75, 0)):
        c.saveState()
        c.translate(x, y)
        c.rotate(a)
        c.ellipse(-3.5, -6, 3.5, 6, stroke=0, fill=1)
        c.restoreState()
    for (x, y) in ((30, 170), (170, 168), (100, 175)):
        star(c, F, x, y, 9, "#FFD166")


def d_xylophone(c, F):
    tube_line(c, F, 18, 150, 182, 114, 8, "#8B5A2B")
    tube_line(c, F, 18, 50, 182, 86, 8, "#8B5A2B")
    cols = ["#E8453C", "#FF9F1C", "#FFD166", "#4CAF50", "#4D96FF", "#7B61FF", "#C77DFF"]
    for i in range(7):
        x = 26 + i * 21
        top, bot = 168 - i * 7, 34 + i * 7
        rect(c, F, x, bot, 17, top - bot, cols[i], r=5)
        cx = x + 8.5
        ty = 150 - 36 * (cx - 18) / 164
        by = 50 + 36 * (cx - 18) / 164
        solid(c, cx, ty, 2.5)
        solid(c, cx, by, 2.5)
    tube_line(c, F, 30, 8, 122, 24, 5, "#C68B59")
    circ(c, F, 128, 25, 9, "#E8453C")
    tube_line(c, F, 70, 24, 150, 6, 5, "#C68B59")
    circ(c, F, 156, 5, 9, "#4D96FF")


def d_yoyo(c, F):
    circ(c, F, 100, 85, 70, "#E8453C")
    circ(c, F, 100, 85, 52, "#FF8FAB")
    thin(c, F)
    for i in range(8):
        a = i * math.pi / 4
        c.line(100 + 20 * math.cos(a), 85 + 20 * math.sin(a), 100 + 50 * math.cos(a), 85 + 50 * math.sin(a))
    normal(c, F)
    circ(c, F, 100, 85, 16, "#FFFFFF")
    c.bezier(100, 85, 92, 130, 112, 160, 100, 182)
    c.circle(100, 190, 8, stroke=1, fill=0)
    thin(c, F)
    c.arc(8, 40, 48, 130, 120, 120)
    c.arc(152, 40, 192, 130, -60, 120)
    normal(c, F)
    star(c, F, 165, 175, 10, "#FFD166")
    star(c, F, 35, 170, 8, "#FFD166")


def d_zebra(c, F):
    for sx in (-1, 1):
        p = c.beginPath()
        p.moveTo(100 + sx * 32, 150)
        p.curveTo(100 + sx * 58, 186, 100 + sx * 44, 202, 100 + sx * 22, 166)
        p.close()
        fp(c, F, p, "#FFFFFF")
    c.setFillColor(INK)
    p = c.beginPath()
    p.moveTo(76, 162)
    for (x, y) in ((80, 188), (90, 168), (100, 194), (110, 168), (120, 188), (124, 162)):
        p.lineTo(x, y)
    p.close()
    c.drawPath(p, stroke=1, fill=1)

    def head():
        p = c.beginPath()
        p.moveTo(100, 176)
        p.curveTo(150, 176, 150, 110, 140, 70)
        p.curveTo(135, 50, 65, 50, 60, 70)
        p.curveTo(50, 110, 50, 176, 100, 176)
        p.close()
        return p
    fp(c, F, head(), "#FFFFFF")
    c.saveState()
    c.clipPath(head(), stroke=0, fill=0)
    c.setFillColor(INK)
    for y in (152, 126, 100):
        for sx in (-1, 1):
            p = c.beginPath()
            p.moveTo(100 + sx * 60, y + 8)
            p.curveTo(100 + sx * 40, y + 10, 100 + sx * 26, y + 2, 100 + sx * 18, y - 4)
            p.curveTo(100 + sx * 28, y - 2, 100 + sx * 40, y - 2, 100 + sx * 60, y - 6)
            p.close()
            c.drawPath(p, stroke=0, fill=1)
    p = c.beginPath()
    p.moveTo(92, 180)
    p.curveTo(95, 165, 98, 156, 100, 146)
    p.curveTo(102, 156, 105, 165, 108, 180)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()
    c.drawPath(head(), stroke=1, fill=0)
    for x in (80, 120):
        circ(c, F, x, 118, 10, "#FFFFFF")
        solid(c, x, 117, 5.5)
        shine(c, x + 2, 120, 2)
    ell(c, F, 62, 20, 138, 80, "#B0B0B0")
    c.setFillColor(INK)
    c.ellipse(78, 46, 88, 58, stroke=0, fill=1)
    c.ellipse(112, 46, 122, 58, stroke=0, fill=1)
    c.bezier(84, 34, 94, 27, 106, 27, 116, 34)


LETTERS = [
    ("A", "APPLE", d_apple), ("B", "BALL", d_ball), ("C", "CAT", d_cat),
    ("D", "DRUM", d_drum), ("E", "EGG", d_egg), ("F", "FISH", d_fish),
    ("G", "GIFT", d_gift), ("H", "HOUSE", d_house), ("I", "ICE CREAM", d_icecream),
    ("J", "JELLYFISH", d_jellyfish), ("K", "KITE", d_kite), ("L", "LEAF", d_leaf),
    ("M", "MOON", d_moon), ("N", "NEST", d_nest), ("O", "OWL", d_owl),
    ("P", "PENCIL", d_pencil), ("Q", "QUILT", d_quilt), ("R", "ROCKET", d_rocket),
    ("S", "SUN", d_sun), ("T", "TREE", d_tree), ("U", "UMBRELLA", d_umbrella),
    ("V", "VAN", d_van), ("W", "WATERMELON", d_watermelon), ("X", "XYLOPHONE", d_xylophone),
    ("Y", "YO-YO", d_yoyo), ("Z", "ZEBRA", d_zebra),
]


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


ART = {"source": "vector", "dir": None}     # set in main() from book-config.json


def place_art(c, letter, fn, x, y, size, F):
    """Use the cleaned AI picture for this letter when AI art is switched on and it
    exists; otherwise the original vector drawing."""
    if ART["source"] == "ai" and ART["dir"]:
        p = os.path.join(ART["dir"], f"{letter}.png")
        if os.path.exists(p):
            c.drawImage(p, x, y, size, size)
            return
    draw_picture(c, fn, x, y, size, F)


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
    """Company logo (MJ mark) + 'mahiMJ' wordmark from kdp-book/company-logo,
    cropped to their visible pixels. Grey versions are used in the B&W interior."""
    key = "color" if color else "grey"
    if key not in _BRAND_CACHE:
        imgs = []
        for name in ("logo.png", "name.png"):
            im = Image.open(os.path.join(LOGO_DIR, name)).convert("RGBA")
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
# Interior
# --------------------------------------------------------------------------
def page_title(c):
    F = Fill()
    frame(c)
    bubble_text(c, "ALPHABET", PAGE_W / 2, 610, fit_size("ALPHABET", 470, 100))
    bubble_text(c, "COLOURING BOOK", PAGE_W / 2, 520, fit_size("COLOURING BOOK", 470, 60))
    c.setFont("Fun", 20)
    c.setFillColor(INK)
    c.drawCentredString(PAGE_W / 2, 472, SUBTITLE)
    place_art(c, "A", d_apple, 90, 200, 200, F)
    place_art(c, "C", d_cat, 322, 200, 200, F)
    c.setFont("BodyBold", 18)
    c.drawCentredString(PAGE_W / 2, 140, f"by {AUTHOR}")
    draw_logo(c, PAGE_W / 2, 86, scale=1.6, align="center")


def page_copyright(c):
    c.setFillColor(INK)
    y = 330
    lines = [
        ("BodyBold", 12, f"{TITLE}"),
        ("Body", 10.5, SUBTITLE),
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


def page_letter(c, letter, word, fn):
    F = Fill()
    frame(c)
    c.setFillColor(INK)
    c.setFont("Fun", 26)
    c.drawCentredString(PAGE_W / 2, 705, f"{letter} is for {word.title()}")
    bubble_text(c, letter + letter.lower(), 158, 455, 140)
    place_art(c, letter, fn, 286, 330, 270, F)
    size = fit_size(word, 480, 110)
    bubble_text(c, word, PAGE_W / 2, 220, size)
    # tracing row
    c.saveState()
    c.setFont("Fun", 11)
    c.setFillColor(GREY)
    c.drawString(66, 150, "Trace the letters:")
    c.restoreState()
    tsize = 58
    row = f"{letter} {letter} {letter} {letter.lower()} {letter.lower()} {letter.lower()}"
    tw = pdfmetrics.stringWidth(row, "Bubble", tsize)
    trace_text(c, row, PAGE_W / 2 - tw / 2, 88, tsize)
    c.saveState()
    c.setStrokeColor(HexColor("#BBBBBB"))
    c.setLineWidth(0.8)
    c.line(66, 86, PAGE_W - 66, 86)
    c.restoreState()
    footer(c)


def page_end(c):
    F = Fill()
    frame(c)
    bubble_text(c, "GREAT JOB!", PAGE_W / 2, 600, fit_size("GREAT JOB!", 460, 90))
    c.setFont("Fun", 24)
    c.setFillColor(INK)
    c.drawCentredString(PAGE_W / 2, 545, "You coloured from A to Z!")
    place_art(c, "S", d_sun, 186, 230, 240, F)
    c.setFont("Body", 13)
    c.drawCentredString(PAGE_W / 2, 175, f"Look for more fun books from {BRAND}.")
    draw_logo(c, PAGE_W / 2, 120, scale=1.5, align="center")
    c.setFont("Body", 9)
    c.setFillColor(GREY)
    c.drawCentredString(PAGE_W / 2, 40, COPYRIGHT_LINE)


def build_interior(path):
    c = canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H), initialFontName="Body")
    c.setTitle(TITLE)
    c.setAuthor(AUTHOR)
    c.setCreator(BRAND)
    c.setProducer(BRAND)
    c.setSubject(SUBTITLE)
    n = 0

    def blank():
        # back of a colouring page: left empty so markers can't bleed onto a picture
        nonlocal n
        c.showPage()
        n += 1

    def page(draw, *args):
        nonlocal n
        draw(c, *args)
        c.showPage()
        n += 1

    page(page_title)           # p1 (right)
    page(page_copyright)       # p2 (back of title)
    page(page_belongs)         # p3 (right)
    if SINGLE_SIDED:
        blank()                # p4 - so every picture starts on a right-hand page
    for letter, word, fn in LETTERS:
        page(page_letter, letter, word, fn)
        if SINGLE_SIDED:
            blank()
    page(page_end)
    if n % 2:
        blank()                # even page count
    c.save()
    return n


# --------------------------------------------------------------------------
# Cover (full wrap)
# --------------------------------------------------------------------------
RAINBOW = [HexColor(h) for h in ("#FF595E", "#FFCA3A", "#8AC926", "#1982C4", "#6A4C93", "#FF924C")]


def card(c, fn, letter, cx, cy, size, letter_col):
    c.saveState()
    c.setFillColor(WHITE)
    c.setStrokeColor(HexColor("#1A1A1A"))
    c.setLineWidth(3)
    c.roundRect(cx - size / 2, cy - size / 2, size, size, 22, stroke=1, fill=1)
    c.restoreState()
    F = Fill(color=True)
    pic = size * 0.74
    draw_picture(c, fn, cx - pic / 2 + size * 0.06, cy - pic / 2 - size * 0.06, pic, F, lw=2.6)
    bubble_text(c, letter, cx - size / 2 + 30, cy + size / 2 - 50, 44, fills=[letter_col], outline=2.2)


def build_cover(path, page_count):
    spine = page_count * SPINE_PER_PAGE_IN * 72
    W = 2 * BLEED + 2 * PAGE_W + spine
    H = 2 * BLEED + PAGE_H
    c = canvas.Canvas(path, pagesize=(W, H), initialFontName="Body")
    c.setTitle(f"{TITLE} - Cover")
    c.setAuthor(AUTHOR)
    c.setCreator(BRAND)
    c.setProducer(BRAND)
    bg = HexColor("#4CC9F0")
    c.setFillColor(bg)
    c.rect(0, 0, W, H, stroke=0, fill=1)

    # soft confetti dots across the wrap
    import random
    rnd = random.Random(7)
    for _ in range(140):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        c.setFillColor(HexColor(rnd.choice(["#7FDBFF", "#A0E7FF", "#3BB8E0"])))
        c.circle(x, y, rnd.uniform(3, 9), stroke=0, fill=1)

    # ---------------- front ----------------
    fx = BLEED + PAGE_W + spine
    fy = BLEED
    c.saveState()
    c.translate(fx, fy)
    c.setFillColor(HexColor("#79D6F4"))      # solid tint, no transparency
    c.circle(PAGE_W / 2, 640, 230, stroke=0, fill=1)
    c.restoreState()
    c.saveState()
    c.translate(fx, fy)
    bubble_text(c, "ALPHABET", PAGE_W / 2, 668, fit_size("ALPHABET", 540, 112), outline=3.5)
    bubble_text(c, "COLOURING BOOK", PAGE_W / 2, 590, fit_size("COLOURING BOOK", 520, 62), fills=RAINBOW, outline=3)
    c.setFont("Fun", 21)
    c.setFillColor(HexColor("#1A1A1A"))
    c.drawCentredString(PAGE_W / 2, 552, SUBTITLE)
    picks = [("A", d_apple), ("B", d_ball), ("C", d_cat), ("F", d_fish), ("R", d_rocket), ("S", d_sun)]
    size = 168
    xs = [PAGE_W / 2 - 186, PAGE_W / 2, PAGE_W / 2 + 186]
    ys = [432, 250]
    k = 0
    for cy in ys:
        for cx in xs:
            letter, fn = picks[k]
            card(c, fn, letter, cx, cy, size, RAINBOW[k % len(RAINBOW)])
            k += 1
    # badge
    F = Fill(color=True)
    c.saveState()
    c.setStrokeColor(HexColor("#1A1A1A"))
    c.setLineWidth(3)
    F.lw = 3
    star(c, F, 520, 112, 58, "#FFCA3A", ri=0.72)
    c.restoreState()
    c.setFillColor(HexColor("#1A1A1A"))
    c.setFont("Fun", 15)
    c.drawCentredString(520, 114, "AGES")
    c.setFont("Fun", 20)
    c.drawCentredString(520, 94, "2-5")
    c.setFont("BodyBold", 22)
    c.setFillColor(WHITE)
    c.drawCentredString(PAGE_W / 2, 112, f"by {AUTHOR}")
    c.setFillColor(WHITE)
    lw_, lh_ = logo_size(1.5)
    c.roundRect(PAGE_W / 2 - lw_ / 2 - 16, 34, lw_ + 32, lh_ + 16, 14, stroke=0, fill=1)
    draw_logo(c, PAGE_W / 2, 51, scale=1.5, color=True, align="center")
    c.restoreState()

    # ---------------- back ----------------
    bx = BLEED
    c.saveState()
    c.translate(bx, fy)
    c.setFillColor(WHITE)
    c.roundRect(54, 446, PAGE_W - 108, 294, 24, stroke=0, fill=1)
    c.setFillColor(HexColor("#1A1A1A"))
    c.setFont("Fun", 28)
    c.drawCentredString(PAGE_W / 2, 690, "Learn your ABCs the fun way!")
    c.setFont("Body", 13.5)
    desc = ("Help your little one discover the alphabet with 26 big, friendly pictures to colour - "
            "from a shiny Apple to a stripy Zebra. Every page has a bubble letter, a word to "
            "colour and a tracing row for early writing practice.")
    y = 650
    for ln in simpleSplit(desc, "Body", 13.5, PAGE_W - 170):
        c.drawCentredString(PAGE_W / 2, y, ln)
        y -= 20
    y -= 10
    c.setFont("BodyBold", 14)
    feats = ["26 original A-Z pictures with thick, easy lines",
             "Big bubble letters and words to colour",
             "Letter tracing practice on every page",
             "Single-sided pages - no bleed-through" if SINGLE_SIDED else "Large 8.5 x 11 inch pages",
             "Perfect for toddlers, preschool and kindergarten"]
    for f in feats:
        F2 = Fill(color=True)
        c.saveState()
        c.setStrokeColor(HexColor("#1A1A1A"))
        c.setLineWidth(1.5)
        F2.lw = 1.5
        star(c, F2, 100, y + 5, 9, "#FFCA3A")
        c.restoreState()
        c.setFillColor(HexColor("#1A1A1A"))
        c.drawString(120, y, f)
        y -= 26
    # small picture row
    for i, fn in enumerate([d_house, d_owl, d_umbrella, d_zebra]):
        cx = 120 + i * 124
        c.saveState()
        c.setFillColor(WHITE)
        c.setStrokeColor(HexColor("#1A1A1A"))
        c.setLineWidth(2.5)
        c.roundRect(cx - 52, 300, 104, 104, 16, stroke=1, fill=1)
        c.restoreState()
        draw_picture(c, fn, cx - 42, 310, 84, Fill(color=True), lw=1.8)
    # brand (bottom-left; bottom-right is reserved for the KDP barcode)
    c.setFillColor(WHITE)
    lw_, lh_ = logo_size(1.5)
    c.roundRect(54, 54, lw_ + 32, lh_ + 16, 14, stroke=0, fill=1)
    draw_logo(c, 70, 71, scale=1.5, color=True)
    c.setFont("Body", 10)
    c.setFillColor(HexColor("#1A1A1A"))
    c.drawString(58, 118, COPYRIGHT_LINE)
    c.restoreState()
    c.save()
    return W / 72, H / 72, spine / 72


# --------------------------------------------------------------------------
# Listing + preview
# --------------------------------------------------------------------------
def write_listing(path, pages, cover_dims):
    listing = {
        "format": "paperback",
        "language": "English",
        "title": TITLE,
        "subtitle": SUBTITLE,
        "author": AUTHOR,
        "publisher_imprint": BRAND,
        "copyright_holder": BRAND,
        "description": (
            "<p><b>Learn your ABCs the fun way!</b></p>"
            "<p>This alphabet colouring book from mahimj-books helps children discover the letters "
            "A to Z with 26 big, friendly, original pictures - from a shiny Apple to a stripy Zebra.</p>"
            "<ul><li>26 A-Z pictures with thick, easy-to-colour lines</li>"
            "<li>Big bubble letters and words to colour</li>"
            "<li>Letter tracing practice on every page</li>"
            "<li>Large 8.5 x 11 inch pages, printed single-sided so markers don't bleed through</li>"
            "<li>Perfect for toddlers, preschool and kindergarten (ages 2-5)</li></ul>"
        ),
        "keywords": [
            "alphabet colouring book for toddlers",
            "abc coloring book ages 2-5",
            "letter tracing book for preschool",
            "kindergarten activity book",
            "learn abc coloring pages kids",
            "toddler coloring book big pictures",
            "a to z coloring workbook",
        ],
        "categories_suggested": [
            "Children's Books > Activities, Crafts & Games > Activity Books > Coloring Books",
            "Children's Books > Activities, Crafts & Games > Activity Books",
            "Children's Books > Early Learning > Basic Concepts > Alphabet",
        ],
        "reading_age": {"min": 2, "max": 5},
        "adult_content": False,
        "low_content": False,
        "low_content_note": ("KDP help (Low-Content Books, GGE5T76TWKA85DJM) lists colouring/activity books as "
                             "NOT generally low-content - leave the low-content box unchecked and use a free KDP ISBN."),
        "ai_generated_content_note": "Text and images were AI-generated (Claude by Anthropic) - answer KDP's AI-content questions Yes for text and images.",
        "territories": "All territories (worldwide rights)",
        "print": {
            "isbn": "Use free KDP ISBN",
            "single_sided": SINGLE_SIDED,
            "ink_and_paper": "Black & white interior with white paper",
            "trim_size": "8.5 x 11 in",
            "trim_w": 8.5, "trim_h": 11, "has_bleed": False, "paper": "white",
            "bleed": "No bleed",
            "cover_finish": "Matte",
            "page_count": pages,
            "cover_size_in": {"width": round(cover_dims[0], 4), "height": round(cover_dims[1], 4),
                              "spine": round(cover_dims[2], 4)},
        },
        "files": {"interior": "interior.pdf", "cover": "cover.pdf"},
        "price_usd_suggested": 9.99,   # KDP pays 60% at >= $9.99, only 50% below
        "marketplace_prices": [
            {"store": s, "currency": cur, "price": price, "printing": prt, "threshold_60": th, "action": act,
             "royalty_60": round(0.6 * float(price) - prt, 2)}
            for s, cur, price, prt, th, act in MARKET_PRICES],
        "kdp_account_url": "https://kdp.amazon.com/en_US/account",
        "status": "awaiting_approval",
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(listing, f, indent=2)


def make_print_safe(out_dir, cover_dpi=300):
    """Make the upload files as easy as possible for KDP's file processor.
    cover.pdf  -> one flattened 300 DPI image on a page of the exact KDP size (no fonts or
                  vector parts left to fail on). The vector original is kept as cover-vector.pdf.
    interior.pdf -> every embedded font gets a unique subset tag (ReportLab names them all
                  'AAAAAA+', which some print checkers reject as duplicates)."""
    import hashlib
    import shutil
    import pymupdf
    cv = os.path.join(out_dir, "cover.pdf")
    vec = os.path.join(out_dir, "cover-vector.pdf")
    shutil.copyfile(cv, vec)
    src = pymupdf.open(vec)
    pg = src[0]
    jpg = pg.get_pixmap(dpi=cover_dpi).tobytes(output="jpg", jpg_quality=95)
    out = pymupdf.open()
    page = out.new_page(width=pg.rect.width, height=pg.rect.height)
    page.insert_image(page.rect, stream=jpg)
    out.set_metadata({"title": f"{TITLE} - Cover", "author": AUTHOR, "creator": BRAND, "producer": BRAND})
    src.close()
    out.save(cv + ".tmp", garbage=4, deflate=True)
    out.close()
    os.replace(cv + ".tmp", cv)

    ip = os.path.join(out_dir, "interior.pdf")
    doc = pymupdf.open(ip)
    for xref in range(1, doc.xref_length()):
        for key in ("BaseFont", "FontName"):
            t, v = doc.xref_get_key(xref, key)
            if t == "name" and len(v) > 8 and v[7] == "+":
                base = v[8:]
                tag = "".join(chr(65 + b % 26) for b in hashlib.md5(base.encode()).digest()[:6])
                doc.xref_set_key(xref, key, f"/{tag}+{base}")
    tmp = ip + ".tmp"
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, ip)


def write_cover_images(out_dir, spine_in):
    """JPG/PNG versions of the cover: KDP Cover Creator and the Kindle/marketing uploads accept
    images only (the paperback itself must use cover.pdf)."""
    import pymupdf
    pg = pymupdf.open(os.path.join(out_dir, "cover.pdf"))[0]
    dpi = 300
    front = pymupdf.Rect(BLEED + PAGE_W + spine_in * 72, BLEED, BLEED + 2 * PAGE_W + spine_in * 72, BLEED + PAGE_H)
    pix = pg.get_pixmap(dpi=dpi, clip=front)                      # 2550 x 3300 px, trimmed front cover
    pix.save(os.path.join(out_dir, "cover-front.jpg"), jpg_quality=95)
    pix.save(os.path.join(out_dir, "cover-front.png"))
    pg.get_pixmap(dpi=dpi).save(os.path.join(out_dir, "cover-full-wrap.jpg"), jpg_quality=92)


def write_previews(out_dir):
    import pymupdf
    from PIL import Image
    pv = os.path.join(out_dir, "preview")
    os.makedirs(pv, exist_ok=True)
    doc = pymupdf.open(os.path.join(out_dir, "cover.pdf"))
    doc[0].get_pixmap(dpi=60).save(os.path.join(pv, "cover.png"))
    doc = pymupdf.open(os.path.join(out_dir, "interior.pdf"))
    thumbs = []
    for pg in doc:
        pix = pg.get_pixmap(dpi=36)
        thumbs.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    cols = 6
    tw, th = thumbs[0].size
    gap = 10
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * (tw + gap) + gap, rows * (th + gap) + gap), (210, 210, 210))
    for i, im in enumerate(thumbs):
        sheet.paste(im, (gap + (i % cols) * (tw + gap), gap + (i // cols) * (th + gap)))
    sheet.save(os.path.join(pv, "interior-pages.png"))
    for i in (0, 4, 28, len(doc) - 2):
        if 0 <= i < len(doc):
            doc[i].get_pixmap(dpi=80).save(os.path.join(pv, f"page-{i + 1:02d}.png"))


def preflight(out_dir, pages):
    """KDP print checks: sizes, page count, safe margins, no transparency,
    embedded fonts, image resolution >= 300 DPI."""
    import pymupdf
    problems = []
    doc = pymupdf.open(os.path.join(out_dir, "interior.pdf"))
    if len(doc) < 24:
        problems.append(f"interior has {len(doc)} pages (KDP minimum is 24)")
    for i, pg in enumerate(doc):
        if abs(pg.rect.width - PAGE_W) > 0.5 or abs(pg.rect.height - PAGE_H) > 0.5:
            problems.append(f"page {i + 1}: size {pg.rect.width / 72:.3f} x {pg.rect.height / 72:.3f} in")
        boxes = [d["rect"] for d in pg.get_drawings()]
        boxes += [pymupdf.Rect(b["bbox"]) for b in pg.get_text("dict")["blocks"]]
        for img in pg.get_images(full=True):
            for r in pg.get_image_rects(img[0]):
                boxes.append(r)
                dpi = img[2] / (r.width / 72)
                if dpi < 300:
                    problems.append(f"page {i + 1}: logo image only {dpi:.0f} DPI")
        # check what actually prints (clipping applied): any ink inside the 0.375 in margin?
        pix = pg.get_pixmap(dpi=72, colorspace=pymupdf.csGRAY)
        s = int(SAFE)
        w, h = pix.width, pix.height
        import numpy as np
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(h, w)
        ys, xs = np.nonzero(a < 200)
        if len(xs):
            edge = np.minimum(np.minimum(xs, ys), np.minimum(w - 1 - xs, h - 1 - ys))
            m = int(edge.min())
            if m < s:
                problems.append(f"page {i + 1}: ink {m / 72:.3f} in from the edge (needs 0.375 in)")
    cover = pymupdf.open(os.path.join(out_dir, "cover.pdf"))
    cv = cover[0]
    for img in cv.get_images(full=True):
        for r in cv.get_image_rects(img[0]):
            dpi = img[2] / (r.width / 72)
            if dpi < 299:
                problems.append(f"cover: image only {dpi:.0f} DPI (KDP needs 300)")
    safe_c = BLEED + 0.25 * 72
    vec = os.path.join(out_dir, "cover-vector.pdf")       # text positions come from the vector original
    tv = pymupdf.open(vec)[0] if os.path.exists(vec) else cv
    for b in tv.get_text("dict")["blocks"]:
        if b.get("type") != 0:                              # text blocks only, not images
            continue
        r = pymupdf.Rect(b["bbox"])
        if min(r.x0, r.y0, cv.rect.width - r.x1, cv.rect.height - r.y1) < safe_c:
            problems.append("cover: text too close to the trim edge")
    for name in ("interior.pdf", "cover.pdf"):
        raw = open(os.path.join(out_dir, name), "rb").read()
        if b"/SMask" in raw or re.search(rb"/(ca|CA)\s+0?\.\d", raw):
            problems.append(f"{name}: contains transparency (not flattened)")
        d = pymupdf.open(os.path.join(out_dir, name))
        for p in d:
            for f in p.get_fonts():
                if f[1] == "n/a":
                    problems.append(f"{name}: font {f[3]} not embedded")
    return sorted(set(problems))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "ready-to-publish", "alphabet-colouring-book")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    import shutil
    import ai_images
    cfg = ai_images.book_config(out_dir)
    ART["source"] = cfg.get("art_source", "vector")
    ART["dir"] = ai_images.art_dir(out_dir)
    pages = build_interior(os.path.join(out_dir, "interior.pdf"))
    dims = build_cover(os.path.join(out_dir, "cover-generated.pdf"), pages)
    cover_note = None
    canva = os.path.join(out_dir, "cover-canva.pdf")
    if cfg.get("cover_source") == "canva" and os.path.exists(canva):
        shutil.copyfile(canva, os.path.join(out_dir, "cover.pdf"))
        cover_note = "Canva"
    else:
        shutil.copyfile(os.path.join(out_dir, "cover-generated.pdf"), os.path.join(out_dir, "cover.pdf"))
    write_listing(os.path.join(out_dir, "kdp-listing.json"), pages, dims)
    write_previews(out_dir)
    write_cover_images(out_dir, dims[2])
    make_print_safe(out_dir)
    problems = preflight(out_dir, pages)
    if cover_note:
        import pymupdf
        r = pymupdf.open(os.path.join(out_dir, "cover.pdf"))[0].rect
        if abs(r.width / 72 - dims[0]) > 0.02 or abs(r.height / 72 - dims[1]) > 0.02:
            problems.append(f"Canva cover is {r.width / 72:.3f} x {r.height / 72:.3f} in but KDP needs "
                            f"{dims[0]:.3f} x {dims[1]:.3f} in - re-export it from Canva at the new size")
    lp = os.path.join(out_dir, "kdp-listing.json")
    with open(lp, encoding="utf-8") as f:
        L = json.load(f)
    L["preflight"] = {"passed": not problems, "problems": problems}
    with open(lp, "w", encoding="utf-8") as f:
        json.dump(L, f, indent=2)
    import copy_sheet
    sheet = copy_sheet.make(out_dir)
    print(f"Artwork: {'AI images' if ART['source'] == 'ai' else 'original drawings'}; cover: {cover_note or 'generated'}")
    print(f"Built {pages}-page interior + cover ({dims[0]:.3f} x {dims[1]:.3f} in, spine {dims[2]:.4f} in)")
    print("KDP preflight: " + ("PASSED" if not problems else "PROBLEMS:\n  - " + "\n  - ".join(problems)))
    print(f"Copy sheet: {sheet}")
    print(f"Output: {out_dir}")


if __name__ == "__main__":
    main()
