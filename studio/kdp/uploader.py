"""
mahimj-books :: KDP paperback uploader (semi-automatic)

Opens Amazon KDP in a real Edge window, waits for YOU to sign in, then
fills the paperback "Details" and "Content" pages from kdp-listing.json and
uploads interior.pdf + cover.pdf.

Safety rules built in:
  * Your password is never seen or stored by this script - you type it in
    the browser. The login session is kept in .kdp-browser-profile/ (private, not in git).
  * It NEVER clicks "Publish". It stops so you can review and publish yourself.
  * It does not assign the free ISBN (that choice is permanent) - you click it.

Every step is best-effort: each field is looked up by KDP's element id first,
then by its visible label. If a field still can't be found the script says
which one and keeps going. It also saves the page's field list (names/labels
only - never values) to <book_dir>/kdp-debug/ so selectors can be fixed.

Used by the app's "Upload to KDP" tab (run(book_dir, log_fn)).
"""
import json
import os
import re
import sys
import time

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from ..config import BROWSER_PROFILE

KDP_HOME = "https://kdp.amazon.com/en_US/bookshelf"
KDP_NEW_PAPERBACK = "https://kdp.amazon.com/en_US/title-setup/paperback/new/details?ref_=cr_ti"
PROFILE_DIR = BROWSER_PROFILE

done, todo = [], []
BOOK_DIR = None
LOG_FN = None          # set by the app to show progress in its window


def log(msg):
    line = time.strftime("[%H:%M:%S] ") + msg
    if LOG_FN:
        LOG_FN(line)
    else:
        print(line, flush=True)


def ok(what):
    done.append(what)
    log("  OK    " + what)


def manual(what):
    todo.append(what)
    log("  TODO  " + what)


# ---------------------------------------------------------------------------
# locating elements: CSS selectors first, then accessible label / text
# ---------------------------------------------------------------------------
def find(page, css=(), labels=(), timeout=2500):
    for sel in css:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:
            pass
    for lab in labels:
        for getter in (lambda: page.get_by_label(lab, exact=False),
                       lambda: page.get_by_placeholder(lab, exact=False)):
            try:
                loc = getter().first
                loc.wait_for(state="visible", timeout=timeout)
                return loc
            except Exception:
                pass
    return None


def fill(page, what, value, css=(), labels=()):
    if not value:
        return
    loc = find(page, css, labels)
    if loc is None:
        manual(f"{what}: {value}")
        return
    try:
        loc.click()
        loc.fill(value)
        ok(what)
    except Exception as e:
        manual(f"{what}: {value} ({e.__class__.__name__})")


def check(page, what, css=(), labels=(), texts=(), required=True):
    loc = find(page, css, labels)
    if loc is None:
        for t in texts:
            try:
                loc = page.get_by_text(t, exact=False).first
                loc.wait_for(state="visible", timeout=2500)
                break
            except Exception:
                loc = None
    if loc is None:
        if required:
            manual(what)
        return False
    try:
        try:
            loc.check(timeout=3000)
        except Exception:
            loc.click(timeout=3000)
        ok(what)
        return True
    except Exception:
        if required:
            manual(what)
        return False


def click(page, what, css=(), texts=(), required=False):
    loc = find(page, css)
    if loc is None:
        for t in texts:
            try:
                loc = page.get_by_role("button", name=re.compile(t, re.I)).first
                loc.wait_for(state="visible", timeout=2500)
                break
            except Exception:
                loc = None
    if loc is None:
        if required:
            manual(what)
        return False
    try:
        loc.click()
        ok(what)
        return True
    except Exception:
        if required:
            manual(what)
        return False


def dump_fields(page, tag):
    """Save field metadata (ids, names, labels - NOT values) for debugging selectors."""
    try:
        fields = page.evaluate("""() => Array.from(document.querySelectorAll(
              'input,select,textarea,button,iframe,[contenteditable=true],[role=radio],[role=checkbox]'))
            .filter(e => e.type === 'file' || e.offsetParent !== null)
            .map(e => ({
              tag: e.tagName.toLowerCase(), type: e.type || '', id: e.id || '', name: e.name || '',
              label: ((e.labels && e.labels[0] && e.labels[0].innerText) || e.getAttribute('aria-label') || '').trim().slice(0, 120),
              placeholder: e.placeholder || '',
              text: (['BUTTON','A'].includes(e.tagName) ? e.innerText : '').trim().slice(0, 60),
              title: e.title || ''
            }))""")
        d = os.path.join(BOOK_DIR, "kdp-debug")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{tag}-fields.json"), "w", encoding="utf-8") as f:
            json.dump({"url": page.url.split("?")[0], "fields": fields}, f, indent=1)
        log(f"Saved field list for '{tag}' page ({len(fields)} fields) to kdp-debug/")
    except Exception as e:
        log(f"Could not save field list: {e.__class__.__name__}")


