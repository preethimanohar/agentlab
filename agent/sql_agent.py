"""The SQL agent ('schema' mode) — library code.

`answer(question)` runs this loop:

  1. ask the model for ONE DuckDB SQL query, given only the base-table schema
  2. run it against data/generated/canonical.duckdb (read-only)
     - on error, feed the error back and let it retry (up to MAX_ATTEMPTS)
  3. ask the model for a one-sentence final answer, given the rows it got back

Returns a SqlRun with the full trace (sql, rows, answer, attempts, cost).

Filmable walkthrough: demos/03_sql_agent.py
Interactive poke:     uv run python tasks.py sqlagent [--show] "your question"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import duckdb

from agent.client import ask
from semantic.loader import SemanticLayer

DB = "data/generated/canonical.duckdb"
MAX_ATTEMPTS = 2
MAX_RESULT_ROWS = 200          # how many rows we feed back to the model

SYSTEM_SQL = (
    "You are a data analyst answering questions about NYC restaurant inspection "
    "data by writing DuckDB SQL. You are given the schema. Reply with ONE SQL "
    "query and nothing else — no prose, no markdown fences, no trailing semicolon."
)
SYSTEM_ANSWER = (
    "You are a data analyst. Given a question, the SQL that ran, and the rows it "
    "returned, answer in ONE short sentence. State the concrete value. If the "
    "result is empty or clearly wrong, say so."
)


def _schema() -> str:
    return SemanticLayer.load().schema_block()


def _clean_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    sql = (m.group(1) if m else text).strip()
    sql = re.sub(r"^\s*SQL\s*:\s*", "", sql, flags=re.I)
    return sql.strip().rstrip(";").strip()


def _run(sql: str):
    """(ok, columns, rows) on success; (False, error_message, None) on failure."""
    con = duckdb.connect(DB, read_only=True)
    try:
        rel = con.sql(sql)
        return True, rel.columns, rel.fetchall()
    except Exception as e:  # noqa: BLE001 — we want any DuckDB error as text
        return False, str(e).splitlines()[0], None
    finally:
        con.close()


def _format_rows(cols, rows) -> str:
    head = [" | ".join(cols)]
    for r in rows[:MAX_RESULT_ROWS]:
        head.append(" | ".join("" if v is None else str(v) for v in r))
    if len(rows) > MAX_RESULT_ROWS:
        head.append(f"... ({len(rows) - MAX_RESULT_ROWS} more rows)")
    return "\n".join(head)


@dataclass
class SqlRun:
    question: str
    sql: str = ""
    ok: bool = False
    error: str = ""
    row_count: int = 0
    result_preview: str = ""
    final_answer: str = ""
    attempts: int = 0
    cost_usd: float = 0.0
    trace: list[str] = field(default_factory=list)


def answer(question: str) -> SqlRun:
    run = SqlRun(question=question)
    feedback = None
    cols = rows = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        run.attempts = attempt
        prompt = f"{_schema()}\n\nQuestion: {question}"
        if feedback:
            prompt += f"\n\nYour previous query failed with:\n{feedback}\nWrite a corrected query."
        rep = ask(prompt, system=SYSTEM_SQL)
        run.cost_usd += rep.cost_usd
        run.sql = _clean_sql(rep.text)
        run.trace.append(f"attempt {attempt} SQL:\n{run.sql}")

        ok, a, b = _run(run.sql)
        if ok:
            run.ok, cols, rows = True, a, b
            run.row_count = len(rows)
            break
        feedback = a
        run.error = a
        run.trace.append(f"attempt {attempt} error: {a}")

    if not run.ok:
        run.final_answer = f"(could not produce a working query: {run.error})"
        return run

    run.result_preview = _format_rows(cols, rows)
    rep = ask(
        f"Question: {question}\n\nSQL that ran:\n{run.sql}\n\n"
        f"Result ({run.row_count} rows):\n{run.result_preview}\n\nFinal answer:",
        system=SYSTEM_ANSWER,
    )
    run.cost_usd += rep.cost_usd
    run.final_answer = rep.text
    run.trace.append(f"answer: {run.final_answer}")
    return run


if __name__ == "__main__":               # interactive poke — the demo is in demos/
    import sys

    args = [a for a in sys.argv[1:] if a != "--show"]
    show = "--show" in sys.argv
    if not args:
        raise SystemExit('usage: uv run python tasks.py sqlagent [--show] "your question"')
    q = " ".join(args)

    if show:
        print("=== SYSTEM (sql step) ===\n" + SYSTEM_SQL)
        print("\n=== USER (sql step) ===\n" + f"{_schema()}\n\nQuestion: {q}")
        raise SystemExit

    r = answer(q)
    print(f"SQL ({r.attempts} attempt(s)):\n{r.sql}\n")
    print(f"rows: {r.row_count}")
    print(f"\nANSWER: {r.final_answer}")
    print(f"\n[cost ${r.cost_usd:.4f}]")
