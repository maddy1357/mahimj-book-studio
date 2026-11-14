# mahimj-books · Book Studio

A Windows desktop app that runs the **whole Amazon KDP paperback lifecycle** for the
mahimj-books imprint:

**idea → approve → create the book → preview → KDP listing → upload → grow sales**

It builds print-ready colouring books (interior PDF + wrap-around cover), checks them against
KDP's print rules, writes every KDP field for you (with copy buttons), sets prices that earn the
60% royalty in every Amazon store, and can fill the KDP website for you as a draft. You always
make the final **Publish** click yourself.

---

## What it does

| Tab | What you do there |
|---|---|
| **1 Book & Preview** | Pick a book, see the cover and every page, rebuild it, run the KDP print check. **Import a book PDF** to analyse any finished book and get it ready for KDP. |
| **2 AI Images** | Generate the pictures with AI (free option included), regenerate any picture you don't like, **✨ Recreate book with AI**. Also where you choose the **Text AI**. |
| **3 Canva Design** | Make a Canva kit (exact KDP cover guide, logos, pictures), design the cover in Canva, import it back - the size is checked against KDP. |
| **4 KDP Copy Sheet** | Every field of KDP's three pages in KDP's own order, each with a **Copy** button (the description copies with its formatting), plus every store's price. |
| **5 Upload to KDP** | **Approve & Upload**: opens KDP in Edge, you sign in, the app fills the forms and uploads the PDFs as a **draft**. It never presses Publish. |
| **6 💡 Next Book Ideas** | AI suggests your next books, checks each one against your existing books and earlier ideas (near-duplicates are replaced automatically), explains why it sells and how to get more buyers. **Approve & create book** builds the whole book. |

### The full lifecycle

```
 6 Next Book Ideas ──► Approve & create book
                            │  AI draws every page + colour cover pictures
                            ▼
 1 Book & Preview  ◄── book PDF + cover PDF + prices + KDP print check
        │  (or: Import a book PDF -> AI analyses it and writes the listing)
        ▼
 3 Canva Design (optional cover redesign)
        ▼
 4 KDP Copy Sheet ── copy/paste every field      5 Upload to KDP ── auto-fill as draft
        ▼
 You press "Publish" on KDP  ──►  6 "How to get more buyers"
```

---

## Install and run (Windows)

1. Install **Python 3.11+** from python.org (tick *Add python.exe to PATH*).
2. Install **Microsoft Edge** or Google Chrome (already on Windows 11).
3. Download this repository (green **Code** button → *Download ZIP*, or `git clone`).
4. Double-click **`run.bat`**. The first run installs the packages from `requirements.txt` and
   builds the sample A-Z book.

Or from a terminal in the project folder:

```bash
pip install -r requirements.txt
python app.py
```

Tip: create a desktop shortcut to `pythonw.exe app.py` (with `company-logo/app.ico` as its icon)
to start it without a console window.

### Set up the AI (once)

Open **2 AI Images** and press **Save settings** after filling in:

| Setting | Free? | Used for |
|---|---|---|
| **Cloudflare Account ID + API token** | ✅ free daily allowance | Pictures (FLUX.1-schnell, Apache-2.0 - commercial use allowed) **and** the free Text AI (Llama 3.3) |
| Hugging Face token | free credits | Pictures (backup) |
| **Anthropic API key** | paid | Text AI **Claude Opus 5.5** - best listings, ideas and book analysis (can read the book's pages) |
| OpenAI / Stability keys | paid | Pictures (optional) |

Cloudflare: sign up at dash.cloudflare.com → copy the **Account ID** → My Profile → API Tokens →
*Create Token* → template **Workers AI**. Keys are saved only on your PC in
`%APPDATA%\mahimj-books\settings.json` - never in this folder or the repository.

---

## Everyday use

**Make a new book**
1. **6 Next Book Ideas** → *Suggest 5 new books*. Read why each sells and how it is different.
2. Don't like one? **Change idea** (optionally say why). Like it? **Approve & create book**.
3. The app draws the pictures, builds the interior, cover, prices and copy sheet, and opens the book.
4. Check every page in **1 Book & Preview**; regenerate any picture in **2 AI Images**.

**Bring in a book you already made**
**1 Book & Preview → Import a book PDF**. The app reads the page size and count, bleed, colour
pages, and any other people's names / websites / © notices (it blocks upload until you confirm you
own the rights). The Text AI writes title, subtitle, description, 7 keywords, 3 categories and the
reading age; the app builds a matching cover from the book's own pages.

