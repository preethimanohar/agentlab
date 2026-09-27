"""The one file that talks to the AI model.

Everything else in the project calls `ask(...)` from here. It does three things:

  1. sends your text to Claude and gets text back
  2. records every reply in .cache/ so asking the same thing again is instant
     and free (this is the "record/replay" that makes experiments repeatable)
  3. reports how many tokens it used and how long it took

This is library code — no demo here. See demos/01_model_connection.py.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()  # reads .env so ANTHROPIC_API_KEY is available

MODEL = "claude-sonnet-5"     # the fixed model for the whole project
MAX_TOKENS = 8192
CACHE_DIR = Path(".cache")


@dataclass
class Reply:
    text: str                # what the model said
    input_tokens: int        # size of what we sent (prompt)
    output_tokens: int       # size of what it wrote back
    latency_s: float         # wall-clock seconds for the API call (0 if cached)
    cached: bool             # True = served from .cache, no API call, no cost
    model: str = MODEL

    @property
    def cost_usd(self) -> float:
        # claude-sonnet-5 list price: $3 / 1M input, $15 / 1M output.
        # A cached reply cost nothing this time (it was paid for on the first call).
        if self.cached:
            return 0.0
        return self.input_tokens / 1e6 * 3 + self.output_tokens / 1e6 * 15


def _cache_key(system: str | None, prompt: str) -> str:
    blob = json.dumps({"model": MODEL, "max_tokens": MAX_TOKENS,
                       "system": system, "prompt": prompt}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:20]


def ask(prompt: str, system: str | None = None, *, refresh: bool = False) -> Reply:
    """Ask the model one question. Returns a Reply. Uses the cache unless refresh=True."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{_cache_key(system, prompt)}.json"

    if cache_file.exists() and not refresh:
        data = json.loads(cache_file.read_text())
        return Reply(**{**data["reply"], "cached": True, "latency_s": 0.0})

    client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY from the environment
    started = time.monotonic()
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system or anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError:
        raise SystemExit("Auth failed — check ANTHROPIC_API_KEY in .env")
    except anthropic.PermissionDeniedError:
        raise SystemExit("Key rejected — is there billing credit on the account?")
    latency = time.monotonic() - started

    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    reply = Reply(
        text=text,
        input_tokens=msg.usage.input_tokens,
        output_tokens=msg.usage.output_tokens,
        latency_s=round(latency, 2),
        cached=False,
    )
    cache_file.write_text(json.dumps(
        {"prompt": prompt, "system": system, "reply": asdict(reply)}, indent=2))
    return reply
