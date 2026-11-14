"""
Theme colouring books (any list of subjects), 8.5 x 11 in, single-sided - built from an approved idea.

<book>/book-spec.json: title, subtitle, theme, audience, age_min, age_max, page_subjects[],
  description_html, keywords[], categories[], features[], back_heading, back_text
Pictures: <book>/ai-images/NN.png (line art) and cover-N.png (colour), generated when missing.
"""
import json
import os

from reportlab.pdfgen import canvas

from ..ai import images
from ..config import AUTHOR, BRAND, COPYRIGHT_LINE, art_dir
from . import cover as cover_builder
from . import design as D
from . import finalize

PAGE_W, PAGE_H = D.PAGE_W, D.PAGE_H


def load_spec(book_dir):
    with open(os.path.join(book_dir, "book-spec.json"), encoding="utf-8") as f:
        return json.load(f)


def pic(book_dir, i):
    return os.path.join(art_dir(book_dir), f"{i + 1:02d}.png")


def cover_pic(book_dir, i):
    return os.path.join(art_dir(book_dir), f"cover-{i + 1}.png")


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
        images.generate_image(path, subject, settings, color=color)
    return True


def _title_lines(title):
    words = title.upper().split()
    if len(title) <= 16:
        return [title.upper()]
    half = (len(words) + 1) // 2
    return [" ".join(words[:half]), " ".join(words[half:])]


def page_title(c, spec, book_dir):
    D.frame(c)
    y = 640
    for ln in _title_lines(spec["title"]):
        D.bubble_text(c, ln, PAGE_W / 2, y, D.fit_size(ln, 480, 80))
        y -= 84
    c.setFont("Fun", 18)
    c.setFillColor(D.INK)
    c.drawCentredString(PAGE_W / 2, y + 30, spec["subtitle"][:70])
    for i, x in enumerate((96, 326)):
        if os.path.exists(pic(book_dir, i)):
            c.drawImage(pic(book_dir, i), x, 190, 190, 190)
    c.setFont("BodyBold", 18)
    c.drawCentredString(PAGE_W / 2, 140, f"by {spec.get('author', AUTHOR)}")
    D.draw_logo(c, PAGE_W / 2, 86, scale=1.6, align="center")


def page_subject(c, book_dir, i, subject):
    D.frame(c)
    c.setFillColor(D.INK)
    c.setFont("Fun", 26)
    c.drawCentredString(PAGE_W / 2, 705, f"Colour the {subject.lower()}!")
    c.drawImage(pic(book_dir, i), 86, 210, 440, 440)
    word = subject.upper()
    D.bubble_text(c, word, PAGE_W / 2, 110, D.fit_size(word, 480, 80))
    D.footer(c)


def page_end(c, spec, book_dir):
    D.frame(c)
    D.bubble_text(c, "GREAT JOB!", PAGE_W / 2, 600, D.fit_size("GREAT JOB!", 460, 90))
    c.setFont("Fun", 22)
    c.setFillColor(D.INK)
    c.drawCentredString(PAGE_W / 2, 545, "You finished the whole book!")
    if os.path.exists(pic(book_dir, 0)):
        c.drawImage(pic(book_dir, 0), 196, 240, 220, 220)
    c.setFont("Body", 13)
    c.drawCentredString(PAGE_W / 2, 175, f"Look for more fun books from {BRAND}.")
    D.draw_logo(c, PAGE_W / 2, 120, scale=1.5, align="center")
    c.setFont("Body", 9)
    c.setFillColor(D.GREY)
    c.drawCentredString(PAGE_W / 2, 40, COPYRIGHT_LINE)


def build_interior(path, spec, book_dir):
    c = canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H), initialFontName="Body")
    c.setTitle(spec["title"])
    c.setAuthor(spec.get("author", AUTHOR))
    c.setCreator(BRAND)
    c.setProducer(BRAND)
    n = 0

    def page(draw=None, *args):
        """Draw one page (or leave it blank) and start the next."""
        nonlocal n
        if draw:
            draw(c, *args)
        c.showPage()
        n += 1

    page(page_title, spec, book_dir)
    page(D.page_copyright, spec["title"], spec["subtitle"])
    page(D.page_belongs)
    page()                                   # blank: pictures start on right-hand pages
    for i, subject in enumerate(spec["page_subjects"]):
        page(page_subject, book_dir, i, subject)
        page()                               # blank back - no bleed-through
    page(page_end, spec, book_dir)
    if n % 2:
        page()
    c.save()
    return n


def build(book_dir, generate=True, settings=None, log=print):
    spec = load_spec(book_dir)
    spec.setdefault("author", AUTHOR)
    if generate:
        generate_images(book_dir, spec, settings, log)
    if missing_images(book_dir, spec):
        raise RuntimeError(f"{len(missing_images(book_dir, spec))} pictures are missing - generate them first.")
    pages = build_interior(os.path.join(book_dir, "interior.pdf"), spec, book_dir)
    age = f"{spec['age_min']}-{spec['age_max']}" if spec.get("age_max") else None
    imgs = [cover_pic(book_dir, i) for i in range(6)] + [pic(book_dir, i) for i in range(6, 10)
                                                         if i < len(spec["page_subjects"])]
    imgs = [p for p in imgs if os.path.exists(p)]
    feats = spec.get("features") or [f"{len(spec['page_subjects'])} big pictures to colour",
                                     "Single-sided pages - no bleed-through", "Large 8.5 x 11 inch pages"]
    cover_builder.build_cover(os.path.join(book_dir, "cover-generated.pdf"), 8.5, 11, pages, "white", spec["title"],
                              spec["subtitle"], spec["author"], spec.get("back_heading", spec["title"]),
                              spec.get("back_text", ""), feats, imgs, age_badge=age)
    finalize.choose_cover(book_dir)
    L = finalize.base_listing(spec["title"], spec["subtitle"], spec["author"], spec["description_html"],
                              spec["keywords"], spec["categories"], spec.get("age_min", 0), spec.get("age_max", 0),
                              8.5, 11, pages, False, ai_text="AI-generated", ai_images_="AI-generated",
                              extra={"book_type": "theme", "theme": spec.get("theme", ""),
                                     "marketing": spec.get("marketing", []), "idea": spec.get("idea", {})})
    L["print"]["single_sided"] = True
    problems, _ = finalize.finalize(book_dir, L)
    log(f"Built {pages}-page book. KDP print check: {'PASSED' if not problems else 'PROBLEMS: ' + '; '.join(problems)}")
    return problems

