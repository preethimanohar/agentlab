"""Profile the frozen raw snapshot. Evidence of the mess — nothing is cleaned here.

    uv run python tasks.py profile   ->   reports/raw_profile.md
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from rich.console import Console

from pipeline.snapshot import load_raw, manifest

console = Console()
OUT = Path("reports/raw_profile.md")


def md_table(rows: list[tuple], headers: tuple[str, ...]) -> str:
    line = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows)
    return "\n".join([line, sep, body])


def main() -> None:
    df = load_raw()
    m = manifest()
    n = df.height
    out: list[str] = []
    out.append(f"# Raw profile — snapshot `{m['snapshot_hash']}` ({m['snapshot_date']})")
    out.append(f"\n{n:,} rows (one row per cited violation), {df.width} columns.\n")

    # null / distinct per column
    null_rows = []
    for col in df.columns:
        nulls = df[col].null_count()
        blanks = df.filter(pl.col(col).cast(pl.Utf8).str.strip_chars() == "").height
        distinct = df[col].n_unique()
        null_rows.append((col, f"{(nulls + blanks) / n:.1%}", f"{distinct:,}"))
    out.append("## Null/blank rate and cardinality\n")
    out.append(md_table(null_rows, ("column", "null_or_blank", "distinct")))

    # key landmines
    out.append("\n## Landmines\n")
    checks = []

    never = df.filter(pl.col("inspection_date").str.starts_with("1900")).height
    checks.append(("inspection_date starts 1900 (never inspected)", f"{never:,}"))

    score_num = df.select(pl.col("score").cast(pl.Int64, strict=False).alias("s"))["s"]
    checks.append(("score is null/non-numeric", f"{score_num.null_count():,}"))
    checks.append(("score < 0 (invalid)", f"{score_num.filter(score_num < 0).len():,}"))
    checks.append(("score = 0 (valid, best)", f"{score_num.filter(score_num == 0).len():,}"))
    checks.append(("score > 100 (rare, valid)", f"{score_num.filter(score_num > 100).len():,}"))

    grade_lag = df.filter(
        (pl.col("grade_date").is_not_null())
        & (pl.col("grade_date") != pl.col("inspection_date"))
        & (pl.col("grade_date").str.strip_chars() != "")
    ).height
    checks.append(("grade_date != inspection_date", f"{grade_lag:,}"))

    dupes = n - df.select(["camis", "inspection_date", "inspection_type", "violation_code"]).n_unique()
    checks.append(("exact dup (camis,date,type,violation_code)", f"{dupes:,}"))

    out.append(md_table(checks, ("check", "count")))

    # grain: rows -> inspections -> restaurants
    restaurants = df["camis"].n_unique()
    inspections = df.select(["camis", "inspection_date", "inspection_type"]).n_unique()
    out.append("\n## Grain\n")
    out.append(md_table(
        [
            ("violation rows", f"{n:,}"),
            ("inspections (camis,date,type)", f"{inspections:,}"),
            ("restaurants (camis)", f"{restaurants:,}"),
            ("avg inspections / restaurant", f"{inspections / restaurants:.1f}"),
            ("avg violation rows / inspection", f"{n / inspections:.1f}"),
        ],
        ("level", "count"),
    ))

    # entity: same DBA across many CAMIS (chains) + name variants
    by_dba = (
        df.group_by("dba")
        .agg(pl.col("camis").n_unique().alias("establishments"))
        .sort("establishments", descending=True)
        .head(10)
    )
    out.append("\n## Top DBA names by distinct establishments (chains)\n")
    out.append(md_table(list(by_dba.iter_rows()), ("dba", "establishments")))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    console.print(f"[green]wrote[/] {OUT}")


if __name__ == "__main__":
    main()
