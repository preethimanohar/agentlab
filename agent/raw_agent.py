"""The naive baseline agent ('raw' mode) — library code.

`answer(question)` hands the model a plain-text SAMPLE of the raw data plus the
question: no tools, no clean tables, no semantic definitions. This is what "just
paste my data into the chatbot" looks like, and it sets the floor the later
agents must beat.

Filmable walkthrough: demos/02_naive_baseline.py
Interactive poke:     uv run python tasks.py raw "how many restaurants are there?"
"""

from __future__ import annotations

import duckdb

from agent.client import Reply, ask
from pipeline.snapshot import latest_stem

SAMPLE_ROWS = 300
SAMPLE_SEED = 42

SYSTEM = (
    "You answer questions about NYC restaurant inspection data. You are given a "
    "SAMPLE of the raw data as CSV — it is not the whole dataset. Answer only "
    "from what you can see in the sample. If the sample cannot answer the "
    "question, say so. Give a short, direct answer first, then one line of "
    "reasoning."
)


def raw_sample_csv(n: int = SAMPLE_ROWS) -> str:
    """A deterministic random sample of the frozen raw snapshot, as CSV text."""
    con = duckdb.connect()
    con.execute(
        f"CREATE VIEW raw AS SELECT * FROM 'data/raw/{latest_stem()}.parquet'"
    )
    rel = con.sql(
        f"""
        SELECT camis, dba, boro, inspection_date, inspection_type,
               score, grade, critical_flag, violation_code, violation_description
        FROM raw USING SAMPLE reservoir({int(n)} ROWS) REPEATABLE ({SAMPLE_SEED})
        """
    )
    cols = rel.columns
    lines = [",".join(cols)]
    for row in rel.fetchall():
        lines.append(",".join("" if v is None else str(v).replace(",", " ") for v in row))
    return "\n".join(lines)


def build_prompt(question: str) -> str:
    return (
        f"Here is a sample of {SAMPLE_ROWS} rows of raw NYC restaurant inspection "
        f"data (CSV, one row per cited violation):\n\n"
        f"{raw_sample_csv()}\n\n"
        f"Question: {question}"
    )


def answer(question: str) -> Reply:
    return ask(build_prompt(question), system=SYSTEM)


if __name__ == "__main__":               # interactive poke only — the demo is in demos/
    import sys

    args = sys.argv[1:]
    show_only = "--show" in args
    args = [a for a in args if a != "--show"]
    if not args:
        raise SystemExit('usage: uv run python tasks.py raw [--show] "your question"')
    question = " ".join(args)

    if show_only:                         # print the exact prompt, don't call the model
        print("=== SYSTEM MESSAGE ===\n" + SYSTEM)
        print("\n=== USER MESSAGE ===\n" + build_prompt(question))
        raise SystemExit

    r = answer(question)
    print(r.text)
    print(f"\n[{'cache' if r.cached else 'live'}] in={r.input_tokens} "
          f"out={r.output_tokens} tok  ${r.cost_usd:.4f}")
