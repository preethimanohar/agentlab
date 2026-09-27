"""A guided tour of what has been built so far. Read-only.

    uv run python tasks.py peek

Prints: the frozen snapshot, the raw shape, each canonical table (schema +
samples), the current-state marts, and one restaurant traced end to end.
"""

from __future__ import annotations

import duckdb
from rich.console import Console
from rich.rule import Rule

from pipeline.snapshot import latest_stem, manifest

console = Console()
DB = "data/generated/canonical.duckdb"


def show(title: str, sql: str, con: duckdb.DuckDBPyConnection, rows: int = 6) -> None:
    console.print(f"\n[bold cyan]{title}[/]")
    console.print(f"[dim]{sql.strip()}[/]")
    con.sql(sql).show(max_rows=rows)


def main() -> None:
    m = manifest()
    console.print(Rule("1. The frozen raw snapshot"))
    console.print(
        f"file        data/raw/{latest_stem()}.parquet\n"
        f"source      {m['source_system']}  ({m['url']})\n"
        f"pulled      {m['snapshot_date']}   rows {m['rows']:,}   hash {m['snapshot_hash']}\n"
        "Nothing downstream re-fetches; every result is pinned to this file."
    )

    con = duckdb.connect(DB, read_only=True)

    console.print(Rule("2. Raw is one row per violation — messy on purpose"))
    show("first raw rows", "SELECT source_record_id, camis, dba, inspection_date, "
         "inspection_type, score, grade, violation_code FROM raw LIMIT 5", con)
    console.print("See reports/raw_profile.md for the full mess (1900 dates, "
                  "null scores, 66 'Dunkin' spellings, ...).")

    console.print(Rule("3. Canonical tables (built by models/*.sql)"))
    for tbl in ("restaurants", "inspections", "violations"):
        n = con.sql(f"SELECT count(*) FROM {tbl}").fetchone()[0]
        console.print(f"\n[bold]{tbl}[/]  —  {n:,} rows")
        con.sql(f"DESCRIBE {tbl}").show(max_rows=30)
        con.sql(f"SELECT * FROM {tbl} LIMIT 3").show(max_rows=3)

    console.print(Rule("4. Current-state marts (models/current_state.sql)"))
    show("latest scored inspection per restaurant",
         "SELECT camis, inspection_date, score, grade, was_closed FROM restaurant_latest_inspection LIMIT 5", con)
    show("did they improve or get worse vs the prior inspection? (lower score = better)",
         "SELECT direction, count(*) FROM restaurant_score_change GROUP BY 1 ORDER BY 2 DESC", con)
    show("neighborhood rollup",
         "SELECT * FROM neighborhood_inspection_summary WHERE restaurants_with_score > 100 "
         "ORDER BY avg_latest_score DESC LIMIT 5", con)

    console.print(Rule("5. One restaurant, traced end to end"))
    camis = con.sql(
        "SELECT camis FROM restaurant_score_change WHERE prev_score BETWEEN 20 AND 40 "
        "AND latest_score < 14 ORDER BY camis LIMIT 1").fetchone()[0]
    console.print(f"camis = {camis}")
    show("identity", f"SELECT camis, dba_raw, name_normalized, boro, nta FROM restaurants WHERE camis = '{camis}'", con)
    show("full inspection history",
         f"SELECT inspection_date, program, inspection_kind, score, grade, total_violations, critical_violations "
         f"FROM inspections WHERE camis = '{camis}' ORDER BY inspection_date", con, rows=20)
    show("its score change (the semantic view)",
         f"SELECT * FROM restaurant_score_change WHERE camis = '{camis}'", con)
    show("provenance: which raw records back the latest inspection",
         f"SELECT inspection_date, score, source_record_ids FROM restaurant_latest_inspection WHERE camis = '{camis}'", con)
    console.print("\n[green]Each source_record_id maps back to an exact row in the frozen parquet.[/]")

    con.close()


if __name__ == "__main__":
    main()
