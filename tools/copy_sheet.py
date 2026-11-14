"""
mahimj-books :: KDP copy sheet
Generates <book_dir>/kdp-copy-sheet.html - every KDP field in the same order
as KDP's three tabs (Details / Content / Rights & Pricing), each with a Copy
button, so the listing can be pasted into KDP by hand.

Usage: python copy_sheet.py <book_dir>
"""
import base64
import html
import io
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "..", "company-logo", "logo.png")


def logo_data_uri():
    try:
        im = Image.open(LOGO).convert("RGBA")
        im = im.crop(im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox())
        im.thumbnail((96, 96))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def strip_html(s):
    import re
    s = re.sub(r"</(p|li|ul)>", "\n", s)
    s = re.sub(r"<li>", "• ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def _trim_label(p):
    tw, th = p.get("trim_w"), p.get("trim_h")
    if not tw:
        return p["trim_size"]
    return f"{tw:g} x {th:g} in ({tw * 2.54:.2f} x {th * 2.54:.2f} cm)"


def _ai_rows(L):
    d = L.get("ai_disclosure") or {"text": "AI-generated", "images": "AI-generated"}
    t, i = d.get("text"), d.get("images")
    if not t and not i:
        return [("choice", "AI-generated content", "Answer truthfully",
                 "This book was imported - say Yes if any AI tool wrote text or made images, and name the tool.")]
    rows = [("choice", "AI-generated content", "Yes" if "AI" in f"{t}{i}" else "No", "")]
    for label, v in (("Text", t), ("Images", i)):
        rows.append(("choice", f" {label}", v or "None", ""))
        if v and "AI" in v:
            rows.append(("copy", f" {label} – tool used", d.get("tool", "Claude (Anthropic)"), ""))
    return rows


def _price_rows(L):
    sym = {"USD": "$", "CAD": "$", "AUD": "$", "GBP": "£", "EUR": "€", "JPY": "¥", "PLN": "zł ", "SEK": "kr "}
    rows = []
    for m in L.get("marketplace_prices", []):
        s = sym.get(m["currency"], "")
        th = m["threshold_60"]
        th_txt = f"{s}{th:,.0f}" if m["currency"] == "JPY" else f"{s}{th:.2f}"
        if m["action"] == "keep":
            rows.append(("info", f"{m['store']} ({m['currency']})", f"Keep KDP's price ({m['price']})",
                         f"Already at or above the 60% threshold ({th_txt}). Nothing to change."))
        else:
            rows.append(("copy", f"{m['store']} ({m['currency']})", m["price"],
                         f"Type this. 60% royalty from {th_txt} – about {s}{m['royalty_60']:.2f} per copy "
                         f"(printing {s}{m['printing']:.2f}). Below the threshold KDP pays only 50%."))
    if not rows:
        rows.append(("copy", "List price – Amazon.com (USD)", f"{L.get('price_usd_suggested', '')}", ""))
    return rows


def load_listing(book_dir):
    with open(os.path.join(book_dir, "kdp-listing.json"), encoding="utf-8") as f:
        return json.load(f)


def build_sections(book_dir, L=None):
    """[(step, title, [(kind, label, value, note), ...]), ...]
    kind: copy | rich (formatted HTML) | choice (select in KDP) | info"""
    L = L or load_listing(book_dir)
    p = L["print"]
    first, _, last = L["author"].rpartition(" ")
    if not first:
        first, last = L["author"], ""
    interior = os.path.join(book_dir, L["files"]["interior"])
    cover = os.path.join(book_dir, L["files"]["cover"])
    ra = L.get("reading_age", {})

    # (kind, label, value, note)  kind: copy | rich | choice | info
    sections = [
        # Order and wording follow KDP's "Paperback Details" page exactly.
        ("1", "Paperback Details", [
            ("choice", "Language", "English", "Dropdown at the top of the page."),
            ("copy", "Book Title", L["title"], "Exactly as on the cover."),
            ("copy", "Subtitle (Optional)", L.get("subtitle", ""),
             "Matches the cover text. KDP puts a colon between title and subtitle."),
            ("info", "Series (optional)", "Skip – don't click 'Add to series'", ""),
            ("info", "Edition number (Optional)", "Leave blank", "Cannot be changed after publishing."),
            ("info", "Author – Prefix", "Leave blank", ""),
            ("copy", "Author – First name", first, ""),
            ("info", "Author – Middle name", "Leave blank", ""),
            ("copy", "Author – Last name", last, "Name can only be edited within 72 hours of publication."),
            ("info", "Author – Suffix", "Leave blank", ""),
            ("info", "Contributors (Optional)", "Click 'Remove' on the empty row", "No other contributors for this book."),
            ("rich", "Description", L["description"],
             "Copies with formatting (bold + bullet list). Click inside KDP's description box and press Ctrl+V."),
            ("copy", "Description – HTML (Source button)", L["description"],
             "Only if formatting doesn't paste: click 'Source' in KDP's editor, paste this, click 'Source' again."),
            ("choice", "Publishing Rights", "I own the copyright and I hold necessary publishing rights.", ""),
            ("choice", "Sexually Explicit Images or Title", "No",
             "Answer this first – KDP won't let you choose categories until you do."),
            ("choice", "Reading age – Minimum", f"{ra.get('min', '')} years", "Dropdown."),
            ("choice", "Reading age – Maximum", f"{ra.get('max', '')} years", "Dropdown."),
            ("choice", "Primary marketplace", "Amazon.com", ""),
        ] + [("copy", f"Category {i + 1}", c,
              "Click 'Choose categories', search the last word (e.g. '" + c.split(" > ")[-1] + "'), tick this path.")
             for i, c in enumerate(L.get("categories_suggested", [])[:3])] + [
            ("choice", "Low-content book", "TICK it" if L.get("low_content") else "Leave UNCHECKED",
             L.get("low_content_note", "KDP help: colouring/activity books are not low-content. Checking it removes the free ISBN.")),
            ("choice", "Large-print book", "Leave UNCHECKED", ""),
        ] + [("copy", f"Keyword {i + 1}", k, f"{len(k)} / 50 characters")
             for i, k in enumerate(L.get("keywords", [])[:7])] + [
            ("choice", "Publication Date", "Publication date and release date are the same",
             "Already selected by default – the book hasn't been published before."),
            ("choice", "Release Date", "Release my book for sale now",
             "Already selected. After you submit, it takes up to 72 hours to go live and can't be edited meanwhile."),
            ("info", "Then", "Click 'Save and Continue' → Paperback Content", ""),
        ]),
        ("2", "Paperback Content", [
            ("choice", "Print ISBN", "Publish without an ISBN (or enter your own)" if L.get("low_content") else "Assign me a free KDP ISBN",
             "Low-content books can't use a free KDP ISBN." if L.get("low_content")
             else "Permanent for this book. Imprint shows as 'Independently published'."),
            ("choice", "Ink and paper type", p["ink_and_paper"], ""),
            ("choice", "Trim size", _trim_label(p), "Must match the PDF page size, or KDP rejects the files."),
            ("choice", "Bleed settings", p["bleed"], ""),
            ("choice", "Paperback cover finish", p["cover_finish"], ""),
            ("choice", "Reading direction", "Left to right", ""),
            ("copy", "Manuscript file (interior.pdf)", interior,
             "Click 'Upload paperback manuscript', paste this path into the File name box, press Enter."),
            ("choice", "Book cover", "Upload a cover you already have (print-ready PDF only)",
             "NOT 'Use Cover Creator' - Cover Creator only takes JPG/PNG images and replaces your design with a KDP template."),
            ("copy", "Cover file (cover.pdf)", cover,
             "Upload the manuscript FIRST and wait for 'uploaded successfully' - KDP needs its page count "
             "to check the cover size. Then click 'Upload your cover file', paste this path, press Enter."),
            ("choice", "Does your cover include a barcode?", "Leave 'Yes, my cover has a barcode' UNCHECKED",
             "KDP adds the barcode for you, free. The back cover has an empty space for it at the bottom right "
             "(2 x 1.2 in) - nothing of the design is covered."),
        ] + _ai_rows(L) + [
            ("choice", " Translations", "No", ""),
            ("choice", "Confirm answers (orange box)", "Tick 'By clicking this, I confirm that my answers are accurate'",
             "Appears after uploading a new manuscript or cover. 'Save and Continue' stays grey until it is ticked "
             "and the previewer is approved."),
            ("info", "Book preview", "Launch Previewer → check every page → Approve",
             "Quality Check should show 0 issues. If KDP says 'browser window is too small', maximise the "
             "window (or F11 / zoom out with Ctrl -) - the previewer needs at least 1200 x 600 pixels."),
            ("info", "Request a book proof", "Optional – order a printed proof copy",
             "Costs only printing + shipping. Good for checking paper and line thickness before selling."),
        ]),
        ("3", "Rights & Pricing", [
            ("choice", "Territories", L.get("territories", "All territories (worldwide rights)"), ""),
            ("choice", "Primary marketplace", "Amazon.com", ""),
        ] + _price_rows(L) + [
            ("choice", "Expanded Distribution", "Leave UNCHECKED",
             "Only 40% royalty (about $1.16 per copy in the US) and not available in most stores."),
            ("info", "Terms & Conditions", "Read them – publishing means you agree", ""),
            ("link", "Account information incomplete?", L.get("kdp_account_url", "https://kdp.amazon.com/en_US/account"),
             "If KDP shows the red 'Account information incomplete' box, Publish stays grey. Click 'Save as Draft', open "
             "your account and complete: 1) author/publisher info and address, 2) Getting paid - bank account "
             "(or Payoneer/Wise), 3) Tax information interview (as a non-US individual; India has a tax treaty "
             "with the US that lowers the withholding on royalties). Then come back and publish."),
            ("info", "Proof copy", "Optional – order one to check paper and print", ""),
            ("info", "Publish", "Press 'Publish Your Paperback Book' yourself when everything is green",
             "Review takes up to 72 hours."),
        ]),
    ]
    return sections


def make(book_dir):
    L = load_listing(book_dir)
    p = L["print"]
    sections = build_sections(book_dir, L)
    rows_html = []
    n = 0
    for num, title, rows in sections:
        rows_html.append(f'<section><h2><span class="step">{num}</span>{html.escape(title)}</h2>')
        for kind, label, value, note in rows:
            n += 1
            fid = f"f{n}"
            if kind == "rich":
                val = f'<div class="val rich" id="{fid}">{value}</div>' \
                      f'<textarea hidden id="{fid}-plain">{html.escape(strip_html(value))}</textarea>'
            else:
                val = f'<div class="val" id="{fid}">{html.escape(value)}</div>'
            if kind in ("copy", "rich"):
                btn = f'<button class="copy" data-target="{fid}" data-rich="{1 if kind == "rich" else 0}">Copy</button>'
            elif kind == "link":
                btn = f'<a class="linkbtn" href="{html.escape(value)}" target="_blank" rel="noopener">Open</a>'
            elif kind == "choice":
                btn = '<span class="tag">Select</span>'
            else:
                btn = '<span class="tag muted">Info</span>'
            note_html = f'<div class="note">{html.escape(note)}</div>' if note else ""
            rows_html.append(
                f'<div class="row {kind}"><label class="done"><input type="checkbox" data-key="{fid}"></label>'
                f'<div class="lab">{html.escape(label)}</div><div class="cell">{val}{note_html}</div>'
                f'<div class="act">{btn}</div></div>')
        rows_html.append("</section>")

    logo = logo_data_uri()
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KDP Copy Sheet</title>
<style>
:root {{
  --bg:#F4F6FA; --card:#FFFFFF; --ink:#14213D; --muted:#5B6475; --line:#E2E6EE;
  --brand:#0B2A8A; --accent:#14B8D4; --ok:#1E8E5A; --chip:#EEF2FB;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{ --bg:#0E1320; --card:#161D2E; --ink:#E7ECF5; --muted:#9AA5B8;
    --line:#26304A; --brand:#7FA2FF; --accent:#3FD3EE; --ok:#4CC38A; --chip:#1E2740; }}
}}
:root[data-theme="dark"] {{ --bg:#0E1320; --card:#161D2E; --ink:#E7ECF5; --muted:#9AA5B8;
    --line:#26304A; --brand:#7FA2FF; --accent:#3FD3EE; --ok:#4CC38A; --chip:#1E2740; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.45 "Segoe UI", system-ui, sans-serif; }}
header {{ position:sticky; top:0; z-index:2; background:var(--card); border-bottom:1px solid var(--line);
  display:flex; align-items:center; gap:14px; padding:12px 16px; }}
header img {{ height:40px; }}
header h1 {{ font-size:18px; margin:0; }}
header .sub {{ color:var(--muted); font-size:13px; }}
header .prog {{ margin-left:auto; font-size:13px; color:var(--muted); white-space:nowrap; }}
main {{ max-width:980px; margin:0 auto; padding:16px; }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:12px; margin:0 0 18px; overflow:hidden; }}
h2 {{ margin:0; padding:12px 16px; font-size:16px; border-bottom:1px solid var(--line); display:flex; align-items:center; gap:10px; }}
.step {{ background:var(--brand); color:#fff; border-radius:50%; width:24px; height:24px; display:inline-grid; place-items:center; font-size:13px; }}
.row {{ display:grid; grid-template-columns:28px 210px 1fr 86px; gap:10px; align-items:start; padding:10px 16px; border-bottom:1px solid var(--line); }}
.row:last-child {{ border-bottom:0; }}
.row.isdone .lab, .row.isdone .val {{ opacity:.45; }}
.lab {{ font-weight:600; padding-top:6px; }}
.val {{ background:var(--chip); border-radius:8px; padding:6px 10px; word-break:break-word; white-space:pre-wrap; }}
.val.rich {{ white-space:normal; }}
.val.rich p {{ margin:0 0 6px; }} .val.rich ul {{ margin:0; padding-left:20px; }}
.note {{ color:var(--muted); font-size:12.5px; margin-top:4px; }}
.done {{ padding-top:7px; }} .done input {{ width:16px; height:16px; accent-color:var(--ok); }}
button.copy {{ width:100%; border:0; border-radius:8px; padding:7px 0; font:600 14px "Segoe UI", sans-serif;
  background:var(--brand); color:#fff; cursor:pointer; }}
button.copy:hover {{ filter:brightness(1.12); }}
button.copy.copied {{ background:var(--ok); }}
a.linkbtn {{ display:block; text-align:center; border-radius:8px; padding:7px 0; font:600 14px "Segoe UI", sans-serif; background:var(--accent); color:#04222b; text-decoration:none; }}
.tag {{ display:block; text-align:center; font-size:12px; padding:7px 0; border-radius:8px; border:1px dashed var(--line); color:var(--muted); }}
@media (max-width:700px) {{
  .row {{ grid-template-columns:24px 1fr; }}
  .lab {{ grid-column:2; padding-top:2px; }} .cell {{ grid-column:1 / -1; }} .act {{ grid-column:1 / -1; }}
  header .prog {{ display:none; }}
}}
</style></head>
<body>
<header>
  {'<img src="' + logo + '" alt="">' if logo else ''}
  <div><h1>KDP Copy Sheet – {html.escape(L['title'])}</h1>
  <div class="sub">{html.escape(L['author'])} • {html.escape(L.get('publisher_imprint', ''))} • {p['page_count']} pages • {html.escape(p['trim_size'])}</div></div>
  <div class="prog" id="prog"></div>
</header>
<main>
{''.join(rows_html)}
<p class="note">Tick the box on each row as you go – ticks are remembered in this browser.</p>
</main>
<script>
const STORE = "kdp-sheet-" + {json.dumps(L['title'])};
function load() {{ try {{ return JSON.parse(localStorage.getItem(STORE) || "{{}}"); }} catch (e) {{ return {{}}; }} }}
function save(s) {{ try {{ localStorage.setItem(STORE, JSON.stringify(s)); }} catch (e) {{}} }}
const state = load();
const boxes = [...document.querySelectorAll('.done input')];
function refresh() {{
  let d = 0;
  boxes.forEach(b => {{ b.closest('.row').classList.toggle('isdone', b.checked); if (b.checked) d++; }});
  document.getElementById('prog').textContent = d + " / " + boxes.length + " done";
}}
boxes.forEach(b => {{ b.checked = !!state[b.dataset.key];
  b.addEventListener('change', () => {{ state[b.dataset.key] = b.checked; save(state); refresh(); }}); }});
refresh();

function fallbackCopy(el, rich) {{
  const sel = window.getSelection(); const r = document.createRange();
  let tmp = null;
  if (rich) {{ r.selectNodeContents(el); }}
  else {{ tmp = document.createElement('textarea'); tmp.value = el.innerText; document.body.appendChild(tmp); tmp.select(); }}
  if (rich) {{ sel.removeAllRanges(); sel.addRange(r); }}
  const ok = document.execCommand('copy');
  if (tmp) tmp.remove(); sel.removeAllRanges();
  return ok;
}}
async function doCopy(btn) {{
  const id = btn.dataset.target, rich = btn.dataset.rich === "1";
  const el = document.getElementById(id);
  let ok = false;
  try {{
    if (rich && window.ClipboardItem) {{
      const plain = document.getElementById(id + '-plain').value;
      await navigator.clipboard.write([new ClipboardItem({{
        'text/html': new Blob([el.innerHTML], {{type: 'text/html'}}),
        'text/plain': new Blob([plain], {{type: 'text/plain'}}) }})]);
    }} else {{
      await navigator.clipboard.writeText(el.innerText);
    }}
    ok = true;
  }} catch (e) {{ ok = fallbackCopy(el, rich); }}
  btn.textContent = ok ? "Copied ✓" : "Select & Ctrl+C";
  btn.classList.toggle('copied', ok);
  const row = btn.closest('.row').querySelector('.done input');
  if (ok && row && !row.checked) {{ row.checked = true; state[row.dataset.key] = true; save(state); refresh(); }}
  setTimeout(() => {{ btn.textContent = "Copy"; btn.classList.remove('copied'); }}, 1600);
}}
document.querySelectorAll('button.copy').forEach(b => b.addEventListener('click', () => doCopy(b)));
</script>
</body></html>"""
    out = os.path.join(book_dir, "kdp-copy-sheet.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    return out


if __name__ == "__main__":
    print(make(os.path.abspath(sys.argv[1])))
