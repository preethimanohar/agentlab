"""Ask the model anything from the command line, to get a feel for it.

    uv run python tasks.py ask "how many boroughs does NYC have?"
    uv run python tasks.py ask --fresh "..."   # ignore the cache, force a new call
"""

from __future__ import annotations

import argparse

from agent.client import ask


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="+")
    ap.add_argument("--fresh", action="store_true", help="bypass the cache")
    args = ap.parse_args()

    r = ask(" ".join(args.question), refresh=args.fresh)
    print(r.text)
    print(f"\n[{'cache' if r.cached else 'live'}]  in={r.input_tokens} out={r.output_tokens} "
          f"tok  {r.latency_s}s  ${r.cost_usd:.4f}")


if __name__ == "__main__":
    main()
