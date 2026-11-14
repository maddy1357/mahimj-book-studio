"""
mahimj-books :: next-book ideas

generate(n)            -> n new ideas, each checked against your own catalogue
change(idea)           -> replace one idea with a different one
create_book(idea)      -> ready-to-publish/<slug>/book-spec.json (then build_theme_book builds it)

The duplicate check compares against books in ready-to-publish/ and earlier ideas. Market notes are the
AI's general knowledge - not live Amazon data (the app does not scrape Amazon).
"""
import difflib
import json
import os
import re
import time

import build_alphabet_book as B
import llm

HERE = os.path.dirname(os.path.abspath(__file__))
READY = os.path.abspath(os.path.join(HERE, "..", "ready-to-publish"))
IDEAS_FILE = os.path.join(READY, "_ideas.json")

IDEA = llm.obj({
    "title": llm.STR, "subtitle": llm.STR, "theme": llm.STR, "audience": llm.STR,
    "age_min": llm.INT, "age_max": llm.INT,
    "page_subjects": llm.STRS,
    "why_it_sells": llm.STR, "differentiation": llm.STR, "market_note": llm.STR,
    "description_html": llm.STR, "keywords": llm.STRS, "categories": llm.STRS,
    "features": llm.STRS, "back_heading": llm.STR, "back_text": llm.STR,
    "marketing": llm.STRS,
})
IDEAS = llm.obj({"ideas": {"type": "array", "items": IDEA}})

SYSTEM = (f"You plan the next Amazon KDP paperback for the small children's publisher {B.BRAND} (author {B.AUTHOR}). "
          "The publisher makes 8.5 x 11 in single-sided colouring books with big, simple AI line-art pictures "
          "(one subject per page, the subject's name printed under it). Suggest books that are realistic to make "
          "this way and that sell: evergreen or seasonal themes, a clear audience, and a fresh angle. "
          "page_subjects: 24-30 short concrete nouns that each make one clear picture (no text, no logos, no "
          "copyrighted characters or brands). Title and subtitle must be what goes on the cover. description_html "
          "uses <p>, <b>, <ul><li>, under 1500 characters. Exactly 7 keywords under 50 characters, no brand or author "
          "names. 3 Amazon category paths. 5 back-cover feature bullets. 5 concrete marketing actions to increase "
          "buyers that follow Amazon policy (never paid, swapped or fake reviews). market_note: honest note on how "
          "crowded the niche probably is (general knowledge, not live data).")


def catalogue():
    """Titles/themes of books already made plus earlier ideas - used to avoid duplicates."""
    items = []
    if os.path.isdir(READY):
        for d in os.listdir(READY):
            lp = os.path.join(READY, d, "kdp-listing.json")
            if os.path.exists(lp):
                with open(lp, encoding="utf-8") as f:
                    L = json.load(f)
                items.append({"title": L.get("title", ""), "theme": L.get("theme", L.get("subtitle", "")),
                              "source": "your book"})
    for i in load_ideas():
        items.append({"title": i["title"], "theme": i.get("theme", ""), "source": "earlier idea"})
    return items


def similarity(a, b):
    na, nb = (re.sub(r"[^a-z ]", "", x.lower()) for x in (a, b))
    return difflib.SequenceMatcher(None, na, nb).ratio()


def duplicate_of(idea, items):
    best, who = 0.0, None
    for it in items:
        s = max(similarity(idea["title"], it["title"]), similarity(idea.get("theme", ""), it.get("theme", "")))
        if s > best:
            best, who = s, it
    return (who, best) if best >= 0.72 else (None, best)


