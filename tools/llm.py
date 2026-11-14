"""
mahimj-books :: text AI for listings, book analysis and new-book ideas.

Providers (chosen in Book Studio > AI Images > Text AI):
  cloudflare  FREE - Workers AI Llama 3.3 70B, uses the same Account ID + token as the images
  claude      BEST - Anthropic Claude Opus 5.5 (your Anthropic API key), structured JSON output

ask_json(system, prompt, schema) always returns a dict that matches `schema`.
"""
import base64
import json
import re

import requests

import ai_images

CLAUDE_MODEL = "claude-opus-5-5"
CF_TEXT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"


class LLMError(Exception):
    pass


def _extract_json(text):
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise LLMError("The AI did not return JSON.")
    return json.loads(m.group(0))


def _claude(system, prompt, schema, s, images):
    try:
        import anthropic
    except ImportError as e:
        raise LLMError("Install the Anthropic SDK: pip install anthropic") from e
    key = s.get("anthropic_key", "").strip()
    client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
    content = []
    for png in images or []:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                    "data": base64.standard_b64encode(png).decode()}})
    content.append({"type": "text", "text": prompt})
    try:
        resp = client.beta.messages.create(
            model=s.get("claude_model") or CLAUDE_MODEL,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise LLMError("Claude: the API key was rejected. Check it in AI Images > Text AI.") from e
    except anthropic.RateLimitError as e:
        raise LLMError("Claude: rate limited - wait a minute and try again.") from e
    except anthropic.APIStatusError as e:
        raise LLMError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise LLMError("Claude: network error - check the internet connection.") from e
    if resp.stop_reason == "refusal":
        raise LLMError("Claude declined this request.")
    if resp.stop_reason == "max_tokens":
        raise LLMError("Claude's answer was cut off - try again.")
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(text)


def _cloudflare(system, prompt, schema, s):
    acc, tok = s.get("cf_account_id", "").strip(), s.get("cf_token", "").strip()
    if not acc or not tok:
        raise LLMError("Cloudflare Account ID and API token are needed (AI Images tab).")
    sys_msg = (system + "\n\nReply with ONLY one JSON object that matches this JSON Schema, no other text:\n"
               + json.dumps(schema))
    body = {"messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
            "max_tokens": 4096, "response_format": {"type": "json_schema", "json_schema": schema}}
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{CF_TEXT_MODEL}",
                      headers={"Authorization": f"Bearer {tok}"}, json=body, timeout=180)
    if r.status_code != 200:
        try:
            errs = r.json().get("errors") or r.text[:300]
        except Exception:
            errs = r.text[:300]
        raise LLMError(f"Cloudflare {r.status_code}: {errs}")
    out = r.json().get("result", {}).get("response")
    if isinstance(out, dict):
        return out
    return _extract_json(out or "")


def ask_json(system, prompt, schema, settings=None, images=None):
    s = settings or ai_images.load_settings()
    if s.get("llm_provider", "cloudflare") == "claude":
        return _claude(system, prompt, schema, s, images)
    return _cloudflare(system, prompt, schema, s)


def obj(props, required=None):
    """Small helper to build strict JSON schemas."""
    return {"type": "object", "properties": props, "required": required or list(props),
            "additionalProperties": False}


STR = {"type": "string"}
INT = {"type": "integer"}
BOOL = {"type": "boolean"}
STRS = {"type": "array", "items": {"type": "string"}}
