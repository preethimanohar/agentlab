# demos/

One standalone, narrated, **filmable** script per build step.

Rules:

- **Runs in isolation.** `uv run python demos/NN_name.py` — or `uv run python tasks.py demo NN`.
  No demo depends on another demo's runtime state. They share only the stable
  artifacts on disk (`data/raw/*.parquet`, `data/generated/canonical.duckdb`).
- **Deterministic.** Every model call goes through `.cache/`. After the first
  run the output is byte-identical forever — re-film any time, the numbers on
  screen don't move. (Demo 01 deliberately spends ~$0.001 per run to show the
  live→cache transition; all others are free after the first run.)
- **Narrated.** Each prints a walkthrough with section banners and a closing
  "what this shows".
- **Self-describing.** The docstring at the top states what it demonstrates,
  which episode it feeds, and its cost/determinism.

Library code lives in `agent/`, `pipeline/`, `semantic/`, `evals/`. Demos
**import and narrate only** — reusable logic never lives in a demo file, so the
big `evals/run_all` runner (later) and the demos stay independent.

| demo | shows | episode |
|---|---|---|
| `01_model_connection` | the AI pipe + the record/replay cache | setup |
| `02_naive_baseline` | AI + a raw data sample fails basic questions | 1 |
| `03_sql_agent` | AI writes SQL, DuckDB runs it, answers get correct | 2, 5 |
| `04_semantic_layer` | feeding definitions flips the "which improved" answers | 2 |
| `05_scorecard` | mode × category accuracy table | 2 |
