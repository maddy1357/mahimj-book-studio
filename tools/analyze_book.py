"""
mahimj-books :: import ANY finished book PDF and get it ready for KDP.

import_book(pdf, description) ->
  1. copies the PDF into ready-to-publish/<name>/interior.pdf
  2. analyses it: page count, trim size, bleed, colour, text, other people's brands/copyright
  3. text AI writes the listing (title, subtitle, description, 7 keywords, 3 categories, age, low-content)
  4. builds a matching wrap-around cover from the book's own pages
  5. prices for every Amazon store, KDP print check, copy sheet

Usage: python analyze_book.py <file.pdf> ["what the book is about"]
"""
import json
import os
import re
import shutil
import sys

import numpy as np
import pymupdf

import ai_images
import build_alphabet_book as B
import cover_builder
import finalize
import kdp_rules
import llm

HERE = os.path.dirname(os.path.abspath(__file__))
READY = os.path.abspath(os.path.join(HERE, "..", "ready-to-publish"))

LISTING_SCHEMA = llm.obj({
    "title": llm.STR, "subtitle": llm.STR, "book_type": llm.STR,
    "description_html": llm.STR, "keywords": llm.STRS, "categories": llm.STRS,
    "reading_age_min": llm.INT, "reading_age_max": llm.INT,
    "low_content": llm.BOOL, "low_content_reason": llm.STR,
    "back_heading": llm.STR, "back_text": llm.STR, "features": llm.STRS,
    "marketing": llm.STRS,
})

SYSTEM = ("You are an Amazon KDP publishing expert. Write accurate, honest, appealing listing metadata for a "
          "paperback. Rules: title and subtitle must match what is printed in the book when visible; description "
          "in simple HTML (<p>, <b>, <ul><li>) under 1500 characters with no claims the book doesn't support; exactly "
          "7 keywords, each under 50 characters, no brand names or other authors; 3 Amazon category paths in the form "
          "\"Books > ... \" or \"Children's Books > ...\"; reading ages only for children's books (else 0 and 0); "
          "low_content is true only for journals, notebooks, planners, logbooks (colouring and activity books are NOT "
          "low-content); 5 short back-cover feature bullets; 5 concrete, policy-compliant marketing actions "
          "(no paid or fake reviews).")

BRAND_RE = re.compile(r"(\b[\w-]+\.(?:com|net|org|in|co|io|ai)\b|©\s*\d{4}[^\n]{0,40}|copyright[^\n]{0,60}|"
                      r"all rights reserved[^\n]{0,40}|published by[^\n]{0,40}|illustrated by[^\n]{0,40})", re.I)


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:50] or "book"


