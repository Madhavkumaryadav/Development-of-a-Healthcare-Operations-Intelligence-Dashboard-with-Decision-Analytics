"""Load raw snapshots into Atlas, clean them, then publish clean collections.

Raw collections are prefixed with ``raw_`` and retain every source row. The
application-facing collections keep their existing names and contain only
rows that pass key/date/value normalization. Re-running is idempotent for
clean collections and replaces each raw snapshot for the selected run.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl.export_and_clean import RAW_DIR, TABLES, export_raw
from etl.load_to_atlas import _natural_key_from_dict, _sanitize

load_dotenv(PROJECT_ROOT / ".env")


def _raw_documents(name: str) -> list[dict[str, Any]]:
    frame = pd.read_csv(RAW_DIR / f"{name}.csv")
    frame.columns = [str(column).strip() for column in frame.columns]
    documents = []
    for row_number, row in enumerate(frame.to_dict("records")):
        document = {"_id": f"{name}:{row_number}", "source_row": row_number}
        document.update({column: _sanitize(value) for column, value in row.items()})
        documents.append(document)
    return documents


def _clean_documents(name: str) -> list[dict[str, Any]]:
    spec = TABLES[name]
    frame = pd.read_csv(RAW_DIR / f"{name}.csv")
    frame.columns = [str(column).strip() for column in frame.columns]
    for column in frame.select_dtypes(include=["object"]).columns:
        frame[column] = frame[column].map(lambda value: value.strip() if isinstance(value, str) else value)
    for column in frame.columns:
        if column in ("full_date", "report_date_raw"):
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    frame = frame.dropna(subset=spec["key"]).drop_duplicates(subset=spec["key"], keep="last")
    documents = []
    for row in frame.to_dict("records"):
        key = _natural_key_from_dict(row, spec["key"])
        if key is None:
            continue
        document = {"_id": key}
        document.update({column: _sanitize(value) for column, value in row.items()})
        documents.append(document)
    return documents


def _replace_collection(collection: Any, documents: list[dict[str, Any]]) -> None:
    collection.delete_many({})
    if documents:
        collection.insert_many(documents, ordered=False)


def run(dry_run: bool = False) -> dict[str, int]:
    export_raw()
    from pymongo import MongoClient

    uri = os.environ.get("MONGO_URI", "").strip()
    if not uri and not dry_run:
        raise SystemExit("MONGO_URI is required for an Atlas sync.")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000) if uri else None
    try:
        db = client[os.environ.get("MONGO_DB", "healthsentinel")] if client else None
        summary = {"raw": 0, "clean": 0}
        for name in TABLES:
            raw_docs = _raw_documents(name)
            clean_docs = _clean_documents(name)
            summary["raw"] += len(raw_docs)
            summary["clean"] += len(clean_docs)
            logging.info("%s: raw=%d clean=%d", name, len(raw_docs), len(clean_docs))
            if db is not None:
                _replace_collection(db[f"raw_{name}"], raw_docs)
                _replace_collection(db[name], clean_docs)
        return summary
    finally:
        if client is not None:
            client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync raw and cleaned HealthSentinel collections to Atlas.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare and count documents without Atlas writes.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    summary = run(args.dry_run)
    logging.info("Atlas pipeline complete: raw=%d clean=%d dry_run=%s", summary["raw"], summary["clean"], args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())