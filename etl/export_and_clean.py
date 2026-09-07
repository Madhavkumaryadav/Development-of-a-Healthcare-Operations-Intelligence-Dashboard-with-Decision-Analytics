"""Export source snapshots, clean them, and prepare Atlas-ready CSVs.

The raw export is byte-for-byte copied into ``data/raw_exports`` before any
transformation. When an original source CSV is not present, the existing
cleaned extract is copied as a clearly labelled fallback; this keeps the
pipeline complete without pretending that unavailable raw data exists.

Usage:
    python etl/export_and_clean.py
    python etl/export_and_clean.py --raw-only
    python etl/export_and_clean.py --clean-only
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw_exports"
MANIFEST_PATH = RAW_DIR / "manifest.json"

TABLES: dict[str, dict[str, Any]] = {
    "dim_dates": {"raw": "dim_date.csv", "cleaned": "dim_dates_cleaned.csv", "key": ["date_id"]},
    "dim_disease": {"raw": "dim_disease.csv", "cleaned": "dim_disease_cleaned.csv", "key": ["disease_id"]},
    "dim_program": {"raw": "dim_program.csv", "cleaned": "dim_program_cleaned.csv", "key": ["program_id"]},
    "dim_source": {"raw": "dim_source.csv", "cleaned": "dim_source_cleaned.csv", "key": ["source_id"]},
    "dim_state": {"raw": "dim_state.csv", "cleaned": "dim_state_cleaned.csv", "key": ["state_id"]},
    "fact_disease_surveillance": {"raw": "fact_disease_surveillance.csv", "cleaned": "fact_disease_surveillance_cleaned.csv", "key": ["date_id", "state_id", "disease_id", "source_id"]},
    "fact_environmental": {"raw": "fact_environmental.csv", "cleaned": "fact_environmental_cleaned.csv", "key": ["date_id", "state_id"]},
    "fact_health_programs": {"raw": "fact_health_programs.csv", "cleaned": "fact_health_programs_cleaned.csv", "key": ["date_id", "state_id", "program_id"]},
    "fact_lab_healthcare": {"raw": "fact_lab_healthcare.csv", "cleaned": "fact_lab_healthcare_cleaned.csv", "key": ["date_id", "state_id"]},
    "fact_outbreak": {"raw": "fact_outbreak.csv", "cleaned": "fact_outbreak_cleaned.csv", "key": ["outbreak_id"]},
}


def export_raw() -> dict[str, dict[str, Any]]:
    """Copy every table snapshot before cleaning and write a manifest."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, Any]] = {}
    for name, spec in TABLES.items():
        snapshot = RAW_DIR / f"{name}.csv"
        source = snapshot if snapshot.exists() else DATA_DIR / spec["raw"]
        source_kind = "raw_snapshot" if snapshot.exists() else "raw"
        if not source.exists():
            source = DATA_DIR / spec["cleaned"]
            source_kind = "cleaned_fallback"
        if not source.exists():
            raise FileNotFoundError(f"No source available for {name}: {source}")
        target = RAW_DIR / f"{name}.csv"
        shutil.copyfile(source, target)
        frame = pd.read_csv(target)
        manifest[name] = {
            "file": target.name,
            "source_file": source.name,
            "source_kind": source_kind,
            "rows": len(frame),
            "columns": list(frame.columns),
        }
        logging.info("Exported %s: %d raw snapshot rows (%s)", name, len(frame), source_kind)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def clean_table(name: str, spec: dict[str, Any]) -> tuple[int, int]:
    """Normalize headers/values and remove duplicate or incomplete keys."""
    frame = pd.read_csv(RAW_DIR / f"{name}.csv")
    frame.columns = [str(column).strip() for column in frame.columns]
    for column in frame.select_dtypes(include=["object"]).columns:
        frame[column] = frame[column].map(lambda value: value.strip() if isinstance(value, str) else value)
    for column in frame.columns:
        if column == "full_date" or column == "report_date_raw":
            frame[column] = pd.to_datetime(frame[column], errors="coerce").dt.strftime("%Y-%m-%d")
    before = len(frame)
    frame = frame.dropna(subset=spec["key"])
    frame = frame.drop_duplicates(subset=spec["key"], keep="last")
    frame.to_csv(DATA_DIR / spec["cleaned"], index=False, quoting=csv.QUOTE_MINIMAL)
    return before, len(frame)


def clean_all() -> None:
    for name, spec in TABLES.items():
        before, after = clean_table(name, spec)
        logging.info("Cleaned %s: %d -> %d rows", name, before, after)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export raw snapshots and create cleaned project CSVs.")
    parser.add_argument("--raw-only", action="store_true", help="Export snapshots without cleaning.")
    parser.add_argument("--clean-only", action="store_true", help="Clean an existing data/raw_exports snapshot.")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not args.clean_only:
        export_raw()
    if not args.raw_only:
        clean_all()
    logging.info("Data preparation complete. Next step: python etl/load_to_atlas.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())