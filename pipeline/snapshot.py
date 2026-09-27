"""Locate the frozen raw snapshot. Shared by profiling, canonical build, evals."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

RAW_DIR = Path("data/raw")


def latest_stem() -> str:
    pointer = RAW_DIR / "LATEST"
    if not pointer.exists():
        raise SystemExit("no snapshot found — run: uv run python tasks.py ingest")
    return pointer.read_text().strip()


def load_raw() -> pl.DataFrame:
    return pl.read_parquet(RAW_DIR / f"{latest_stem()}.parquet")


def manifest() -> dict:
    return json.loads((RAW_DIR / f"{latest_stem()}.manifest.json").read_text())
