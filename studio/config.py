"""Paths, brand details and saved settings shared by the whole app."""
import json
import os

# ---- paths -----------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND_DIR = os.path.join(ROOT, "assets", "brand")          # logo.png, name.png, app.ico
READY = os.path.join(ROOT, "ready-to-publish")             # one folder per book (generated)
BROWSER_PROFILE = os.path.join(ROOT, ".kdp-browser-profile")  # KDP login session - private
SETTINGS_PATH = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "mahimj-books", "settings.json")

# ---- brand -----------------------------------------------------------------
BRAND = "mahimj-books"            # imprint + copyright holder
BRAND_TAGLINE = "Books"           # printed under the mahiMJ wordmark
AUTHOR = "Madhavan J"
YEAR = 2026
COPYRIGHT_LINE = f"© {YEAR} {BRAND}. All rights reserved."

# ---- settings (AI keys stay on this PC, never in the project) --------------
DEFAULT_PROMPT_STYLE = (
    "A simple black and white colouring page for toddlers showing one cute {word}. "
    "Thick, clean, smooth black outlines. No shading, no grey, no colour, no text, no letters. "
    "Plain white background. One single centred subject with large open areas to colour. "
    "Cute cartoon style.")

DEFAULT_SETTINGS = {
    "provider": "cloudflare",          # image AI: cloudflare | huggingface | openai | stability
    "llm_provider": "cloudflare",      # text AI: cloudflare (free) | claude (best)
    "cf_account_id": "",
    "cf_token": "",
    "hf_token": "",
    "anthropic_key": "",
    "claude_model": "claude-opus-5-5",
    "openai_key": "",
    "openai_model": "gpt-image-1",
    "openai_quality": "medium",
    "stability_key": "",
    "prompt_style": DEFAULT_PROMPT_STYLE,
}


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_settings():
    return {**DEFAULT_SETTINGS, **read_json(SETTINGS_PATH, {})}


def save_settings(settings):
    write_json(SETTINGS_PATH, settings)


# ---- per-book files ----------------------------------------------------------
def book_config(book_dir):
    """book-config.json: builder type, picture source, cover source, rights confirmation."""
    return read_json(os.path.join(book_dir, "book-config.json"),
                      {"art_source": "vector", "cover_source": "generated"})


def save_book_config(book_dir, cfg):
    write_json(os.path.join(book_dir, "book-config.json"), cfg)


def load_listing(book_dir):
    return read_json(os.path.join(book_dir, "kdp-listing.json"), {})


def save_listing(book_dir, listing):
    write_json(os.path.join(book_dir, "kdp-listing.json"), listing)


def art_dir(book_dir):
    return os.path.join(book_dir, "ai-images")
