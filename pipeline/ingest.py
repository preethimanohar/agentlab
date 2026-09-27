"""Pull the NYC DOHMH Restaurant Inspection Results and freeze an immutable snapshot.

The source (Socrata dataset 43nn-pn8j) updates daily. Everything downstream is
pinned to the hash-stamped Parquet written here so ground truth cannot drift.

    uv run python tasks.py ingest
    uv run python tasks.py ingest --limit 20000   # fast dev sample
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path

import httpx
import polars as pl
from rich.console import Console

SODA_URL = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"
PAGE = 50_000
RAW_DIR = Path("data/raw")
console = Console()

# Columns we keep. Socrata returns strings; typing happens in the canonical layer.
COLUMNS = [
    "camis", "dba", "boro", "building", "street", "zipcode", "phone",
    "cuisine_description", "inspection_date", "action", "violation_code",
    "violation_description", "critical_flag", "score", "grade", "grade_date",
    "record_date", "inspection_type", "latitude", "longitude",
    "community_board", "council_district", "census_tract", "bin", "bbl", "nta",
]


def fetch(limit: int | None) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    app_token = None  # optional; set SODA app token here if you hit rate limits
    with httpx.Client(timeout=120) as client:
        while True:
            page_size = PAGE if limit is None else min(PAGE, limit - len(rows))
            if page_size <= 0:
                break
            params = {
                "$select": ",".join(COLUMNS),
                "$limit": page_size,
                "$offset": offset,
                "$order": "camis,inspection_date",
            }
            headers = {"X-App-Token": app_token} if app_token else {}
            resp = client.get(SODA_URL, params=params, headers=headers)
            resp.raise_for_status()
            batch = resp.json()
            rows.extend(batch)
            console.log(f"fetched {len(rows):,} rows")
            if len(batch) < page_size:
                break
            offset += page_size
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="row cap for a dev sample")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows = fetch(args.limit)
    if not rows:
        raise SystemExit("no rows returned")

    df = pl.DataFrame(rows)
    for col in COLUMNS:  # ensure stable schema even if a page omitted a sparse column
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).alias(col))
    df = df.select(COLUMNS)

    df = df.sort(["camis", "inspection_date", "inspection_type", "violation_code"])
    # content hash (not parquet bytes) so it is stable across writes of the same data
    row_hashes = sorted(df.hash_rows(seed=0).to_list())
    digest = hashlib.sha256(repr(row_hashes).encode()).hexdigest()[:16]

    # stable provenance id: snapshot digest + ordinal in the sorted snapshot
    df = df.with_row_index("_i").with_columns(
        (pl.lit(digest) + ":" + pl.col("_i").cast(pl.Utf8).str.pad_start(6, "0"))
        .alias("source_record_id")
    ).drop("_i").select(["source_record_id", *COLUMNS])

    buf = io.BytesIO()
    df.write_parquet(buf)
    parquet_bytes = buf.getvalue()
    snapshot_date = dt.date.today().isoformat()
    stem = f"inspections_{snapshot_date}_{digest}"

    (RAW_DIR / f"{stem}.parquet").write_bytes(parquet_bytes)
    manifest = {
        "dataset": "NYC DOHMH Restaurant Inspection Results",
        "source_system": "NYC Socrata 43nn-pn8j",
        "url": SODA_URL,
        "snapshot_date": snapshot_date,
        "snapshot_hash": digest,
        "rows": df.height,
        "columns": df.columns,
        "row_limit": args.limit,
        "fetched_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    (RAW_DIR / f"{stem}.manifest.json").write_text(json.dumps(manifest, indent=2))
    (RAW_DIR / "LATEST").write_text(stem)

    console.print(f"[green]froze[/] {df.height:,} rows -> data/raw/{stem}.parquet")
    console.print(f"snapshot_hash = [bold]{digest}[/]")


if __name__ == "__main__":
    main()