**Publish on KDP**
1. **4 KDP Copy Sheet**: copy each field into KDP (or **5 Upload to KDP** to auto-fill a draft).
2. Paperback Content: upload `interior.pdf` first, then `cover.pdf` with
   *Upload a cover you already have* (not Cover Creator). Leave the barcode box unchecked.
3. Launch Previewer (maximise the window), Approve, set the prices from the sheet, Publish.

---

## KDP rules the app applies

- Trim sizes, bleed, 0.375 in safe margin, 24-828 pages, embedded fonts, flattened 300 DPI cover.
- Spine = pages × 0.002252 in (white paper); cover = 2 × trim + spine + 0.25 in bleed.
- Colouring/activity books are **not** low-content → free KDP ISBN; journals/planners are.
- Royalty: 60% at/above **$9.99 / £7.99 / €9.99 / CA$13.99 / A$13.99 / ¥1000 / 40 zł / 110 kr**,
  50% below (since June 2025). The app prices every store above its threshold.
- Printing-cost and currency numbers are estimates calibrated on a real KDP screen -
  KDP's Rights & Pricing page always shows the exact figures.
- AI disclosure: books made with AI pictures/text are marked "AI-generated" in the copy sheet.

## How to get more buyers (built into tab 6)

Price at $9.99 · all 7 keyword boxes · 3 specific categories · A+ Content · small Sponsored
Products ads · Author Central page · build a series · launch seasonal books 6-8 weeks early ·
share sample pages on Pinterest/Instagram · ask for honest reviews (never pay for or swap reviews).

---

## Safety built in

- **Never presses Publish** and never assigns the ISBN for you (both are permanent).
- **Rights check** on imported books: other brands, websites and © notices block the upload until
  you confirm you own the rights. Don't publish other people's books.
- No Amazon scraping: market notes on ideas are AI estimates, not live sales data.
- Your KDP password is typed only into the real KDP page; the browser session is stored in
  `.kdp-browser-profile/` (ignored by git - keep it private).

## Project layout

```
app.py                       the desktop app (6 tabs)
run.bat                      install + start
requirements.txt
company-logo/                logo.png, name.png, app.ico
tools/
  build.py                   rebuild any book (dispatches by type)
  build_alphabet_book.py     the original A-Z book (vector art or AI art)
  build_theme_book.py        books created from an approved idea
  analyze_book.py            import + analyse any PDF
  ideas.py                   next-book ideas, duplicate check, growth playbook
  cover_builder.py           wrap-around cover for any trim size
  finalize.py                listing, previews, print-safe files, KDP print check, copy sheet
  kdp_rules.py               trims, spine, printing cost, royalty thresholds, store prices
  ai_images.py               image AI (Cloudflare, Hugging Face, OpenAI, Stability) + line-art cleaning
  llm.py                     text AI (Cloudflare Llama free / Claude Opus 5.5)
  copy_sheet.py              KDP copy sheet (in-app tab + HTML page)
  canva_kit.py               Canva round trip for covers
  kdp_upload.py              fills KDP in Edge as a draft (Playwright)
ready-to-publish/<book>/     output per book (ignored by git): interior.pdf, cover.pdf,
                             cover-front.jpg, kdp-listing.json, kdp-copy-sheet.html, previews
```

## Troubleshooting

| KDP says | Fix |
|---|---|
| *This is not a valid image file* | You chose Cover Creator - choose **Upload a cover you already have** and upload `cover.pdf`. |
| *Error processing cover* | Check trim size (8.5 x 11), **white** paper, upload the manuscript first, then the cover. |
| *Browser window is too small* | Maximise the browser (or F11 / Ctrl -) before Launch Previewer. |
| *Account information incomplete* | Save as Draft → finish tax interview + bank details in your KDP account → publish. |
| Build failed in the app | The message shows the error; the print check lists what to fix. |

---

© mahimj-books. All rights reserved.
