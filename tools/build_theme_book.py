"""
mahimj-books :: theme colouring book builder (any subject list), 8.5 x 11 in, single-sided.

Reads <book_dir>/book-spec.json (written when you approve an idea):
  title, subtitle, theme, audience, age_min, age_max, page_subjects[], description_html,
  keywords[], categories[], features[], back_heading, back_text
Pictures: <book_dir>/ai-images/NN.png (line art) and cover-N.png (colour) - generated if missing.

Usage: python build_theme_book.py <book_dir>
"""
import json
import os
import sys

import ai_images
import build_alphabet_book as B
import cover_builder
import finalize
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = B.PAGE_W, B.PAGE_H


def load_spec(book_dir):
    with open(os.path.join(book_dir, "book-spec.json"), encoding="utf-8") as f:
        return json.load(f)


def pic(book_dir, i):
    return os.path.join(ai_images.art_dir(book_dir), f"{i + 1:02d}.png")


def cover_pic(book_dir, i):
    return os.path.join(ai_images.art_dir(book_dir), f"cover-{i + 1}.png")


def missing_images(book_dir, spec):
    subj = spec["page_subjects"]
    todo = [(pic(book_dir, i), s, False) for i, s in enumerate(subj) if not os.path.exists(pic(book_dir, i))]
    todo += [(cover_pic(book_dir, i), subj[i], True) for i in range(min(6, len(subj)))
             if not os.path.exists(cover_pic(book_dir, i))]
    return todo


def generate_images(book_dir, spec, settings=None, log=print, stop=lambda: False):
    todo = missing_images(book_dir, spec)
    for n, (path, subject, color) in enumerate(todo, 1):
        if stop():
            return False
        log(f"Picture {n}/{len(todo)}: {subject}{' (cover, colour)' if color else ''}")
        ai_images.generate_image(path, subject, settings, color=color)
    return True


def _title_lines(title):
    words = title.upper().split()
    if len(title) <= 16:
        return [title.upper()]
    half = (len(words) + 1) // 2
    return [" ".join(words[:half]), " ".join(words[half:])]


def page_title(c, spec, book_dir):
    B.frame(c)
    y = 640
    for ln in _title_lines(spec["title"]):
        B.bubble_text(c, ln, PAGE_W / 2, y, B.fit_size(ln, 480, 80))
        y -= 84
    c.setFont("Fun", 18)
    c.setFillColor(B.INK)
    c.drawCentredString(PAGE_W / 2, y + 30, spec["subtitle"][:70])
    for i, x in enumerate((96, 326)):
        if os.path.exists(pic(book_dir, i)):
            c.drawImage(pic(book_dir, i), x, 190, 190, 190)
    c.setFont("BodyBold", 18)
    c.drawCentredString(PAGE_W / 2, 140, f"by {spec.get('author', B.AUTHOR)}")
    B.draw_logo(c, PAGE_W / 2, 86, scale=1.6, align="center")


def page_subject(c, book_dir, i, subject):
    B.frame(c)
    c.setFillColor(B.INK)
    c.setFont("Fun", 26)
    c.drawCentredString(PAGE_W / 2, 705, f"Colour the {subject.lower()}!")
    c.drawImage(pic(book_dir, i), 86, 210, 440, 440)
    word = subject.upper()
    B.bubble_text(c, word, PAGE_W / 2, 110, B.fit_size(word, 480, 80))
    B.footer(c)


def page_end(c, spec, book_dir):
    B.frame(c)
    B.bubble_text(c, "GREAT JOB!", PAGE_W / 2, 600, B.fit_size("GREAT JOB!", 460, 90))
    c.setFont("Fun", 22)
    c.setFillColor(B.INK)
    c.drawCentredString(PAGE_W / 2, 545, "You finished the whole book!")
    if os.path.exists(pic(book_dir, 0)):
        c.drawImage(pic(book_dir, 0), 196, 240, 220, 220)
    c.setFont("Body", 13)
    c.drawCentredString(PAGE_W / 2, 175, f"Look for more fun books from {B.BRAND}.")
    B.draw_logo(c, PAGE_W / 2, 120, scale=1.5, align="center")
    c.setFont("Body", 9)
    c.setFillColor(B.GREY)
    c.drawCentredString(PAGE_W / 2, 40, B.COPYRIGHT_LINE)


def build_interior(path, spec, book_dir):
    c = canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H), initialFontName="Body")
    c.setTitle(spec["title"])
    c.setAuthor(spec.get("author", B.AUTHOR))
    c.setCreator(B.BRAND)
    c.setProducer(B.BRAND)
    n = 0

    def show():
        nonlocal n
        c.showPage()
        n += 1

    page_title(c, spec, book_dir); show()
    B.page_copyright(c); show()
    B.page_belongs(c); show()
    show()                                   # blank: pictures start on right-hand pages
    for i, subject in enumerate(spec["page_subjects"]):
        page_subject(c, book_dir, i, subject); show()
        show()                               # blank back - no bleed-through
    page_end(c, spec, book_dir); show()
    if n % 2:
        show()
    c.save()
    return n


def build(book_dir, generate=True, settings=None, log=print):
    spec = load_spec(book_dir)
    spec.setdefault("author", B.AUTHOR)
    if generate:
        generate_images(book_dir, spec, settings, log)
    if missing_images(book_dir, spec):
        raise RuntimeError(f"{len(missing_images(book_dir, spec))} pictures are missing - generate them first.")
    B.TITLE, B.SUBTITLE = spec["title"], spec["subtitle"]
    pages = build_interior(os.path.join(book_dir, "interior.pdf"), spec, book_dir)
    age = f"{spec['age_min']}-{spec['age_max']}" if spec.get("age_max") else None
    imgs = [cover_pic(book_dir, i) for i in range(6)] + [pic(book_dir, i) for i in range(6, 10)
                                                         if i < len(spec["page_subjects"])]
    imgs = [p for p in imgs if os.path.exists(p)]
    feats = spec.get("features") or [f"{len(spec['page_subjects'])} big pictures to colour",
                                     "Single-sided pages - no bleed-through", "Large 8.5 x 11 inch pages"]
    cover_builder.build_cover(os.path.join(book_dir, "cover.pdf"), 8.5, 11, pages, "white", spec["title"],
                              spec["subtitle"], spec["author"], spec.get("back_heading", spec["title"]),
                              spec.get("back_text", ""), feats, imgs, age_badge=age)
    L = finalize.base_listing(spec["title"], spec["subtitle"], spec["author"], spec["description_html"],
                              spec["keywords"], spec["categories"], spec.get("age_min", 0), spec.get("age_max", 0),
                              8.5, 11, pages, False, ai_text="AI-generated", ai_images_="AI-generated",
                              extra={"book_type": "theme", "theme": spec.get("theme", ""),
                                     "marketing": spec.get("marketing", []), "idea": spec.get("idea", {})})
    L["print"]["single_sided"] = True
    problems, warnings = finalize.finalize(book_dir, L)
    log(f"Built {pages}-page book. KDP print check: {'PASSED' if not problems else 'PROBLEMS: ' + '; '.join(problems)}")
    return problems


if __name__ == "__main__":
    build(os.path.abspath(sys.argv[1]))