def analyse_pdf(pdf_path):
    doc = pymupdf.open(pdf_path)
    p0 = doc[0].rect
    w, h = p0.width / 72, p0.height / 72
    trim = kdp_rules.nearest_trim(w, h)
    text = ""
    for pg in doc:
        text += pg.get_text() + "\n"
        if len(text) > 12000:
            break
    colour_pages = 0
    sample_idx = sorted({0, min(3, len(doc) - 1), len(doc) // 2, len(doc) - 1})
    samples = []
    for i in range(len(doc)):
        pix = doc[i].get_pixmap(dpi=20)
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[..., :3].astype(int)
        if (a.max(axis=2) - a.min(axis=2) > 40).mean() > 0.01:
            colour_pages += 1
    for i in sample_idx:
        samples.append(doc[i].get_pixmap(dpi=45).tobytes("png"))
    found = sorted({m.group(0).strip()[:60] for m in BRAND_RE.finditer(text)})
    own = (B.BRAND.lower(), B.AUTHOR.lower(), "mahimj")
    flags = [f for f in found if not any(o in f.lower() for o in own)]
    return {"pages": len(doc), "page_w": round(w, 4), "page_h": round(h, 4), "trim": trim,
            "text": text[:12000], "colour_pages": colour_pages, "rights_flags": flags[:12],
            "image_only": len(text.strip()) < 40, "samples": samples}


def picture_pages(pdf_path, out_dir, n=10):
    """Render the busiest pages as square thumbnails for the cover cards."""
    doc = pymupdf.open(pdf_path)
    scored = []
    for i, pg in enumerate(doc):
        pix = pg.get_pixmap(dpi=12, colorspace=pymupdf.csGRAY)
        a = np.frombuffer(pix.samples, dtype=np.uint8)
        scored.append(((a < 200).mean(), i))
    picks = [i for s, i in sorted(scored, reverse=True) if s > 0.02][:n]
    paths = []
    for k, i in enumerate(sorted(picks)):
        pg = doc[i]
        r = pg.rect
        side = min(r.width, r.height) * 0.92
        clip = pymupdf.Rect(r.x0 + (r.width - side) / 2, r.y0 + (r.height - side) / 2,
                            r.x0 + (r.width + side) / 2, r.y0 + (r.height + side) / 2)
        p = os.path.join(out_dir, f"thumb-{k + 1}.png")
        pg.get_pixmap(dpi=150, clip=clip).save(p)
        paths.append(p)
    return paths


def ask_listing(info, description, filename, settings=None):
    prompt = (f"File name: {filename}\nPages: {info['pages']}\nPage size: {info['page_w']} x {info['page_h']} in\n"
              f"Colour pages: {info['colour_pages']} of {info['pages']}\n"
              f"Publisher's own description: {description or '(none given)'}\n"
              f"Author: {B.AUTHOR}  Imprint: {B.BRAND}\n\nText found in the book (may be empty for picture books):\n"
              f"{info['text'][:8000]}")
    return llm.ask_json(SYSTEM, prompt, LISTING_SCHEMA, settings, images=info["samples"])


def import_book(pdf_path, description="", settings=None, log=print, listing_override=None):
    info = analyse_pdf(pdf_path)
    name = slugify(os.path.splitext(os.path.basename(pdf_path))[0])
    book_dir = os.path.join(READY, name)
    n = 2
    while os.path.exists(book_dir):
        book_dir = os.path.join(READY, f"{name}-{n}")
        n += 1
    os.makedirs(os.path.join(book_dir, "imported"), exist_ok=True)
    shutil.copyfile(pdf_path, os.path.join(book_dir, "imported", "original.pdf"))
    shutil.copyfile(pdf_path, os.path.join(book_dir, "interior.pdf"))
    log(f"Analysed: {info['pages']} pages, {info['page_w']} x {info['page_h']} in, "
        f"{info['colour_pages']} colour pages")
    meta = listing_override or ask_listing(info, description, os.path.basename(pdf_path), settings)
    log(f"Listing written by AI: {meta['title']}")
    cfg = {"builder": "imported", "art_source": "imported", "cover_source": "generated",
           "description": description, "meta": meta,
           "analysis": {k: v for k, v in info.items() if k not in ("samples", "text")}}
    ai_images.save_book_config(book_dir, cfg)
    return rebuild(book_dir, log=log)


def rebuild(book_dir, log=print):
    cfg = ai_images.book_config(book_dir)
    meta, a = cfg["meta"], cfg["analysis"]
    trim = a.get("trim")
    if trim:
        tw, th, bleed = trim
    else:
        tw, th, bleed = a["page_w"], a["page_h"], False
    pages = a["pages"]
    thumbs = picture_pages(os.path.join(book_dir, "interior.pdf"), os.path.join(book_dir, "imported"))
    canva = os.path.join(book_dir, "cover-canva.pdf")
    age = f"{meta['reading_age_min']}-{meta['reading_age_max']}" if meta.get("reading_age_max") else None
    cover_builder.build_cover(os.path.join(book_dir, "cover-generated.pdf"), tw, th, pages, "white", meta["title"],
                              meta["subtitle"], B.AUTHOR, meta["back_heading"], meta["back_text"],
                              meta["features"], thumbs, age_badge=age)
    shutil.copyfile(canva if cfg.get("cover_source") == "canva" and os.path.exists(canva)
                    else os.path.join(book_dir, "cover-generated.pdf"), os.path.join(book_dir, "cover.pdf"))
    L = finalize.base_listing(meta["title"], meta["subtitle"], B.AUTHOR, meta["description_html"],
                              meta["keywords"], meta["categories"], meta.get("reading_age_min", 0),
                              meta.get("reading_age_max", 0), tw, th, pages, bleed,
                              low_content=meta.get("low_content", False),
                              extra={"book_type": "imported", "marketing": meta.get("marketing", []),
                                     "rights_flags": a.get("rights_flags", []),
                                     "rights_confirmed": cfg.get("rights_confirmed", False)})
    if a["colour_pages"]:
        L["print"]["ink_and_paper"] += f"  (NOTE: {a['colour_pages']} pages have colour - choose a colour option in KDP if you want it printed in colour)"
    problems = []
    if not trim:
        problems.append(f"page size {a['page_w']} x {a['page_h']} in is not a KDP trim size - export the PDF at a KDP size")
    probs, warnings = finalize.finalize(book_dir, L, strict_margins=bool(not trim or not trim[2]))
    problems += probs
    if problems != probs:
        L["preflight"]["problems"] = problems
        L["preflight"]["passed"] = False
        with open(os.path.join(book_dir, "kdp-listing.json"), "w", encoding="utf-8") as f:
            json.dump(L, f, indent=2)
    log(f"KDP print check: {'PASSED' if not problems else 'PROBLEMS: ' + '; '.join(problems)}")
    return book_dir


if __name__ == "__main__":
    print(import_book(os.path.abspath(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else ""))
