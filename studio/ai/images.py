"""
Image AI: one picture per subject from your chosen provider, cleaned for print.

  cloudflare   FREE  Workers AI, FLUX.1-schnell (Apache-2.0, commercial use allowed)
  huggingface  free credits, FLUX.1-schnell
  openai       paid  (model e.g. gpt-image-1)
  stability    paid

Page pictures become pure black & white line art at 2400 px (~640 DPI on the page);
cover pictures stay in colour. Keys come from config.load_settings() (stored on this PC only).
"""
import base64
import io
import os

import requests
from PIL import Image, ImageFilter, ImageOps

from ..config import DEFAULT_PROMPT_STYLE, load_settings

PRINT_PX = 2400          # cleaned line-art size; ~640 DPI at the 3.75 in picture area


# ---------------------------------------------------------------------------
class ImageAPIError(Exception):
    pass


class QuotaError(ImageAPIError):
    """The provider's free daily allowance is used up - stop instead of failing every remaining picture."""


def _err(r):
    try:
        j = r.json()
        msg = j.get("error", {}).get("message") if isinstance(j.get("error"), dict) else j.get("errors") or j
    except Exception:
        msg = r.text[:300]
    return ImageAPIError(f"{r.status_code}: {msg}")


def generate_openai(prompt, s):
    key = s.get("openai_key", "").strip()
    if not key:
        raise ImageAPIError("No OpenAI API key saved (AI Images tab > Settings).")
    model = s.get("openai_model") or "gpt-image-1"
    body = {"model": model, "prompt": prompt, "size": "1024x1024", "n": 1}
    if model.startswith("dall-e"):
        body["response_format"] = "b64_json"
    else:
        body["quality"] = s.get("openai_quality", "medium")
    r = requests.post("https://api.openai.com/v1/images/generations",
                      headers={"Authorization": f"Bearer {key}"}, json=body, timeout=180)
    if r.status_code != 200:
        raise _err(r)
    d = r.json()["data"][0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    return requests.get(d["url"], timeout=60).content


def generate_stability(prompt, s):
    key = s.get("stability_key", "").strip()
    if not key:
        raise ImageAPIError("No Stability AI API key saved (AI Images tab > Settings).")
    r = requests.post("https://api.stability.ai/v2beta/stable-image/generate/core",
                      headers={"Authorization": f"Bearer {key}", "Accept": "image/*"},
                      files={"none": ""},
                      data={"prompt": prompt, "aspect_ratio": "1:1", "output_format": "png",
                            "style_preset": "line-art",
                            "negative_prompt": "shading, grey, gradient, colour, text, letters, watermark, signature"},
                      timeout=180)
    if r.status_code != 200:
        raise _err(r)
    return r.content


def generate_cloudflare(prompt, s):
    """FREE: Cloudflare Workers AI daily allowance. Model FLUX.1-schnell (Apache-2.0, commercial use OK)."""
    acc, tok = s.get("cf_account_id", "").strip(), s.get("cf_token", "").strip()
    if not acc or not tok:
        raise ImageAPIError("Cloudflare Account ID and API token are needed (AI Images tab > Settings).")
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/black-forest-labs/flux-1-schnell",
                      headers={"Authorization": f"Bearer {tok}"}, json={"prompt": prompt, "steps": 8}, timeout=180)
    if r.status_code != 200:
        try:
            errs = r.json().get("errors") or r.text[:300]
        except Exception:
            errs = r.text[:300]
        if r.status_code == 429 or "4006" in str(errs) or "daily free allocation" in str(errs):
            raise QuotaError("Cloudflare's free daily allowance is used up. It resets every day at 00:00 UTC "
                             "(5:30 AM India time). Pictures already made are kept - continue after the reset.")
        raise ImageAPIError(f"{r.status_code}: {errs}")
    return base64.b64decode(r.json()["result"]["image"])


def generate_huggingface(prompt, s):
    """FREE tier credits: Hugging Face Inference. Model FLUX.1-schnell (Apache-2.0)."""
    tok = s.get("hf_token", "").strip()
    if not tok:
        raise ImageAPIError("Hugging Face access token is needed (AI Images tab > Settings).")
    r = requests.post("https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
                      headers={"Authorization": f"Bearer {tok}", "Accept": "image/png"},
                      json={"inputs": prompt, "parameters": {"num_inference_steps": 4, "width": 1024, "height": 1024}},
                      timeout=180)
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
        raise _err(r)
    return r.content


