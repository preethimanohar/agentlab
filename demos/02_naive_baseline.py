"""DEMO 02 — the naive baseline: AI + a raw data sample.

Shows: hand the model 300 rows of the raw messy data as text, ask benchmark
questions, compare to the frozen ground truth. Specific lookups miss (the row
isn't in the sample); counts are wildly wrong (it counts its slice); the right
answers are right by luck or prior knowledge. This is the floor.

Episode: 1 ("A Table Is Not a Data Product").
Cost:    ~$0.50 the first run, then free (cache). Deterministic after run 1.

    uv run python demos/02_naive_baseline.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root on path

import yaml                                            # noqa: E402

from demos._lib import banner, rule                    # noqa: E402
from agent.raw_agent import SAMPLE_ROWS, answer        # noqa: E402

SHOW = ["dl_01", "ag_03", "id_02a", "sm_02"]   # one per failure/luck mode


def main() -> None:
    banner(f"DEMO 02  —  naive baseline  (model sees {SAMPLE_ROWS} raw rows, no tools)")
    gt = {q["id"]: q for q in yaml.safe_load(open("evals/ground_truth/structured.yaml"))["questions"]}

    hits = 0
    for qid in SHOW:
        q = gt[qid]
        r = answer(q["text"])
        # loose check just for the demo tally; the real grader is in Session 5
        match = bool(re.search(rf"\b{re.escape(str(q['ground_truth']))}\b", r.text, re.I))
        hits += match
        rule(f"{qid}  ({q['category']})")
        print(f"Q      {q['text']}")
        print(f"MODEL  {r.text}")
        print(f"TRUTH  {q['ground_truth']}")
        print(f"       {'looks right' if match else 'WRONG'}   "
              f"[{'cache' if r.cached else 'live'}] "
              f"in={r.input_tokens} out={r.output_tokens} tok  ${r.cost_usd:.4f}")

    rule("what this shows")
    print(
        f"{hits}/{len(SHOW)} landed — and the misses are structural:\n"
        "  dl_01  : the row is not in a 300-of-296,679 sample -> can't answer\n"
        "  id_02a : counted the ~5 Dunkins it saw; real answer is 450\n"
        "  ag_03  : correct, but only because the sample's top code matched\n"
        "  sm_02  : correct from general knowledge, not from the data\n"
        "Next: demo 03 lets the model query all the rows precisely."
    )


if __name__ == "__main__":
    main()
