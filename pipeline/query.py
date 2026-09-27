"""Run ad-hoc SQL. `raw` is the frozen snapshot; canonical tables/views are also visible.

    uv run python tasks.py sql "SELECT count(*) FROM raw"
    uv run python tasks.py sql "SELECT * FROM restaurant_score_change ORDER BY score_change LIMIT 10"
    uv run python tasks.py sql --file scratch.sql
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from pipeline.snapshot import latest_stem


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sql", nargs="?", help="SQL string")
    ap.add_argument("--file", type=Path, help="read SQL from a file instead")
    ap.add_argument("--rows", type=int, default=50)
    args = ap.parse_args()

    sql = args.file.read_text() if args.file else args.sql
    if not sql:
        raise SystemExit('need SQL, e.g.  tasks.py sql "SELECT * FROM raw LIMIT 5"')

    db = Path("data/generated/canonical.duckdb")
    con = duckdb.connect(str(db), read_only=True) if db.exists() else duckdb.connect()
    # make the raw snapshot queryable as `raw` even before canonical is built
    if "raw" not in [r[0] for r in con.sql("SHOW TABLES").fetchall()]:
        con.execute(f"CREATE VIEW raw AS SELECT * FROM 'data/raw/{latest_stem()}.parquet'")
    con.sql(sql).show(max_rows=args.rows, max_width=240)


if __name__ == "__main__":
    main()
