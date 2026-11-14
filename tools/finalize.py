"""
mahimj-books :: last step for every book type
listing -> previews -> cover images -> print-safe files -> KDP print check -> copy sheet
"""
import json
import os
import re

import numpy as np
import pymupdf

import build_alphabet_book as B
import copy_sheet
import kdp_rules


def cover_images(book_dir, trim_w, trim_h, spine):
    pg = pymupdf.open(os.path.join(book_dir, "cover.pdf"))[0]
    bl = kdp_rules.BLEED_IN * 72
    front = pymupdf.Rect(bl + trim_w * 72 + spine * 72, bl, bl + 2 * trim_w * 72 + spine * 72, bl + trim_h * 72)
    pix = pg.get_pixmap(dpi=300, clip=front)
    pix.save(os.path.join(book_dir, "cover-front.jpg"), jpg_quality=95)
    pix.save(os.path.join(book_dir, "cover-front.png"))
    pg.get_pixmap(dpi=300).save(os.path.join(book_dir, "cover-full-wrap.jpg"), jpg_quality=92)


def preflight(book_dir, L, strict_margins=True):
    """Returns (problems, warnings). Problems block upload; warnings are shown."""
    p = L["print"]
    tw, th = p["trim_w"], p["trim_h"]
    bleed = p.get("has_bleed", False)
    problems, warnings = [], []
    doc = pymupdf.open(os.path.join(book_dir, "interior.pdf"))
    n = len(doc)
    if n < kdp_rules.MIN_PAGES:
        problems.append(f"interior has {n} pages - KDP paperbacks need at least {kdp_rules.MIN_PAGES}")
    if n > kdp_rules.MAX_PAGES_BW:
        problems.append(f"interior has {n} pages - more than KDP's maximum {kdp_rules.MAX_PAGES_BW}")
    ew, eh = (tw + kdp_rules.BLEED_IN, th + 2 * kdp_rules.BLEED_IN) if bleed else (tw, th)
    bad = [i + 1 for i, pg in enumerate(doc) if abs(pg.rect.width / 72 - ew) > 0.02 or abs(pg.rect.height / 72 - eh) > 0.02]
    if bad:
        problems.append(f"{len(bad)} page(s) are not {ew:.3f} x {eh:.3f} in (e.g. page {bad[0]})")
    safe = (0.375 if not bleed else 0.375 + kdp_rules.BLEED_IN) * 72
    near = []
    for i, pg in enumerate(doc):
        pix = pg.get_pixmap(dpi=36, colorspace=pymupdf.csGRAY)
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        ys, xs = np.nonzero(a < 200)
        if len(xs):
            k = 72 / 36
            edge = np.minimum(np.minimum(xs, ys), np.minimum(pix.width - 1 - xs, pix.height - 1 - ys)) * k
            if edge.min() < safe - 2 * k:
                near.append(i + 1)
        for img in pg.get_images(full=True):
            for r in pg.get_image_rects(img[0]):
                if r.width > 36 and img[2] / (r.width / 72) < 200:
                    warnings.append(f"page {i + 1}: an image is only {img[2] / (r.width / 72):.0f} DPI (300 recommended)")
    if near:
        msg = (f"{len(near)} page(s) have ink within 0.375 in of the edge (e.g. page {near[0]}) - "
               "KDP may cut it off" + ("" if bleed else "; if the art should touch the edge, the PDF needs bleed"))
        (problems if strict_margins else warnings).append(msg)
    fonts_missing = sorted({f[3] for pg in doc for f in pg.get_fonts() if f[1] == "n/a"})
    if fonts_missing:
        problems.append("fonts not embedded: " + ", ".join(fonts_missing[:5]))
    raw = open(os.path.join(book_dir, "interior.pdf"), "rb").read()
    if b"/SMask" in raw or re.search(rb"/(ca|CA)\s+0?\.\d", raw):
        warnings.append("interior uses transparency - KDP usually accepts it; flatten it if the previewer complains")
    cv = pymupdf.open(os.path.join(book_dir, "cover.pdf"))[0]
    cw, ch = cv.rect.width / 72, cv.rect.height / 72
    W, H = p["cover_size_in"]["width"], p["cover_size_in"]["height"]
    if abs(cw - W) > 0.02 or abs(ch - H) > 0.02:
        problems.append(f"cover is {cw:.3f} x {ch:.3f} in but KDP needs {W:.3f} x {H:.3f} in")
    for img in cv.get_images(full=True):
        for r in cv.get_image_rects(img[0]):
            if r.width > 0.9 * cv.rect.width and img[2] / (r.width / 72) < 299:
                problems.append(f"cover image only {img[2] / (r.width / 72):.0f} DPI (KDP needs 300)")
    if L.get("rights_flags") and not L.get("rights_confirmed"):
        problems.append("the book mentions other brands/websites/copyright (" + ", ".join(L["rights_flags"][:4]) +
                        ") - confirm you own the rights before uploading")
    return sorted(set(problems)), sorted(set(warnings))


