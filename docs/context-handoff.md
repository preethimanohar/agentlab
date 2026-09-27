# agentlab — context handoff

Paste this into a new Claude chat to bring it up to speed on the project without re-explaining from scratch.

## What this is

`agent-ready-data-lab` (repo: `D:\preethi\git\agentlab`) is a hands-on experiment lab being built to produce a **5-episode vlog**. Core question: *what changes when an AI agent becomes a consumer of a data product?*

Domain: Restaurant / Food Safety Intelligence, using NYC DOHMH restaurant inspection data.

Progression the build follows:

```
Raw Data -> Canonical Data Product -> Semantic Layer -> Agent + RAG Baseline
   -> Failure Injection -> Data Contract -> Governed Tools / MCP -> Evaluation + Comparison
```

## The bar this work (and the vlog) must clear

- Own an ambiguous, high-stakes problem end-to-end — not execute a defined ticket
- Treat failure modes, evaluation, governance, and economics as first-class design concerns, not afterthoughts
- Produce durable artifacts (contracts, regression suites, routing rules, decision frameworks) that are reusable, not one-offs
- Make explicit, evidence-based "what would I ship" calls under real constraints (accuracy, latency, cost, maintainability, residual risk)
- Show system-level judgment, not isolated feature work

The user is coding this end-to-end themselves *before* filming, to genuinely understand the process — this isn't scripted after the fact.

## Locked decisions (do not relitigate these)

- **Dataset:** NYC DOHMH Restaurant Inspection Results (Socrata `43nn-pn8j`), frozen to a hash-stamped Parquet snapshot in `data/raw/`. A 2026-08-31 snapshot had 296,679 violation rows -> 97,192 inspections -> 31,419 restaurants; the hash rotates on re-ingest since the live dataset updates daily.
- **Model:** `claude-sonnet-5`, fixed as the control across every experiment (the independent variable is the *data product*, not the model). All calls go through a prompt-hash record/replay cache (`.cache/`) so reruns are free and identical — this is what makes results filmable and reproducible.
- **Toolchain:** `uv`, not system Python. All commands run as `uv run python tasks.py <task>`.
- **Entity resolution:** deterministic only, via `name_normalized`. Never merge across `CAMIS` (the stable restaurant id). LLM-based entity resolution is deliberately deferred to a later "Overkill Files" episode.

## Working style the user wants from Claude

- Baby steps, one concept at a time; explain *before* and *after* building each piece.
- Every build step gets its own standalone, narrated script in `demos/NN_name.py`, run via `uv run python tasks.py demo NN`. Library code lives in `agent/`, `pipeline/`, etc. — demos only import and narrate, never absorb logic, so each stays independently runnable and filmable forever. Nothing gets merged into one mega-runner.
- Demos are deterministic thanks to the `.cache/`.

## Experiment design (Phase 0, locked before implementation)

**Thesis:** making a dataset "agent-ready" (canonical grain, resolved entities, explicit semantics, provenance, contracts, governed tools) changes agent answer quality — but the agent-ready product is *not assumed to win*. A small difference, or a win confined to specific question categories, is an equally publishable result.

**Modes compared** (the data product varies; the model does not):

| Mode | Description |
|---|---|
| `raw` | LLM gets a raw/sample representation of the source |
| `schema` | LLM gets schema + SQL execution tool |
| `schema+semantics` | above + machine-consumed `semantic/metrics.yaml` |
| `rag` | + policy-document retrieval |
| `rag_broken` | rag after a failure injection |
| `contract_protected` | corrupted data blocked/flagged by contract before the agent |
| `sql_agent` | arbitrary SQL |
| `governed_tools` | only explicit product functions, responses carry provenance |

**Benchmark question categories** (`evals/questions.yaml`): direct_lookup, aggregation, temporal, identity, semantic, provenance. Ground truth computed by deterministic SQL against the frozen snapshot, eyeball-verified by a human before freezing.

**Metrics** (no LLM judge for structured questions — compared against frozen ground truth): `answer_correctness`, `query_success_rate`, `entity_resolution_accuracy`, `freshness_accuracy`, `provenance_coverage`, `unsupported_answer_rate`, `latency_s`, `tokens`.

**"Done" = 7 artifacts + one command regenerates results:** canonical product; agent; RAG baseline; failure-injection framework; automated eval suite; machine-verifiable contract; governed tool/MCP interface.

## Known data landmines (already discovered, informing the canonical model)

- `inspection_date` year 1900 => never inspected (3,712 rows; null action & type)
- `score` null/absent ~6% (not scored); **0 is valid and best**; no negatives; max 214
- `score`/`grade` are invariant within an inspection
- `grade`: A/B/C final; N/Z/P pending; ~51% null
- `inspection_type` is compound (`"<program> / <kind>"`) => needs splitting
- `action` encodes closures (10,862 "Closed by DOHMH") => derive `was_closed`
- `boro = '0'` (352 rows) is a missing sentinel => null it
- 172 exact-duplicate violation rows => dedupe at violation grain
- One row per violation in source => inspection grain requires aggregation
- `CAMIS` is a stable id, so entity resolution is mostly solved by the source; DBA name variants (e.g. 66 "%dunkin%" spellings) need deterministic normalization that *correctly refuses* to merge co-brands/store-number noise across CAMIS

## Repo layout

| Path | Purpose |
|---|---|
| `pipeline/` | ingest, normalize, entity resolution, build canonical tables |
| `models/` | SQL for canonical + current-state views |
| `semantic/` | machine-consumed metric & entity definitions (YAML) |
| `contracts/` | data-contract specs + validators + publication gate (not yet built) |
| `rag/` | chunk / embed / retrieve / answer over policy documents (not yet built) |
| `agent/` | raw-context, SQL, and governed-tool agents |
| `tools/` | governed data-product functions + MCP server (not yet built) |
| `failures/` | deterministic failure injectors (not yet built) |
| `evals/` | question banks, ground truth, metrics, runner |
| `experiments/` | one folder per controlled comparison (not yet built) |
| `reports/` | regenerable outputs (profiles, scorecards) |
| `demos/` | one narrated, standalone script per build step |

## Progress as of 2026-09-05 (Milestone 1 done, Milestone 2 in progress)

- **Session 1** — `agent/client.py`: `ask()` + `.cache/` record-replay. `demos/01`.
- **Session 2** — `agent/raw_agent.py`: naive baseline, 300-row raw sample stuffed into the prompt. `demos/02`. Scored 2/4 on the sample; misses were structural (not a knowledge gap).
- **Session 3** — `agent/sql_agent.py`: model writes SQL -> runs it on `canonical.duckdb` -> retries on error -> answers. `demos/03`. Scored 5/5 on the sample, ~$0.03 total.
  - **Finding worth carrying forward:** the model already "knows" NYC's convention that a lower inspection score is better, from pretraining — so the semantic layer likely adds little for *directionality*. Its expected value is elsewhere: tie-break rules, obscure/derived metrics, and picking the correct view (e.g. current-state vs full history).
- **Next up:** Session 4 — semantic-aware variant (`sql_agent` + a `semantics_block` from `semantic/metrics.yaml`), landing in `demos/04`.

Roadmap detail (checkbox source of truth) lives in `docs/roadmap.md`; full experiment design lives in `docs/experiment-design.md`.
