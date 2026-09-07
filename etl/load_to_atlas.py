"""
etl/load_to_atlas.py
---------------------
Phase 1 ETL: load every cleaned CSV extract (data/*_cleaned.csv) into a
MongoDB Atlas database, one collection per table, keyed by each table's
natural key so re-running the script never creates duplicate documents.

Design notes
------------
* Idempotency: every document's ``_id`` is the natural key (e.g.
  ``"3|7|2|4"`` for state x date x disease x source). Rows are upserted
  with ``replace_one(..., upsert=True)`` inside batched ``bulk_write``
  calls, so re-runs update in place instead of duplicating.
* Schema validation: each CSV is checked for its required columns and for
  missing natural-key values before anything is written. Rows with a
  missing key are skipped and counted, never silently dropped.
* Value sanitisation: NaN / Inf / NaT are converted to null and numpy
  scalars are converted to native Python types so every document is
  BSON-safe (PyMongo rejects numpy types).
* Credentials: the connection string comes from ``MONGO_URI`` in the
  environment or a ``.env`` file at the project root (or ``--uri``).
  Nothing is hardcoded in this repo.
* Dry run: ``--dry-run`` validates schemas, builds all documents and
  reports row counts / what would be written, without connecting to Atlas.

Usage
-----
    python etl/load_to_atlas.py --dry-run
    python etl/load_to_atlas.py
    python etl/load_to_atlas.py --collections dim_state,fact_disease_surveillance
    python etl/load_to_atlas.py --uri "mongodb+srv://user:pass@cluster.mongodb.net" --db healthsentinel
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Load .env from the project root if it exists (never fail if absent).
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_DB_NAME = "healthsentinel"
DEFAULT_BATCH_SIZE = 1000

# --------------------------------------------------------------------------- #
# Collection registry: collection name -> CSV file, natural key, date columns
# --------------------------------------------------------------------------- #
COLLECTIONS: dict[str, dict[str, Any]] = {
    "dim_dates": {
        "file": "dim_dates_cleaned.csv",
        "key": ["date_id"],
        "dates": ["full_date"],
    },
    "dim_disease": {
        "file": "dim_disease_cleaned.csv",
        "key": ["disease_id"],
        "dates": [],
    },
    "dim_program": {
        "file": "dim_program_cleaned.csv",
        "key": ["program_id"],
        "dates": [],
    },
    "dim_source": {
        "file": "dim_source_cleaned.csv",
        "key": ["source_id"],
        "dates": [],
    },
    "dim_state": {
        "file": "dim_state_cleaned.csv",
        "key": ["state_id"],
        "dates": [],
    },
    "fact_disease_surveillance": {
        "file": "fact_disease_surveillance_cleaned.csv",
        "key": ["date_id", "state_id", "disease_id", "source_id"],
        "dates": ["report_date_raw"],
    },
    "fact_environmental": {
        "file": "fact_environmental_cleaned.csv",
        "key": ["date_id", "state_id"],
        "dates": [],
    },
    "fact_health_programs": {
        "file": "fact_health_programs_cleaned.csv",
        "key": ["date_id", "state_id", "program_id"],
        "dates": [],
    },
    "fact_lab_healthcare": {
        "file": "fact_lab_healthcare_cleaned.csv",
        "key": ["date_id", "state_id"],
        "dates": [],
    },
    # NOTE: the (date_id, state_id, disease_id, source_id) grain is NOT unique
    # in this CSV — 38 composite keys appear twice with different values, so a
    # composite key would silently overwrite real outbreak records. The row's
    # own outbreak_id is unique per record and stable, so it is the key.
    "fact_outbreak": {
        "file": "fact_outbreak_cleaned.csv",
        "key": ["outbreak_id"],
        "dates": [],
    },
}


# --------------------------------------------------------------------------- #
# CSV -> documents
# --------------------------------------------------------------------------- #
def read_csv(collection_name: str) -> pd.DataFrame:
    """Read a collection's CSV file, stripping stray whitespace from headers."""
    spec = COLLECTIONS[collection_name]
    path = DATA_DIR / spec["file"]
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV for '{collection_name}': {path}")
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def validate_schema(df: pd.DataFrame, collection_name: str) -> None:
    """Ensure every required column exists; raise if any are missing."""
    spec = COLLECTIONS[collection_name]
    required = spec["key"] + [c for c in df.columns if c not in spec["key"]]
    # Required = key columns plus any explicitly listed date columns.
    required = list(dict.fromkeys(spec["key"] + spec["dates"]))
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"'{collection_name}' CSV is missing required column(s): {missing}. "
            f"Expected keys: {spec['key']}"
        )


def _sanitize(value: Any) -> Any:
    """Convert a pandas/numpy value into a BSON-safe native Python value."""
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, np.datetime64):
        return pd.Timestamp(value).to_pydatetime()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if value is pd.NA or (isinstance(value, float) and value != value):
        return None
    return value


def build_documents(collection_name: str) -> tuple[list[dict[str, Any]], int]:
    """
    Turn a collection's CSV into upsert-ready documents.

    Returns (documents, skipped) where ``skipped`` is the number of rows
    dropped because a natural-key value was missing.
    """
    spec = COLLECTIONS[collection_name]
    key_cols: list[str] = spec["key"]
    date_cols: list[str] = spec["dates"]

    df = read_csv(collection_name)
    validate_schema(df, collection_name)

    # Parse date columns up front so they are stored as BSON dates.
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Warm up natural keys as a numpy array for speed.
    documents: list[dict[str, Any]] = []
    skipped = 0
    seen_keys: set[str] = set()
    duplicate_keys = 0

    for row in df.itertuples(index=False):
        row_dict = row._asdict()
        key = _natural_key_from_dict(row_dict, key_cols)
        if key is None:
            skipped += 1
            continue
        if key in seen_keys:
            duplicate_keys += 1
        seen_keys.add(key)
        doc = {"_id": key}
        for col, value in row_dict.items():
            doc[col] = _sanitize(value)
        documents.append(doc)

    if duplicate_keys:
        logging.warning(
            "'%s': %d row(s) share a natural key within the same CSV — last occurrence wins.",
            collection_name,
            duplicate_keys,
        )
    return documents, skipped


