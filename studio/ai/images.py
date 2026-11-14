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


def generate_image(out_path, word, settings=None, color=False):
    """Any subject -> print-ready picture. color=False: B&W line art for pages; True: cover art."""
    s = settings or load_settings()
    fn = PROVIDERS.get(s.get("provider", "cloudflare"))
    if fn is None:
        raise ImageAPIError(f"Unknown provider {s.get('provider')}")
    style = COLOR_STYLE if color else s.get("prompt_style", DEFAULT_PROMPT_STYLE)
    raw = fn(style.replace("{word}", word.lower()), s)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    (colour_square(raw) if color else clean_line_art(raw)).save(out_path, optimize=True)
    return out_path
