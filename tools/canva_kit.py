"""
mahimj-books :: Canva round trip for the book cover

make_kit(book_dir)          -> <book_dir>/canva-kit/  (exact KDP size guide, current cover,
                               logos, every A-Z picture in colour as transparent PNG, README)
import_cover(book_dir, pdf) -> checks the Canva PDF against KDP's cover size and uses it
use_generated_cover(book_dir)
"""
import json
import os
import shutil

import pymupdf
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_DIR = os.path.abspath(os.path.join(HERE, "..", "company-logo"))
BLEED_IN, SAFE_IN = 0.125, 0.25
BARCODE_W_IN, BARCODE_H_IN = 2.0, 1.2


def _listing(book_dir):
    with open(os.path.join(book_dir, "kdp-listing.json"), encoding="utf-8") as f:
        return json.load(f)


def cover_size(book_dir):
    c = _listing(book_dir)["print"]["cover_size_in"]
    return c["width"], c["height"], c["spine"]


def _font(size):
    for f in ("segoeuib.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", f), size)
        except Exception:
            pass
    return ImageFont.load_default()


def guide_png(path, W, H, spine, dpi=150):
    """Transparent overlay: bleed, trim, safe area, spine and barcode zone."""
    px = lambda inch: int(round(inch * dpi))
    w, h = px(W), px(H)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    b = px(BLEED_IN)
    red, blue, green, grey = (230, 40, 40, 255), (30, 90, 230, 255), (20, 150, 80, 255), (90, 90, 90, 255)
    # bleed band
    for box in ((0, 0, w, b), (0, h - b, w, h), (0, 0, b, h), (w - b, 0, w, h)):
        d.rectangle(box, fill=(230, 40, 40, 70))
    d.rectangle((b, b, w - b, h - b), outline=red, width=3)                     # trim
    s = px(BLEED_IN + SAFE_IN)
    trim_w = (W - 2 * BLEED_IN - spine) / 2
    back_r = px(BLEED_IN + trim_w)
    front_l = px(BLEED_IN + trim_w + spine)
    for x0, x1 in ((s, back_r - px(SAFE_IN)), (front_l + px(SAFE_IN), w - s)):  # safe areas
        for x in range(x0, x1, 24):
            d.line((x, s, min(x + 12, x1), s), fill=blue, width=2)
            d.line((x, h - s, min(x + 12, x1), h - s), fill=blue, width=2)
        for y in range(s, h - s, 24):
            d.line((x0, y, x0, min(y + 12, h - s)), fill=blue, width=2)
            d.line((x1, y, x1, min(y + 12, h - s)), fill=blue, width=2)
    d.rectangle((back_r, 0, front_l, h), fill=(30, 90, 230, 50))                # spine
    d.line((back_r, 0, back_r, h), fill=blue, width=2)
    d.line((front_l, 0, front_l, h), fill=blue, width=2)
    bx1 = back_r - px(SAFE_IN)
    by1 = h - s
    d.rectangle((bx1 - px(BARCODE_W_IN), by1 - px(BARCODE_H_IN), bx1, by1), fill=(255, 210, 60, 160),
                outline=(160, 110, 0, 255), width=3)
    f, fs = _font(px(0.32)), _font(px(0.14))
    d.text((bx1 - px(BARCODE_W_IN) + 10, by1 - px(BARCODE_H_IN) + 10), "BARCODE AREA\nkeep empty", fill=(120, 80, 0, 255), font=fs)
    d.text(((s + back_r) // 2 - px(1.1), px(0.6)), "BACK COVER", fill=grey, font=f)
    d.text(((front_l + w) // 2 - px(1.2), px(0.6)), "FRONT COVER", fill=grey, font=f)
    d.text((s + 6, h - s - px(0.45)), f"Red = trim/bleed  •  blue dashes = keep text inside\n"
                                      f"Blue band = spine ({spine:.4f} in, no text under 79 pages)", fill=green, font=fs)
    im.save(path, dpi=(dpi, dpi))


def make_kit(book_dir):
    kit = os.path.join(book_dir, "canva-kit")
    art = os.path.join(kit, "pictures")
    os.makedirs(art, exist_ok=True)
    W, H, spine = cover_size(book_dir)
    guide_png(os.path.join(kit, "1-kdp-cover-guide.png"), W, H, spine)
    gen = os.path.join(book_dir, "cover-generated.pdf")
    if not os.path.exists(gen):
        gen = os.path.join(book_dir, "cover.pdf")
    pymupdf.open(gen)[0].get_pixmap(dpi=200).save(os.path.join(kit, "2-current-cover.png"))
    for name in ("logo.png", "name.png"):
        src = os.path.join(LOGO_DIR, name)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(kit, "3-" + name))

    # every picture in colour on a transparent background
    import build_alphabet_book as B
    from reportlab.pdfgen import canvas
    tmp = os.path.join(kit, "_tmp.pdf")
    for letter, word, fn in B.LETTERS:
        c = canvas.Canvas(tmp, pagesize=(220, 220))
        B.draw_picture(c, fn, 10, 10, 200, B.Fill(color=True), lw=2.6)
        c.save()
        name = f"{letter}-{word.lower().replace(' ', '-')}.png"
        pymupdf.open(tmp)[0].get_pixmap(dpi=450, alpha=True).save(os.path.join(art, name))
    os.remove(tmp)

    with open(os.path.join(kit, "README.txt"), "w", encoding="utf-8") as f:
        f.write(f"""CANVA COVER KIT - {_listing(book_dir)['title']}

1. In Canva: Create a design > Custom size > units: in
      Width  {W:.3f} in
      Height {H:.3f} in
   (this is back + spine + front, including the 0.125 in bleed on every side)

2. Upload 1-kdp-cover-guide.png, place it over the whole page as the top layer
   (it is transparent). Keep text inside the blue dashed boxes, keep the yellow
   barcode area on the back cover empty, no text on the spine.
   2-current-cover.png is the cover the app made - use it as a starting point.
   3-logo.png / 3-name.png are your company logo files.
   pictures/ has every A-Z picture in colour with a transparent background.

3. DELETE the guide layer before exporting.

4. Share > Download > PDF Print
      - do NOT tick "Crop marks and bleed" (the bleed is already in the size)
      - tick "Flatten PDF"
   Then in Book Studio > Canva Design tab > "Import cover PDF from Canva".

If the page count changes, the spine changes: make a new kit and resize the design.
""")
    return kit


def import_cover(book_dir, pdf_path):
    W, H, spine = cover_size(book_dir)
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as e:
        return False, f"Could not open the PDF: {e}"
    if len(doc) != 1:
        return False, f"The cover PDF must have exactly 1 page (it has {len(doc)})."
    r = doc[0].rect
    w, h = r.width / 72, r.height / 72
    if abs(w - W) > 0.02 or abs(h - H) > 0.02:
        return False, (f"Size is {w:.3f} x {h:.3f} in, but KDP needs {W:.3f} x {H:.3f} in.\n"
                       "Resize the Canva design to the size in canva-kit/README.txt and export again "
                       "(without 'Crop marks and bleed').")
    doc.close()
    shutil.copyfile(pdf_path, os.path.join(book_dir, "cover-canva.pdf"))
    import ai_images
    cfg = ai_images.book_config(book_dir)
    cfg["cover_source"] = "canva"
    ai_images.save_book_config(book_dir, cfg)
    return True, f"Canva cover imported ({w:.3f} x {h:.3f} in). Rebuilding the book to use it."


def use_generated_cover(book_dir):
    import ai_images
    cfg = ai_images.book_config(book_dir)
    cfg["cover_source"] = "generated"
    ai_images.save_book_config(book_dir, cfg)
