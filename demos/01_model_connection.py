"""DEMO 01 — the AI pipe and the record/replay cache.

Shows: agent/client.py sends text to claude-sonnet-5 and gets text back; the
second identical call is served from .cache/ — instant, free, byte-identical.
That repeatability is what makes every later result filmable.

Episode: setup / behind-the-scenes.
Cost:    ~$0.001 per run (deliberate — call 1 forces a live call to show the
         live -> cache transition). Call 2 onward is free.

    uv run python demos/01_model_connection.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root on path

from demos._lib import banner, rule     # noqa: E402
from agent.client import MODEL, ask     # noqa: E402

Q = "In one sentence, what is a NYC restaurant health inspection score?"


def main() -> None:
    banner(f"DEMO 01  —  talking to {MODEL}")
    print(f"\nprompt:\n  {Q}")

    rule("call 1  (forced live)")
    r1 = ask(Q, refresh=True)
    print(r1.text)
    print(f"\n  cached   = {r1.cached}")
    print(f"  input    = {r1.input_tokens} tokens   (the prompt)")
    print(f"  output   = {r1.output_tokens} tokens   (the answer)")
    print(f"  latency  = {r1.latency_s} s")
    print(f"  cost     = ${r1.cost_usd:.4f}")

    rule("call 2  (same question, no refresh)")
    r2 = ask(Q)
    print(r2.text)
    print(f"\n  cached   = {r2.cached}")
    print(f"  latency  = {r2.latency_s} s")
    print(f"  cost     = ${r2.cost_usd:.4f}")

    rule("what this shows")
    print(
        "Same question -> identical answer, 0 s, $0.\n"
        "Call 1 recorded the reply to .cache/<hash>.json; call 2 replayed it.\n"
        "Re-run or re-film this later and the numbers do not move.\n"
        "Every agent in this project calls ask() and nothing else."
    )


if __name__ == "__main__":
    main()
