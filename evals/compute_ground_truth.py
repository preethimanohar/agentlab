"""Compute deterministic ground truth for the structured benchmark.

    uv run python tasks.py ground-truth

Picks an example restaurant, runs each question's SQL against the frozen
canonical product, writes evals/ground_truth/structured.yaml, and prints a
table for a human to verify before the answers are trusted.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import yaml
from rich.console import Console
from rich.table import Table

from pipeline.snapshot import manifest

console = Console()
DB = "data/generated/canonical.duckdb"
QUESTIONS = Path("evals/questions.yaml")
OUT = Path("evals/ground_truth/structured.yaml")


def pick_example_camis(con: duckdb.DuckDBPyConnection) -> str:
    """Deterministic: single-location, clean name, exactly 4 scored inspections."""
    row = con.execute(
        """
        SELECT h.camis
        FROM restaurant_scored_history h
        JOIN restaurants r USING (camis)
        WHERE h.scored_count = 4
          AND r.name_normalized = r.dba_raw            -- no punctuation/case quirks
          AND r.dba_raw NOT SIMILAR TO '.*[0-9/()#].*' -- no store numbers / co-brands
          AND (SELECT count(*) FROM restaurants r2
               WHERE r2.name_normalized = r.name_normalized) = 1   -- unambiguous name
        GROUP BY h.camis
        ORDER BY h.camis
        LIMIT 1
        """
    ).fetchone()
    if not row:
        raise SystemExit("no example restaurant matched the criteria")
    return row[0]


def run(con: duckdb.DuckDBPyConnection, sql: str, answer_type: str):
    rows = con.execute(sql).fetchall()
    if answer_type == "set":
        return sorted(str(r[0]) for r in rows)
    if not rows:
        return None
    val = rows[0][0]
    return int(val) if answer_type == "number" and val is not None else val


def main() -> None:
    con = duckdb.connect(DB, read_only=True)
    spec = yaml.safe_load(QUESTIONS.read_text())
    camis = pick_example_camis(con)
    dba = con.execute("SELECT dba_raw FROM restaurants WHERE camis = ?", [camis]).fetchone()[0]
    console.print(f"[bold]EXAMPLE_CAMIS[/] = {camis}  ([italic]{dba}[/])\n")

    resolved = []
    for q in spec["questions"]:
        text = q["text"].replace("{camis}", camis)
        if q["truth"] == "fixed":
            gt = q["ground_truth"]
        elif q["truth"] == "manual":
            gt = None
        else:
            gt = run(con, q["sql"].replace("{camis}", camis), q["answer_type"])
        resolved.append({
            "id": q["id"], "category": q["category"], "text": text,
            "answer_type": q["answer_type"], "truth": q["truth"],
            "difficulty": q.get("difficulty", "clean"),
            "ground_truth": gt,
        })

    m = manifest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump({
        "snapshot_hash": m["snapshot_hash"],
        "snapshot_date": m["snapshot_date"],
        "example_camis": camis,
        "example_dba": dba,
        "verified_by_human": False,   # flip to true after eyeballing the table below
        "questions": resolved,
    }, sort_keys=False, width=100))

    t = Table(show_lines=True)
    for col in ("id", "category", "question", "answer_type", "ground truth"):
        t.add_column(col, overflow="fold")
    for r in resolved:
        gt = r["ground_truth"]
        gt_str = "(manual)" if gt is None and r["truth"] == "manual" else (
            "[red]NO RESULT[/]" if gt is None else str(gt))
        t.add_row(r["id"], r["category"], r["text"], r["answer_type"], gt_str)
    console.print(t)
    console.print(f"\n[green]wrote[/] {OUT}")
    console.print("[yellow]Review every row. If correct, set verified_by_human: true in that file.[/]")


if __name__ == "__main__":
    main()
