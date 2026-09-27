"""Dispatch to a numbered demo.

    uv run python tasks.py demo          # list demos
    uv run python tasks.py demo 02       # run demos/02_*.py
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

DEMOS = sorted(Path("demos").glob("[0-9][0-9]_*.py"))


def main() -> None:
    if len(sys.argv) < 2:
        print("demos:")
        for d in DEMOS:
            print(f"  {d.stem[:2]}   {d.stem[3:]}")
        print('\nrun one:  uv run python tasks.py demo <NN>')
        return
    want = sys.argv[1].zfill(2)
    match = [d for d in DEMOS if d.stem.startswith(want)]
    if not match:
        raise SystemExit(f"no demo {want} (have: {[d.stem[:2] for d in DEMOS]})")
    sys.argv = [str(match[0])]
    runpy.run_path(str(match[0]), run_name="__main__")


if __name__ == "__main__":
    main()