PROVIDERS = {"cloudflare": generate_cloudflare, "huggingface": generate_huggingface,
             "openai": generate_openai, "stability": generate_stability}
PROVIDER_LABELS = {"cloudflare": "Cloudflare Workers AI – FLUX (free)",
                   "huggingface": "Hugging Face – FLUX (free credits)",
                   "openai": "OpenAI images (paid)", "stability": "Stability AI (paid)"}


# ---------------------------------------------------------------------------
def clean_line_art(raw_bytes, size=PRINT_PX):
    """AI picture -> pure black & white line art, enlarged, cropped and centred on a square."""
    im = Image.open(io.BytesIO(raw_bytes)).convert("L")
    im = ImageOps.autocontrast(im, cutoff=1)
    k = size / max(im.size)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    im = im.filter(ImageFilter.GaussianBlur(1.0))
    bw = im.point(lambda v: 0 if v < 145 else 255)
    bw = bw.filter(ImageFilter.MedianFilter(5))            # remove specks
    box = ImageOps.invert(bw).getbbox()
    if box:
        bw = bw.crop(box)
    side = int(max(bw.size) * 1.06)
    out = Image.new("L", (side, side), 255)
    out.paste(bw, ((side - bw.width) // 2, (side - bw.height) // 2))
    return out.resize((size, size), Image.LANCZOS).point(lambda v: 0 if v < 128 else 255)


COLOR_STYLE = ("A cute, colourful cartoon illustration of one {word} for a children's book cover. "
               "Bright flat colours, thick dark outlines, plain white background, centred, no text, no letters.")


def colour_square(raw_bytes, size=1600):
    im = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    side = max(im.size)
    out = Image.new("RGB", (side, side), (255, 255, 255))
    out.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    return out.resize((size, size), Image.LANCZOS)


# Plainer wording used when a provider's safety filter wrongly flags a prompt
# (Cloudflare blocks e.g. "nebula" or "black hole" next to "for toddlers").
SAFE_STYLE = ("A simple black and white colouring page showing one {word}. Thick, clean, smooth black outlines. "
              "No shading, no grey, no colour, no text, no letters. Plain white background. "
              "One single centred subject with large open areas to colour. Cartoon style.")
SAFE_COLOR_STYLE = ("A colourful cartoon illustration of one {word}. Bright flat colours, thick dark outlines, "
                    "plain white background, centred, no text, no letters.")


def _blocked(err):
    t = str(err).lower()
    return any(k in t for k in ("nsfw", "safety", "moderation", "content policy", "content_policy"))


def _plain_description(word, s):
    """Ask the text AI to describe the subject in everyday picture words (e.g. nebula -> swirly cloud with stars)."""
    from . import text
    r = text.ask_json(
        "You describe a simple, friendly cartoon drawing for a children's colouring book in plain everyday words: "
        "shapes, objects, plants, animals, weather, sky. Never mention bodies, skin, clothing, darkness, danger "
        "or violence. Do not repeat the subject word.",
        f'Subject: "{word}". Describe the drawing in at most 12 words.',
        text.obj({"description": text.STR}), s)
    return r["description"].strip().rstrip(".")


def generate_image(out_path, word, settings=None, color=False):
    """Any subject -> print-ready picture. color=False: B&W line art for pages; True: cover art.
    If the provider's safety filter wrongly blocks the subject, retries with plainer wording and then
    with a plain description of the subject written by the text AI."""
    s = settings or load_settings()
    fn = PROVIDERS.get(s.get("provider", "cloudflare"))
    if fn is None:
        raise ImageAPIError(f"Unknown provider {s.get('provider')}")
    styles = [COLOR_STYLE, SAFE_COLOR_STYLE] if color else [s.get("prompt_style", DEFAULT_PROMPT_STYLE), SAFE_STYLE]
    subjects = [word.lower()]
    raw, tried_description = None, False
    while raw is None:
        for subject in subjects:
            for style in styles:
                try:
                    raw = fn(style.replace("{word}", subject), s)
                    break
                except Exception as e:
                    if not _blocked(e):
                        raise
            if raw is not None:
                break
        if raw is None:
            if tried_description:
                raise ImageAPIError(
                    f"The image AI's safety filter blocked the picture “{word}” (a false alarm on an ordinary word). "
                    "Press Regenerate for it in the AI Images tab, or change that subject.")
            tried_description = True
            try:
                subjects = [_plain_description(word, s), _plain_description(word, s)]
            except Exception:
                subjects = []
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    (colour_square(raw) if color else clean_line_art(raw)).save(out_path, optimize=True)
    return out_path
