# agent-ready-data-lab

**Core question:** What changes when an AI agent becomes a consumer of a data product?

**Domain:** Restaurant / Food Safety Intelligence (NYC DOHMH inspection results)

## Progression

```
Raw Data
   -> Canonical Data Product
   -> Semantic Layer
   -> Agent + RAG Baseline
   -> Failure Injection
   -> Data Contract
   -> Governed Tools / MCP
   -> Evaluation + Comparison
```

Each milestone leaves behind an artifact the next one depends on. See
`docs/experiment-design.md` for the locked Phase 0 setup (thesis, metrics,
model-as-control decision) and `docs/roadmap.md` for the build order.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python tasks.py ingest     # pull + freeze an immutable NYC inspection snapshot
uv run python tasks.py profile    # generate reports/raw_profile.md ("evidence of the mess")
```

## Layout

| Path | Purpose |
|---|---|
| `pipeline/` | ingest, normalize, entity resolution, build canonical tables |
| `models/` | SQL for canonical + current-state views |
| `semantic/` | machine-consumed metric & entity definitions (YAML) |
| `contracts/` | data-contract specs + validators + publication gate |
| `rag/` | chunk / embed / retrieve / answer over policy documents |
| `agent/` | raw-context, SQL, and governed-tool agents |
| `tools/` | governed data-product functions (+ MCP server) |
| `failures/` | deterministic failure injectors (one variable at a time) |
| `evals/` | question banks, ground truth, metrics, runner |
| `experiments/` | one folder per controlled comparison |
| `reports/` | regenerable outputs (profiles, scorecards) |
