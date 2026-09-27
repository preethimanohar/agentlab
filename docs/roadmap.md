# Build order

Do **not** work episode-by-episode. Build a thin end-to-end vertical slice
first, then go wide.

**Demo convention:** every build step gets a standalone narrated script in
`demos/NN_name.py` (run: `uv run python tasks.py demo NN`). Library code stays in
`agent/` etc.; demos only import and narrate, so each stays independently
runnable and filmable forever. See `demos/README.md`.

## Week 0 — toolchain (you)
- [x] git repo + structure
- [ ] `uv` installed, `uv sync` green
- [ ] `.env` with `ANTHROPIC_API_KEY`

## Week 1 — data foundation
1. [ ] `pipeline/ingest.py` — freeze hash-stamped NYC snapshot  ← *scaffolded*
2. [ ] `pipeline/profile.py` — raw profiling report            ← *scaffolded*
3. [x] Decide grain + entity model from the profile output
4. [x] `pipeline/canonical.py` + `models/*.sql` — restaurants / inspections / violations
5. [x] Deterministic entity normalization (no LLM) — `name_normalized`
6. [x] Current-state views: latest inspection, scored history, score_change, neighborhood summary
7. [x] `semantic/metrics.yaml` + `semantic/loader.py` (schema_block / semantics_block / context)
8. [~] `evals/questions.yaml` (13 Qs) + `evals/compute_ground_truth.py` -> `structured.yaml`
       — computed; awaiting human `verified_by_human: true`

**Gate:** >=95% deterministic correctness from canonical tables.  ← ground truth all resolves from the views/tables.

## Week 2 — agent + evaluation
9.  [x] Model client with record/replay cache — `agent/client.py` (`ask()`), model = claude-sonnet-5
10. [x] `agent/raw_agent.py` baseline — 300-row raw sample in the prompt, no tools
11. [x] `agent/sql_agent.py` — generate SQL -> run on canonical.duckdb -> retry on error -> answer.
       demos/03. 5/5 on the sample; naive got 2/4. Finding: agent already knows NYC
       'lower is better' from training, so semantic layer's value is elsewhere.
12. [ ] semantic-aware variant (adds semantics_block: views + tie-breaks) — demos/04
13. [ ] `evals/runner.py` — mode x category scorecard — demos/05
14. [ ] `app/streamlit_app.py` — Ask / Answer / Trace (minimal)

**Gate:** one command produces the scorecard.

## Week 3 — RAG + failure lab
15. [ ] policy documents into `data/documents/` with version/effective_date
16. [ ] `rag/` transparent pipeline (chunk / embed / retrieve / answer)
17. [ ] `evals/rag_questions.yaml`
18. [ ] `failures/base.py` — injector API: deterministic, reversible, manifest w/ predicted blast radius
19. [ ] injectors: stale, duplicates, identity, semantics, provenance, documents
20. [ ] run controlled experiments -> `experiments/failure_injection/`
21. [ ] generate failure matrix

## Week 4 — contracts + governed access
22. [ ] `contracts/restaurant_product.yaml` (only the failures that mattered)
23. [ ] `contracts/validators.py` (Pandera + asserts) + severity: BLOCK/WARN/MONITOR
24. [ ] publication gate; rerun corrupted-data experiments
25. [ ] `tools/*.py` governed functions, responses carry provenance
26. [ ] `tools/mcp_server.py` wrapper (last, thin)
27. [ ] `experiments/access_patterns/` — raw vs sql vs tools
28. [ ] `experiments/overkill_files/` — "is the data stale?" rule vs LLM vs agent
29. [ ] `evals/run_all.py` — regenerate every report + `reports/final_scorecard`
