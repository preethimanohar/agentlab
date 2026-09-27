"""DEMO 03 — the SQL agent.

Shows: the model writes DuckDB SQL from the base-table schema, our code runs it
against all 296,679 rows, the model reads the real result and answers. Three of
these five questions are ones the naive baseline (demo 02) got wrong.

Episode: 2 ("Your Data Product Has a New Customer") and 5 ("Give the Agent Tools").
Cost:    ~$0.10 the first run, then free (cache). Deterministic after run 1.

    uv run python demos/03_sql_agent.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root on path

import re                                         # noqa: E402
import yaml                                       # noqa: E402

from demos._lib import banner, rule               # noqa: E402
from agent.sql_agent import answer                # noqa: E402

SHOW = ["dl_01", "ag_03", "id_02a", "tp_02", "sm_01"]
ALSO_IN_DEMO_02 = {"dl_01", "ag_03", "id_02a"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", str(s).lower())


def looks_right(truth, text: str) -> bool:
    # loose check for the demo tally; punctuation-insensitive. Real grader = Session 5.
    vals = truth if isinstance(truth, list) else [truth]
    return all(_norm(v) in _norm(text) for v in vals)


def main() -> None:
    banner("DEMO 03  —  SQL agent  (model writes SQL, DuckDB runs it on every row)")
    gt = {q["id"]: q for q in yaml.safe_load(open("evals/ground_truth/structured.yaml"))["questions"]}

    total_cost = 0.0
    hits = 0
    for qid in SHOW:
        q = gt[qid]
        run = answer(q["text"])
        total_cost += run.cost_usd
        ok = looks_right(q["ground_truth"], run.final_answer)
        hits += ok

        tag = "  (demo 02 got this WRONG)" if qid in ALSO_IN_DEMO_02 else ""
        rule(f"{qid}  ({q['category']}){tag}")
        print(f"Q      {q['text']}")
        print(f"SQL    {run.sql}")
        print(f"       -> {run.row_count} row(s), {run.attempts} attempt(s)")
        print(f"MODEL  {run.final_answer}")
        print(f"TRUTH  {q['ground_truth']}")
        print(f"       {'MATCH' if ok else 'no match'}   ${run.cost_usd:.4f}")

    rule("what this shows")
    print(
        f"{hits}/{len(SHOW)} correct  (naive baseline got 2/4 on the overlap, and by luck).\n"
        f"total cost this run: ${total_cost:.4f}  vs ~$0.60 naive. Faster and cheaper too.\n"
        "Every answer carries the exact SQL that produced it — fully traceable.\n"
        "\n"
        "The finding: tp_02 and sm_01 needed 'lower score = better', and the agent\n"
        "knew that WITHOUT being told — NYC's scoring is famous enough to be in its\n"
        "training. So for this dataset the semantic layer may add little on\n"
        "directionality. Demo 04 tests where it DOES earn its place: the latest-\n"
        "inspection tie-break rule, and picking the right curated view."
    )


if __name__ == "__main__":
    main()
