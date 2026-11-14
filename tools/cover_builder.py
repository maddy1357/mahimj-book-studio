"""
mahimj-books :: general wrap-around paperback cover (back + spine + front, with bleed)
for any KDP trim size. Used for new theme books and for imported books.
"""
import hashlib

from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

import build_alphabet_book as B
import kdp_rules

PALETTES = ["#4CC9F0", "#FFB703", "#8AC926", "#FF8FAB", "#9B5DE5", "#00BBF9", "#F15BB5", "#06D6A0"]
INK = HexColor("#1A1A1A")


def _palette(title):
    h = int(hashlib.md5(title.encode()).hexdigest(), 16)
    return PALETTES[h % len(PALETTES)]


def _card(c, img_path, cx, cy, size):
    c.saveState()
    c.setFillColor(white)
    c.setStrokeColor(INK)
    c.setLineWidth(3)
    c.roundRect(cx - size / 2, cy - size / 2, size, size, size * 0.12, stroke=1, fill=1)
    c.restoreState()
    if img_path:
        pad = size * 0.1
        c.drawImage(ImageReader(img_path), cx - size / 2 + pad, cy - size / 2 + pad, size - 2 * pad,
                    size - 2 * pad, preserveAspectRatio=True, anchor="c")


def build_cover(path, trim_w, trim_h, pages, paper, title, subtitle, author, back_heading, back_text,
                features, images, age_badge=None, bg=None):
    """images: list of picture file paths (up to 6 front, 4 back). Returns (W_in, H_in, spine_in)."""
    W_in, H_in, sp = kdp_rules.cover_size(trim_w, trim_h, pages, paper)
    PW, PH, BL, SP = trim_w * 72, trim_h * 72, kdp_rules.BLEED_IN * 72, sp * 72
    W, H = W_in * 72, H_in * 72
    k = min(PW / 612, PH / 792)                    # scale relative to the 8.5x11 layout
    bgc = HexColor(bg or _palette(title))
    c = canvas.Canvas(path, pagesize=(W, H), initialFontName="Body")
    c.setTitle(f"{title} - Cover")
    c.setAuthor(author)
    c.setCreator(B.BRAND)
    c.setProducer(B.BRAND)
    c.setFillColor(bgc)
    c.rect(0, 0, W, H, stroke=0, fill=1)

    # ---------- front ----------
    c.saveState()
    c.translate(BL + PW + SP, BL)
    words = title.upper().split()
    line1, line2 = (" ".join(words[:len(words) // 2 + len(words) % 2]), " ".join(words[len(words) // 2 + len(words) % 2:])) \
        if len(" ".join(words)) > 16 else (" ".join(words), "")
    y = PH - 120 * k
    B.bubble_text(c, line1, PW / 2, y, B.fit_size(line1, PW - 70 * k, 100 * k), outline=3.5)
    if line2:
        y -= 90 * k
        B.bubble_text(c, line2, PW / 2, y, B.fit_size(line2, PW - 70 * k, 80 * k), fills=B.RAINBOW, outline=3)
    c.setFont("Fun", max(12, 20 * k))
    c.setFillColor(INK)
    for i, ln in enumerate(simpleSplit(subtitle, "Fun", max(12, 20 * k), PW - 90 * k)[:2]):
        c.drawCentredString(PW / 2, y - 40 * k - i * 24 * k, ln)
    front = images[:6]
    size = min(168 * k, (PW - 80 * k) / 3 - 18 * k)
    xs = [PW / 2 - size - 18 * k, PW / 2, PW / 2 + size + 18 * k]
    top = y - 70 * k - size / 2 - (24 * k if len(subtitle) > 40 else 0)
    for i, img in enumerate(front):
        _card(c, img, xs[i % 3], top - (i // 3) * (size + 18 * k), size)
    c.setFont("BodyBold", max(12, 22 * k))
    c.setFillColor(white)
    c.drawCentredString(PW / 2, 112 * k, f"by {author}")
    lw, lh = B.logo_size(1.5 * k)
    c.setFillColor(white)
    c.roundRect(PW / 2 - lw / 2 - 16 * k, 34 * k, lw + 32 * k, lh + 16 * k, 14 * k, stroke=0, fill=1)
    B.draw_logo(c, PW / 2, 34 * k + 8 * k + 6 * 1.5 * k, scale=1.5 * k, color=True, align="center")
    if age_badge:
        F = B.Fill(color=True)
        c.setStrokeColor(INK)
        c.setLineWidth(3)
        F.lw = 3
        B.star(c, F, PW - 92 * k, 112 * k, 54 * k, "#FFCA3A", ri=0.72)
        c.setFillColor(INK)
        c.setFont("Fun", 14 * k)
        c.drawCentredString(PW - 92 * k, 114 * k, "AGES")
        c.setFont("Fun", 18 * k)
        c.drawCentredString(PW - 92 * k, 95 * k, age_badge)
    c.restoreState()

    # ---------- back ----------
    c.saveState()
    c.translate(BL, BL)
    box_top, box_h = PH - 52 * k, 300 * k
    c.setFillColor(white)
    c.roundRect(54 * k, box_top - box_h, PW - 108 * k, box_h, 24 * k, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("Fun", max(14, 26 * k))
    c.drawCentredString(PW / 2, box_top - 44 * k, back_heading[:48])
    fs = max(9, 12.5 * k)
    c.setFont("Body", fs)
    yy = box_top - 80 * k
    for ln in simpleSplit(back_text, "Body", fs, PW - 170 * k)[:6]:
        c.drawCentredString(PW / 2, yy, ln)
        yy -= fs * 1.45
    yy -= 6 * k
    c.setFont("BodyBold", max(9, 13 * k))
    for f in features[:5]:
        if yy < box_top - box_h + 18 * k:
            break
        F2 = B.Fill(color=True)
        c.setStrokeColor(INK)
        c.setLineWidth(1.5)
        F2.lw = 1.5
        B.star(c, F2, 92 * k, yy + 5 * k, 8 * k, "#FFCA3A")
        c.setFillColor(INK)
        c.drawString(108 * k, yy, f[:70])
        yy -= 24 * k
    for i, img in enumerate(images[6:10] or images[:4]):
        cs = 100 * k
        _card(c, img, 110 * k + i * 124 * k, box_top - box_h - 80 * k, cs)
    lw, lh = B.logo_size(1.5 * k)
    c.setFillColor(white)
    c.roundRect(54 * k, 54 * k, lw + 32 * k, lh + 16 * k, 14 * k, stroke=0, fill=1)
    B.draw_logo(c, 70 * k, 54 * k + 8 * k + 6 * 1.5 * k, scale=1.5 * k, color=True)
    c.setFont("Body", max(8, 10 * k))
    c.setFillColor(INK)
    c.drawString(58 * k, 118 * k, B.COPYRIGHT_LINE)
    c.restoreState()
    c.save()
    return W_in, H_in, sp
