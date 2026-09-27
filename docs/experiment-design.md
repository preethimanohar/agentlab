# Phase 0 — Experiment Design (locked before implementation)

This document is written *before* building anything so success criteria are not
invented after the fact.

## Thesis

Making a dataset "agent-ready" (canonical grain, resolved entities, explicit
semantics, provenance, contracts, governed tools) changes agent answer quality.
**We do not assume the agent-ready product wins.** Small differences, or wins
only in specific question categories, are equally publishable results.

## The independent variable is the data product, not the model

The agent model is a **control**, held fixed across every experiment:

- Primary model: `claude-sonnet-5` (frontier-class, ~2.5x cheaper than Opus,
  which matters across many benchmark re-runs). Fixed for every experiment.
  (Sampling params like `temperature` are not accepted on Sonnet 5 / Opus 5 —
  determinism comes from the cache below, not a temperature knob.)
- All model calls go through a **record/replay cache** keyed by prompt hash, so
  reruns return the identical stored answer — free and repeatable.
- Optional *secondary* axis (one episode only): a small local model, to ask
  "does agent-readiness matter more when the consumer is weak?" This is
  deliberate, never the default.

The data product is what varies:

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

## Datasets

- **Structured:** NYC DOHMH Restaurant Inspection Results (Socrata `43nn-pn8j`).
  Pinned to a hash-stamped Parquet snapshot in `data/raw/` — the data updates
  daily; ground truth must not drift.
- **Unstructured (Milestone 3+):** NYC health-code / inspection-scoring rules,
  with `effective_date` / `version` metadata. If genuine dated versions are not
  available, a synthetic prior version is constructed and **disclosed in-episode**.

### Known landmines (confirmed against a 2026-08-31 snapshot, 296,679 rows;
### the content hash rotates whenever the live dataset changes on re-ingest)
- `inspection_date` year 1900 => never inspected (3,712 rows; null action & type)
- `score` null/absent ~6% (= not scored); **0 is valid and best**; no negatives; max 214
- `score`/`grade` are invariant within an inspection (safe at inspection grain)
- `grade`: A/B/C are final; N/Z/P pending; ~51% null. grade_date == inspection_date
  in this snapshot (no lag here)
- `inspection_type` is compound: "<program> / <kind>" => split
- `action` encodes closures: 10,862 "Closed by DOHMH" => derive `was_closed`
- `boro = '0'` (352 rows) => missing sentinel, null it
- 172 exact-duplicate violation rows => dedupe at violation grain
- one row per violation => inspection grain needs aggregation
  (296,679 rows -> 97,192 inspections -> 31,419 restaurants)
- `CAMIS` is a stable restaurant id, so entity resolution is largely solved by
  the source. DBA names are messy (66 "%dunkin%" variants: `DUNKIN`, `DUNKIN'`,
  curly-quote `DUNKIN'`, `DUNKIN99`, co-brands `DUNKIN' / BASKIN ROBBINS`).
  Deterministic name normalization merges the punctuation/case variants and
  *correctly refuses* the co-brands / store-number noise -- this is the tension
  the identity questions and the *Overkill Files* (LLM entity resolution) episode
  are built on. We never merge across CAMIS.

## Benchmark questions

`evals/questions.yaml` — categories:

| Category | Example | Why it matters |
|---|---|---|
| direct_lookup | latest inspection score for restaurant X | baseline |
| aggregation | neighborhood with highest average score | grain correctness |
| temporal | restaurants that deteriorated between last two inspections | current-vs-history |
| identity | how many inspections has "Joe's Pizza" had | entity resolution |
| semantic | which restaurants improved the most | needs directionality fact |
| provenance | what record supports this answer | traceability |

Ground truth is computed by deterministic SQL against the frozen snapshot and
**eyeball-verified by a human before freezing** (`evals/ground_truth/`).

## Metrics

Defined in `evals/metrics.py`. For deterministic structured questions we compare
against frozen ground truth — **no LLM judge**. RAG/explanation questions use a
rubric + strong model as judge, spot-checked by hand.

| Metric | Definition |
|---|---|
| `answer_correctness` | matches frozen ground truth (exact / numeric tolerance / set) |
| `query_success_rate` | generated query executed without error |
| `entity_resolution_accuracy` | resolved to the correct canonical entity |
| `freshness_accuracy` | "current state" answers reflect the latest record |
| `provenance_coverage` | fraction of answers carrying a valid source record id |
| `unsupported_answer_rate` | answered without retrievable support (should be low) |
| `latency_s`, `tokens` | cost axes |

## Milestone acceptance gates

1. **Canonical product:** >=95% deterministic correctness on structured
   questions answered directly from canonical tables; 100% metrics documented;
   100% canonical rows trace to a raw source record.
2. **Agent + eval:** full `mode` x `category` scorecard produced by one command;
   no predetermined winner.
3. **RAG + failure lab:** every injector deterministic + reversible + emits a
   manifest with predicted blast radius; failure matrix cells come from measured
   eval deltas.
4. **Contracts:** confusion matrix of (contract caught / missed) x (failure
   harmful / benign); headline metric = downstream agent failures prevented by
   upstream controls.
5. **Governed access:** `raw` vs `sql_agent` vs `governed_tools` on the same
   benchmark; include >=1 question class where governed tools *lose*.

## "Done" = 7 artifacts + one command regenerates results

canonical product; agent; RAG baseline; failure-injection framework; automated
eval suite; machine-verifiable contract; governed tool/MCP interface.