def load_ideas():
    try:
        with open(IDEAS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_ideas(ideas):
    os.makedirs(READY, exist_ok=True)
    with open(IDEAS_FILE, "w", encoding="utf-8") as f:
        json.dump(ideas, f, indent=2)


def _avoid_text(items):
    return "\n".join(f"- {i['title']} ({i['theme']}) [{i['source']}]" for i in items) or "- (none yet)"


def _stamp(idea, items):
    dup, score = duplicate_of(idea, items)
    idea["duplicate_of"] = dup["title"] if dup else ""
    idea["similarity"] = round(score, 2)
    idea["status"] = "new"
    idea["created_at"] = time.strftime("%Y-%m-%d %H:%M")
    idea["keywords"] = [k[:50] for k in idea.get("keywords", [])][:7]
    return idea


def generate(n=5, settings=None, max_rounds=2):
    """Ask for n ideas; any that duplicate the catalogue are replaced automatically."""
    items = catalogue()
    prompt = (f"Suggest {n} different next books. Avoid anything too close to these existing books and earlier "
              f"ideas:\n{_avoid_text(items)}")
    ideas = [_stamp(i, items) for i in llm.ask_json(SYSTEM, prompt, IDEAS, settings)["ideas"][:n]]
    for _ in range(max_rounds):
        dups = [i for i in ideas if i["duplicate_of"]]
        if not dups:
            break
        for d in dups:
            ideas[ideas.index(d)] = change(d, settings, items=items, save=False)
    save_ideas(load_ideas() + ideas)
    return ideas


def change(idea, settings=None, items=None, save=True, reason=""):
    """Replace an idea (duplicate or not wanted) with a clearly different one."""
    items = items if items is not None else catalogue()
    prompt = (f"Replace this idea with ONE clearly different book idea{(' because: ' + reason) if reason else ''}.\n"
              f"Idea to replace: {idea['title']} - {idea.get('theme', '')}\n"
              f"Also avoid:\n{_avoid_text(items)}\nReturn a list with exactly one idea.")
    new = _stamp(llm.ask_json(SYSTEM, prompt, IDEAS, settings)["ideas"][0], items + [
        {"title": idea["title"], "theme": idea.get("theme", ""), "source": "replaced idea"}])
    if save:
        all_ideas = load_ideas()
        for k, i in enumerate(all_ideas):
            if i.get("title") == idea.get("title") and i.get("created_at") == idea.get("created_at"):
                i["status"] = "replaced"
        save_ideas(all_ideas + [new])
    return new


def create_book(idea):
    """Approved idea -> new book folder with book-spec.json (pictures + PDFs are built next)."""
    slug = re.sub(r"[^a-z0-9]+", "-", idea["title"].lower()).strip("-")[:50] or "book"
    book_dir = os.path.join(READY, slug)
    n = 2
    while os.path.exists(book_dir):
        book_dir = os.path.join(READY, f"{slug}-{n}")
        n += 1
    os.makedirs(book_dir)
    spec = {k: idea[k] for k in ("title", "subtitle", "theme", "audience", "age_min", "age_max", "page_subjects",
                                 "description_html", "keywords", "categories", "features", "back_heading",
                                 "back_text", "marketing")}
    spec["author"] = B.AUTHOR
    spec["idea"] = {k: idea.get(k) for k in ("why_it_sells", "differentiation", "market_note")}
    with open(os.path.join(book_dir, "book-spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    with open(os.path.join(book_dir, "book-config.json"), "w", encoding="utf-8") as f:
        json.dump({"builder": "theme", "art_source": "ai", "cover_source": "generated"}, f, indent=2)
    all_ideas = load_ideas()
    for i in all_ideas:
        if i.get("title") == idea.get("title") and i.get("created_at") == idea.get("created_at"):
            i["status"] = "approved"
            i["book_dir"] = os.path.basename(book_dir)
    save_ideas(all_ideas)
    return book_dir


GROWTH_PLAYBOOK = [
    "Price at $9.99 (60% royalty tier) - the app sets every store above its 60% threshold.",
    "Use all 7 keyword boxes with phrases buyers type (age + theme + 'colouring book').",
    "Pick 3 specific categories - small categories are easier to rank in.",
    "Add A+ Content (free, in KDP Marketing): sample pages and a 'more books' strip.",
    "Run Amazon Sponsored Products ads with a small daily budget; keep keywords that sell.",
    "Set up Author Central and link every book to your author page.",
    "Build a series (same look, numbered) so buyers of one book find the next.",
    "Launch seasonal books 6-8 weeks before the season (Halloween, Christmas, Easter, back to school).",
    "Share flip-throughs and free sample pages on Pinterest/Instagram/YouTube Shorts.",
    "Ask happy buyers to leave an honest review (a note on the last page is fine) - never pay for or swap reviews.",
]