def _natural_key_from_dict(row_dict: dict[str, Any], key_cols: list[str]) -> str | None:
    """Build the composite natural key from a row dict; None if any part is missing."""
    parts: list[str] = []
    for col in key_cols:
        value = row_dict.get(col)
        if value is None or value is pd.NA:
            return None
        if isinstance(value, float) and math.isnan(value):
            return None
        parts.append(str(value))
    return "|".join(parts)


# --------------------------------------------------------------------------- #
# Atlas write path
# --------------------------------------------------------------------------- #
def get_mongo_uri(args_uri: str | None) -> str:
    """Resolve the connection string: --uri > MONGO_URI env/.env > error."""
    uri = args_uri or os.environ.get("MONGO_URI", "").strip()
    if not uri:
        raise SystemExit(
            "No MongoDB connection string found.\n"
            "Set MONGO_URI in the environment or in a .env file at the project root,\n"
            "or pass --uri (e.g. 'mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net')."
        )
    return uri


def load_collection(
    db: Any,
    collection_name: str,
    batch_size: int,
) -> dict[str, int]:
    """Upsert one collection. Returns {source, skipped, inserted, updated}."""
    documents, skipped = build_documents(collection_name)
    if not documents:
        logging.info(
            "'%s': 0 rows to write (skipped=%d) — nothing to do.",
            collection_name,
            skipped,
        )
        return {"collection": collection_name, "source": 0, "skipped": skipped,
                "inserted": 0, "updated": 0}

    from pymongo import ReplaceOne

    collection = db[collection_name]
    inserted = 0
    updated = 0

    for start in range(0, len(documents), batch_size):
        batch = documents[start : start + batch_size]
        result = collection.bulk_write(
            [ReplaceOne({"_id": doc["_id"]}, doc, upsert=True) for doc in batch],
            ordered=False,
        )
        inserted += result.upserted_count
        updated += result.matched_count

    logging.info(
        "'%s': %d rows | inserted=%d updated=%d skipped=%d",
        collection_name,
        len(documents),
        inserted,
        updated,
        skipped,
    )
    return {
        "collection": collection_name,
        "source": len(documents),
        "skipped": skipped,
        "inserted": inserted,
        "updated": updated,
    }


def dry_run_report(collection_names: Iterable[str]) -> dict[str, int]:
    """Validate + build documents for every collection without connecting."""
    summary: dict[str, int] = {"total_rows": 0, "total_skipped": 0}
    for name in collection_names:
        documents, skipped = build_documents(name)
        total = len(documents)
        summary["total_rows"] += total
        summary["total_skipped"] += skipped
        logging.info(
            "'%s': %d row(s) ready to upsert (skipped=%d)",
            name,
            total,
            skipped,
        )
        if documents:
            sample = {k: v for k, v in documents[0].items() if k != "_id"}
            sample["_id"] = documents[0]["_id"]
            logging.info("  first doc: %s", sample)
    return summary


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load data/*_cleaned.csv into MongoDB Atlas (idempotent upsert by natural key).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate schemas, build documents and report counts without connecting to Atlas.",
    )
    parser.add_argument(
        "--uri",
        default=None,
        help="MongoDB connection string (overrides MONGO_URI env var).",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("MONGO_DB", DEFAULT_DB_NAME),
        help=f"Target database name (default: {DEFAULT_DB_NAME}, or MONGO_DB env var).",
    )
    parser.add_argument(
        "--collections",
        default=None,
        help="Comma-separated subset of collections to load (default: all).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Documents per bulk_write batch (default: {DEFAULT_BATCH_SIZE}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    args = parse_args(argv)

    names = list(COLLECTIONS)
    if args.collections:
        requested = [c.strip() for c in args.collections.split(",") if c.strip()]
        unknown = [c for c in requested if c not in COLLECTIONS]
        if unknown:
            raise SystemExit(f"Unknown collection(s): {unknown}. Known: {names}")
        names = requested

    if args.dry_run:
        summary = dry_run_report(names)
        logging.info(
            "DRY RUN complete: %d collection(s), %d row(s) would be upserted, %d skipped.",
            len(names),
            summary["total_rows"],
            summary["total_skipped"],
        )
        return 0

    uri = get_mongo_uri(args.uri)
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
        # Fail fast if the cluster is unreachable / credentials are wrong.
        client.admin.command("ping")
        db = client[args.db]
        endpoint = uri.split("@", 1)[-1] if "@" in uri else "configured URI"
        logging.info("Connected to '%s' (db endpoint='%s').", args.db, endpoint)
    except PyMongoError as exc:
        logging.error("Could not connect to MongoDB Atlas: %s", exc)
        return 1

    summary = {"inserted": 0, "updated": 0}
    exit_code = 0
    for name in names:
        try:
            stats = load_collection(db, name, args.batch_size)
            summary["inserted"] += stats["inserted"]
            summary["updated"] += stats["updated"]
        except Exception as exc:  # noqa: BLE001 — one bad collection must not abort the rest
            logging.error("'%s' failed: %s", name, exc)
            exit_code = 1

    client.close()
    logging.info(
        "ETL finished: %d collection(s), %d inserted, %d updated (exit=%d).",
        len(names),
        summary["inserted"],
        summary["updated"],
        exit_code,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())