def finalize(book_dir, L, strict_margins=True, interior_safe=True):
    p = L["print"]
    lp = os.path.join(book_dir, "kdp-listing.json")
    with open(lp, "w", encoding="utf-8") as f:
        json.dump(L, f, indent=2)
    B.write_previews(book_dir)
    cover_images(book_dir, p["trim_w"], p["trim_h"], p["cover_size_in"]["spine"])
    old_title = B.TITLE
    B.TITLE = L["title"]
    try:
        B.make_print_safe(book_dir) if interior_safe else None
    finally:
        B.TITLE = old_title
    problems, warnings = preflight(book_dir, L, strict_margins)
    L["preflight"] = {"passed": not problems, "problems": problems, "warnings": warnings}
    with open(lp, "w", encoding="utf-8") as f:
        json.dump(L, f, indent=2)
    copy_sheet.make(book_dir)
    return problems, warnings


def base_listing(title, subtitle, author, description_html, keywords, categories, age_min, age_max,
                 trim_w, trim_h, pages, has_bleed, paper="white", low_content=False, ai_text=None,
                 ai_images_=None, extra=None):
    """Listing fields shared by every book type (the copy sheet and uploader read these)."""
    large = kdp_rules.is_large_trim(trim_w, trim_h)
    W, H, sp = kdp_rules.cover_size(trim_w, trim_h, pages, paper)
    us_price, printing = kdp_rules.recommend_us_price(pages, large)
    L = {
        "format": "paperback", "language": "English",
        "title": title, "subtitle": subtitle, "author": author,
        "publisher_imprint": B.BRAND, "copyright_holder": B.BRAND,
        "description": description_html,
        "keywords": [k[:50] for k in keywords][:7],
        "categories_suggested": categories[:3],
        "reading_age": {"min": age_min, "max": age_max} if age_min or age_max else {},
        "adult_content": False,
        "low_content": bool(low_content),
        "low_content_note": ("Low-content (journals, notebooks, planners): no free KDP ISBN - publish without one or use your own."
                             if low_content else "Not low-content - leave the box unchecked and use a free KDP ISBN."),
        "ai_disclosure": {"text": ai_text, "images": ai_images_},
        "territories": "All territories (worldwide rights)",
        "print": {
            "isbn": "Publish without an ISBN (or use your own)" if low_content else "Use free KDP ISBN",
            "ink_and_paper": f"Black & white interior with {paper} paper",
            "paper": paper, "trim_w": trim_w, "trim_h": trim_h,
            "trim_size": f"{trim_w:g} x {trim_h:g} in",
            "bleed": "Bleed (PDF only)" if has_bleed else "No bleed", "has_bleed": has_bleed,
            "cover_finish": "Matte", "page_count": pages,
            "cover_size_in": {"width": round(W, 4), "height": round(H, 4), "spine": round(sp, 4)},
            "printing_cost_usd_estimate": printing,
        },
        "files": {"interior": "interior.pdf", "cover": "cover.pdf"},
        "price_usd_suggested": us_price,
        "marketplace_prices": kdp_rules.marketplace_prices(us_price, pages, large),
        "kdp_account_url": "https://kdp.amazon.com/en_US/account",
        "status": "awaiting_approval",
    }
    L.update(extra or {})
    return L