def strip_html(html):
    txt = re.sub(r"</(p|li|ul)>", "\n", html)
    txt = re.sub(r"<li>", "- ", txt)
    txt = re.sub(r"<[^>]+>", "", txt)
    return re.sub(r"\n{3,}", "\n\n", txt).strip()


# ---------------------------------------------------------------------------
def wait_for_login(page):
    log("Opening KDP. Please SIGN IN to your Amazon KDP account in the Edge window.")
    page.goto(KDP_HOME)
    deadline = time.time() + 15 * 60
    while time.time() < deadline:
        url = page.url
        if "kdp.amazon.com" in url and "signin" not in url and "/ap/" not in url \
                and ("bookshelf" in url or "title-setup" in url or "dashboard" in url):
            log("Signed in to KDP.")
            return True
        time.sleep(2)
    log("Timed out waiting for sign-in (15 min).")
    return False


def do_details(page, L):
    log("Step 1/2: Paperback details page")
    page.goto(KDP_NEW_PAPERBACK)
    page.wait_for_load_state("domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PWTimeout:
        pass
    time.sleep(2)
    dump_fields(page, "details")

    fill(page, "Book title", L["title"],
         css=["#data-print-book-title", "input[name='data[print_book][title]']", "input[id*='book-title']"],
         labels=["Book Title", "Title"])
    fill(page, "Subtitle", L.get("subtitle"),
         css=["#data-print-book-subtitle", "input[name='data[print_book][subtitle]']", "input[id*='subtitle']"],
         labels=["Subtitle"])

    first, _, last = L["author"].rpartition(" ")
    if not first:
        first, last = L["author"], ""
    fill(page, "Author first name", first,
         css=["#data-print-book-primary-author-first-name", "input[id*='primary-author-first-name']",
              "input[name*='primary_author'][name*='first_name']"],
         labels=["First name"])
    fill(page, "Author last name", last,
         css=["#data-print-book-primary-author-last-name", "input[id*='primary-author-last-name']",
              "input[name*='primary_author'][name*='last_name']"],
         labels=["Last name"])

    desc = strip_html(L["description"])
    filled = False
    for frame_sel in ("iframe.cke_wysiwyg_frame", "iframe[title*='Rich Text']", "iframe[title*='editor' i]"):
        try:
            body = page.frame_locator(frame_sel).first.locator("body")
            body.wait_for(timeout=4000)
            body.click()
            body.fill(desc)
            filled = True
            break
        except Exception:
            continue
    if not filled:
        try:
            ed = page.locator("[contenteditable=true]").first
            ed.wait_for(timeout=3000)
            ed.click()
            ed.fill(desc)
            filled = True
        except Exception:
            try:
                ta = page.locator("textarea[id*='description'], textarea[name*='description']").first
                ta.wait_for(timeout=3000)
                ta.fill(L["description"])
                filled = True
            except Exception:
                pass
    ok("Description") if filled else manual("Description (copy it from kdp-listing.json)")

    check(page, "Publishing rights: I own the copyright",
          css=["#non-public-domain", "input[name*='public_domain'][value='false']"],
          texts=["I own the copyright and I hold the necessary publishing rights"])

    kws = L.get("keywords", [])[:7]
    kw_inputs = page.locator("input[id*='keywords'], input[name*='keywords']")
    for i, kw in enumerate(kws):
        loc = find(page, css=[f"#data-print-book-keywords-{i}"], timeout=1500)
        if loc is None:
            try:
                loc = kw_inputs.nth(i)
                loc.wait_for(state="visible", timeout=1500)
            except Exception:
                loc = None
        if loc is None:
            manual(f"Keyword {i + 1}: {kw}")
            continue
        try:
            loc.fill(kw)
            ok(f"Keyword {i + 1}")
        except Exception:
            manual(f"Keyword {i + 1}: {kw}")

    check(page, "Sexually explicit content: No",
          css=["input[name*='is_adult_content'][value='false']", "#data-print-book-is-adult-content-false"],
          texts=[], required=False)

    manual("Categories: " + "; ".join(L.get("categories_suggested", [])))
    if not L.get("low_content", False):
        manual("Low-content book box: leave UNCHECKED (KDP: colouring/activity books are not low-content)")
    ra = L.get("reading_age")
    if ra:
        manual(f"Reading age: {ra['min']} to {ra['max']} (optional)")

    log("Saving as draft...")
    if not click(page, "Save as Draft", css=["#save-announce"], texts=["Save as Draft"]):
        manual("Click 'Save as Draft' at the bottom of the Details page")
    time.sleep(4)
    log("Pick the categories now, then press 'Save and Continue' - the script will carry on with the Content page.")


def do_content(page, L, book_dir):
    log("Step 2/2: waiting for the Content page (finish Details and press 'Save and Continue')...")
    try:
        page.wait_for_url(re.compile(r".*/content.*"), timeout=20 * 60000)
    except PWTimeout:
        manual("Open the Content page and upload interior.pdf and cover.pdf")
        return
    page.wait_for_load_state("domcontentloaded")
    time.sleep(4)
    dump_fields(page, "content")

    manual("ISBN: click 'Assign me a free KDP ISBN' (permanent choice, so you click it)")
    p = L["print"]
    log(f"Print options: {p['ink_and_paper']}, trim {p['trim_size']}, {p['bleed']}, {p['cover_finish']} cover")
    check(page, "Ink & paper: black & white, white paper",
          texts=["Black & white interior with white paper"], required=False)
    check(page, "Bleed: no bleed", texts=["No Bleed"], required=False)
    check(page, "Cover finish: matte", texts=["Matte"], required=False)
    manual(f"Check trim size is {p['trim_size']} (click 'Select a different size' if not)")

    interior = os.path.join(book_dir, L["files"]["interior"])
    cover = os.path.join(book_dir, L["files"]["cover"])
    files = page.locator("input[type=file]")
    try:
        page.locator("input[type=file][id*='interior' i], input[type=file][name*='interior' i]").first \
            .set_input_files(interior, timeout=8000)
        ok("Uploaded manuscript (interior.pdf)")
    except Exception:
        try:
            files.nth(0).set_input_files(interior, timeout=8000)
            ok("Uploaded manuscript (interior.pdf) [first file field]")
        except Exception:
            manual(f"Upload manuscript: {interior}")

    check(page, "Cover: upload a print-ready PDF",
          texts=["Upload a cover you already have"], required=False)
    time.sleep(2)
    try:
        page.locator("input[type=file][id*='cover' i], input[type=file][name*='cover' i]").first \
            .set_input_files(cover, timeout=8000)
        ok("Uploaded cover (cover.pdf)")
    except Exception:
        try:
            files.nth(1).set_input_files(cover, timeout=8000)
            ok("Uploaded cover (cover.pdf) [second file field]")
        except Exception:
            manual(f"Upload cover: {cover}")

    manual("AI-generated content question: answer YES for images (see kdp-listing.json note)")
    manual("Wait for processing, click 'Launch Previewer', check every page, Quality Check = 0 issues, Approve")
    manual("Rights & Pricing: select 'All territories (worldwide rights)'")
    manual(f"Pricing: list price (suggested ${L.get('price_usd_suggested')}) - optional proof copy - then YOU press Publish")
    manual("One-time account setup if not done: tax interview + bank account (or Payoneer/Wise)")


def main():
    run(sys.argv[1])


def run(book_dir, log_fn=None):
    """Run the whole upload. Returns (done, todo). Safe to call from a worker thread."""
    global BOOK_DIR, LOG_FN
    BOOK_DIR = os.path.abspath(book_dir)
    LOG_FN = log_fn
    done.clear()
    todo.clear()
    with open(os.path.join(BOOK_DIR, "kdp-listing.json"), encoding="utf-8") as f:
        L = json.load(f)
    if L.get("status") not in ("approved", "uploaded_draft"):
        log("This book has not been approved in the preview app. Stopping.")
        return done, todo

    log(f"Uploading: {L['title']} by {L['author']}")
    with sync_playwright() as pw:
        ctx = None
        for channel in ("msedge", "chrome", None):
            try:
                kwargs = dict(user_data_dir=PROFILE_DIR, headless=False, no_viewport=True,
                              args=["--start-maximized"])
                if channel:
                    kwargs["channel"] = channel
                ctx = pw.chromium.launch_persistent_context(**kwargs)
                log(f"Browser: {channel or 'chromium'}")
                break
            except Exception as e:
                log(f"Could not start {channel}: {e.__class__.__name__}")
        if ctx is None:
            log("No browser available (install Microsoft Edge or Google Chrome).")
            return done, todo
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if not wait_for_login(page):
            ctx.close()
            return done, todo
        try:
            do_details(page, L)
            do_content(page, L, BOOK_DIR)
        except Exception as e:
            log(f"Stopped early: {e}")
            manual("Finish the remaining steps in the browser")

        L["status"] = "uploaded_draft"
        L["upload_log"] = {"done": done, "todo": todo, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        with open(os.path.join(BOOK_DIR, "kdp-listing.json"), "w", encoding="utf-8") as f:
            json.dump(L, f, indent=2)

        log("=" * 50)
        log(f"Done automatically ({len(done)}):")
        for d in done:
            log("   [x] " + d)
        log(f"Please finish in the browser ({len(todo)}) - see the KDP Copy Sheet tab:")
        for t in todo:
            log("   [ ] " + t)
        log("The uploader never presses Publish - that final click is yours.")
        log("Close the browser window when you are finished.")
        log("=" * 50)
        try:
            while ctx.pages:
                time.sleep(1)
        except Exception:
            pass
        try:
            ctx.close()
        except Exception:
            pass
        log("Browser closed. Upload session finished.")
    return done, todo


if __name__ == "__main__":
    main()
