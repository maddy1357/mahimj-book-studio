"""
The A-Z Alphabet Colouring Book (the first mahimj-books title).

Pictures: the 26 original vector drawings, or AI pictures from ai-images/<letter>.png when
"AI images" is switched on in the app. Layout: 8.5 x 11 in, single-sided, tracing row per letter.
"""
import os
import random

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from .. import config
from ..config import AUTHOR, BRAND, COPYRIGHT_LINE
from ..kdp import rules
from . import finalize
from .alphabet_art import (LETTERS, d_apple, d_ball, d_cat, d_fish, d_house, d_owl, d_rocket, d_sun, d_umbrella,
                           d_zebra)
from .design import (BLEED, GREY, INK, PAGE_H, PAGE_W, RAINBOW, WHITE, Fill, bubble_text, draw_logo, draw_picture,
                     fit_size, footer, frame, logo_size, page_belongs, page_copyright, star, trace_text)

TITLE = "Alphabet Colouring Book"
SUBTITLE = "Trace, Learn & Colour from A to Z"      # must match the cover text (KDP rule)
SINGLE_SIDED = True                                 # blank back behind every colouring page
DESCRIPTION = (
    "<p><b>Learn your ABCs the fun way!</b></p>"
    "<p>This alphabet colouring book from mahimj-books helps children discover the letters "
    "A to Z with 26 big, friendly, original pictures - from a shiny Apple to a stripy Zebra.</p>"
    "<ul><li>26 A-Z pictures with thick, easy-to-colour lines</li>"
    "<li>Big bubble letters and words to colour</li>"
    "<li>Letter tracing practice on every page</li>"
    "<li>Large 8.5 x 11 inch pages, printed single-sided so markers don't bleed through</li>"
    "<li>Perfect for toddlers, preschool and kindergarten (ages 2-5)</li></ul>")
KEYWORDS = ["alphabet colouring book for toddlers", "abc coloring book ages 2-5", "letter tracing book for preschool",
            "kindergarten activity book", "learn abc coloring pages kids", "toddler coloring book big pictures",
            "a to z coloring workbook"]
CATEGORIES = ["Children's Books > Activities, Crafts & Games > Activity Books > Coloring Books",
              "Children's Books > Activities, Crafts & Games > Activity Books",
              "Children's Books > Early Learning > Basic Concepts > Alphabet"]

ART = {"source": "vector", "dir": None}     # set by build() from book-config.json


def image_path(book_dir, letter):
    """Where the AI picture for a letter lives."""
    return os.path.join(config.art_dir(book_dir), f"{letter}.png")


def place_art(c, letter, fn, x, y, size, F):
    """AI picture for this letter when AI art is on and it exists, else the vector drawing."""
    if ART["source"] == "ai" and ART["dir"]:
        p = os.path.join(ART["dir"], f"{letter}.png")
        if os.path.exists(p):
            c.drawImage(p, x, y, size, size)
            return
    draw_picture(c, fn, x, y, size, F)


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
    page(page_copyright, TITLE, SUBTITLE)  # p2 (back of title)
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
    spine = rules.spine_in(page_count) * 72
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
# Build
# --------------------------------------------------------------------------
def build(book_dir, log=print):
    os.makedirs(book_dir, exist_ok=True)
    cfg = config.book_config(book_dir)
    cfg.setdefault("builder", "alphabet")
    config.save_book_config(book_dir, cfg)
    ART["source"], ART["dir"] = cfg.get("art_source", "vector"), config.art_dir(book_dir)
    pages = build_interior(os.path.join(book_dir, "interior.pdf"))
    build_cover(os.path.join(book_dir, "cover-generated.pdf"), pages)
    finalize.choose_cover(book_dir)
    listing = finalize.base_listing(TITLE, SUBTITLE, AUTHOR, DESCRIPTION, KEYWORDS, CATEGORIES, 2, 5, 8.5, 11, pages,
                                    False, ai_text="AI-generated", ai_images_="AI-generated",
                                    extra={"book_type": "alphabet"})
    listing["print"]["single_sided"] = SINGLE_SIDED
    problems, _ = finalize.finalize(book_dir, listing)
    log(f"Built {pages}-page A-Z book ({'AI' if ART['source'] == 'ai' else 'original'} pictures). "
        f"KDP print check: {'PASSED' if not problems else 'PROBLEMS: ' + '; '.join(problems)}")
    return problems
