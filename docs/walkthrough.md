# Walkthrough — what exists so far

## Open it in VSCode

1. **File > Open Folder** -> `D:\preethi\git\agentlab`
2. Install the **Python** extension (Microsoft) if you don't have it.
3. `Ctrl+Shift+P` -> **Python: Select Interpreter** -> pick
   `.\.venv\Scripts\python.exe`. That is the environment `uv` created; it has
   duckdb, polars, etc. installed. (Your separately-installed system Python is
   not used by this project — `uv` manages its own.)
4. Open a terminal in VSCode (`Ctrl+` `` ` ``). Every command below is run there.

## The one command that shows everything

```
uv run python tasks.py peek
```

It prints a narrated tour: the frozen snapshot, raw data, each canonical table
with its schema, the current-state marts, and one restaurant traced from raw
rows all the way to the "did it improve?" answer. Read that output alongside
this doc.

## The data flow

```
NYC Socrata API
      │  pipeline/ingest.py         (run once, result frozen)
      ▼
data/raw/inspections_<date>_<hash>.parquet     ← 296,679 rows, 1 per violation
      │  pipeline/canonical.py  +  models/*.sql
      ▼
data/generated/canonical.duckdb                ← the "data product"
      ├─ restaurants   31,419   (grain: one row per establishment)
      ├─ inspections   93,480   (grain: one row per inspection event)
      ├─ violations   290,053   (grain: one row per cited violation)
      └─ views: restaurant_latest_inspection, restaurant_score_change,
               neighborhood_inspection_summary, ...
```

Everything downstream (the agent, tools, evals — not built yet) reads
`canonical.duckdb`. Nothing re-fetches from the internet.

## Files, in reading order

| File | What it is | Why it matters |
|---|---|---|
| `docs/experiment-design.md` | Phase 0: the thesis, the 8 "data product modes" we compare, the metrics, the acceptance gates | The whole project's contract with itself — read first |
| `docs/roadmap.md` | Build order, checkboxes | Where we are (Milestone 1 nearly done) |
| `pipeline/ingest.py` | Pulls + freezes the raw snapshot, stamps every row with a `source_record_id` | "Immutable raw input" — Episode 1 |
| `reports/raw_profile.md` | Auto-generated evidence of the mess | The "a table is not a data product" argument, in numbers |
| `models/restaurants.sql` | Builds the restaurant entity; **deterministic name normalization, no LLM** | Entity resolution — Episode 1 & the later Overkill Files episode |
| `models/inspections.sql` | Rolls 296k violation rows up to 93k inspection events | Making the grain explicit |
| `models/violations.sql` | Violation detail, dedupes 172 exact dups | — |
| `models/current_state.sql` | The marts that encode "latest", "improved vs got worse", "neighborhood" | The difference between *history* and *current state* — critical for agent questions |
| `semantic/metrics.yaml` | Machine-readable definitions: `score` is **lower_is_better**, what "latest" means, etc. | Episode 2 — we test whether feeding this to the agent changes its answers |
| `evals/questions.yaml` | 13 benchmark questions across 6 categories | Ground truth not computed yet — next step |
| `pipeline/canonical.py` | Orchestrates the SQL, runs integrity checks | `uv run python tasks.py canonical` rebuilds the product |
| `pipeline/peek.py` | The guided tour | `uv run python tasks.py peek` |

## Poke the data yourself

**Python REPL:**

```
uv run python
```
```python
import duckdb
con = duckdb.connect("data/generated/canonical.duckdb", read_only=True)
con.sql("SELECT dba_raw, name_normalized FROM restaurants WHERE name_normalized LIKE 'DUNKIN%'").show()
con.sql("SELECT * FROM restaurant_score_change ORDER BY score_change LIMIT 10").show()
```

**Or install a VSCode extension** to browse the `.duckdb` file visually: search
the Extensions panel for "SQLTools" + "SQLTools DuckDB", or the "DuckDB" viewer
extension, and point it at `data/generated/canonical.duckdb`.

## Demos (the filmable scripts)

Each build step has a standalone narrated script under `demos/`:

```
uv run python tasks.py demo          # list them
uv run python tasks.py demo 01       # the AI pipe + the cache
uv run python tasks.py demo 02       # naive baseline fails basic questions
```

They're deterministic (every model call is cached after the first run), so the
terminal output is identical every time — safe to film once, re-film later, or
edit around. `agent/`, `pipeline/`, etc. hold the reusable logic; `demos/` only
narrates it.

## Rebuild from scratch anytime

```
uv run python tasks.py ingest      # re-pull (new snapshot hash if the city updated the data)
uv run python tasks.py profile     # -> reports/raw_profile.md
uv run python tasks.py canonical   # -> data/generated/canonical.duckdb  (+ integrity checks)
uv run python tasks.py peek        # look at the result
```
