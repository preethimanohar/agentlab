"""Build the canonical data product from the frozen raw snapshot.

    uv run python tasks.py canonical

Produces a persistent DuckDB database at data/generated/canonical.duckdb
(tables: restaurants, inspections, violations; + current-state views) plus
Parquet exports. Everything downstream (agent, tools, evals) reads this.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
from rich.console import Console

from pipeline.snapshot import latest_stem, manifest

console = Console()
GEN = Path("data/generated")
DB_PATH = GEN / "canonical.duckdb"
MODELS = ["restaurants", "inspections", "violations", "current_state"]


def build() -> None:
    GEN.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    raw_path = f"data/raw/{latest_stem()}.parquet"
    con = duckdb.connect(str(DB_PATH))
    con.execute(f"CREATE VIEW raw AS SELECT * FROM read_parquet('{raw_path}')")

    for name in MODELS:
        sql = Path(f"models/{name}.sql").read_text()
        con.execute(sql)
        console.log(f"ran models/{name}.sql")

    # provenance stamp
    m = manifest()
    con.execute("CREATE TABLE _snapshot AS SELECT * FROM (VALUES (?, ?, ?)) t(snapshot_hash, snapshot_date, source_system)",
                [m["snapshot_hash"], m["snapshot_date"], m["source_system"]])

    # export parquet
    for tbl in ("restaurants", "inspections", "violations"):
        con.execute(f"COPY {tbl} TO '{GEN / f'{tbl}.parquet'}' (FORMAT parquet)")

    checks(con)
    con.close()
    console.print(f"[green]built[/] {DB_PATH}")


def checks(con: duckdb.DuckDBPyConnection) -> None:
    console.print("\n[bold]row counts[/]")
    for tbl in ("restaurants", "inspections", "violations"):
        n = con.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
        console.print(f"  {tbl:<13} {n:>9,}")

    assertions = {
        "restaurants.camis unique":
            "SELECT count(*) - count(DISTINCT camis) FROM restaurants",
        "inspections.inspection_id unique":
            "SELECT count(*) - count(DISTINCT inspection_id) FROM inspections",
        "every inspection has a restaurant":
            "SELECT count(*) FROM inspections i LEFT JOIN restaurants r USING (camis) WHERE r.camis IS NULL",
        "every violation has an inspection":
            "SELECT count(*) FROM violations v LEFT JOIN inspections i USING (inspection_id) WHERE i.inspection_id IS NULL",
        "no negative scores":
            "SELECT count(*) FROM inspections WHERE score < 0",
        "is_scored matches score":
            "SELECT count(*) FROM inspections WHERE is_scored <> (score IS NOT NULL)",
    }
    console.print("\n[bold]integrity[/]")
    ok = True
    for label, sql in assertions.items():
        bad = con.execute(sql).fetchone()[0]
        mark = "[green]ok[/]" if bad == 0 else f"[red]FAIL ({bad})[/]"
        console.print(f"  {mark} {label}")
        ok = ok and bad == 0
    if not ok:
        raise SystemExit("integrity checks failed")


if __name__ == "__main__":
    build()
