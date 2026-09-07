"""
data_loader.py
----------------
Centralized data access layer for the Public Health Analytics Dashboard.

All raw data extracts are loaded and joined here so that page modules never
touch the filesystem directly. Streamlit's cache decorators are used to
avoid re-reading / re-joining data on every widget interaction.

Data source (Phase 1)
---------------------
When ``MONGO_URI`` is set (environment variable or ``.env`` file), all
tables are read from the MongoDB Atlas database populated by
``etl/load_to_atlas.py`` (collections named after each table, e.g.
``fact_disease_surveillance``). When it is not set, the app transparently
falls back to the cleaned CSV extracts in ``data/`` — so local development
and tests work with zero configuration.

Function signatures are stable: dashboards keep calling the same
``get_*_master()`` / ``load_raw_tables()`` helpers regardless of source.

Author : Analytics Engineering Team
Module : Public Health Surveillance Dashboard
"""

from pathlib import Path
import os
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Collection name -> cleaned CSV filename. Collection names double as the
# MongoDB collection names written by etl/load_to_atlas.py.
FILES = {
    "dim_dates": "dim_dates_cleaned.csv",
    "dim_disease": "dim_disease_cleaned.csv",
    "dim_program": "dim_program_cleaned.csv",
    "dim_source": "dim_source_cleaned.csv",
    "dim_state": "dim_state_cleaned.csv",
    "fact_outbreak": "fact_outbreak_cleaned.csv",
    "fact_surveillance": "fact_disease_surveillance_cleaned.csv",
    "fact_environmental": "fact_environmental_cleaned.csv",
    "fact_health_programs": "fact_health_programs_cleaned.csv",
    "fact_lab_healthcare": "fact_lab_healthcare_cleaned.csv",
}

# Mongo database name: MONGO_DB env var, else this default. Keep in sync
# with the default in etl/load_to_atlas.py.
DEFAULT_MONGO_DB = "healthsentinel"

# Keep the dashboard-facing key stable while matching the ETL collection name.
MONGO_COLLECTIONS = {
    "fact_surveillance": "fact_disease_surveillance",
}


# --------------------------------------------------------------------------- #
# Data source resolution
# --------------------------------------------------------------------------- #
def _mongo_uri() -> str | None:
    """Connection string from MONGO_URI env var, then st.secrets. None if unset."""
    uri = os.environ.get("MONGO_URI", "").strip()
    if uri:
        return uri
    try:
        return st.secrets.get("MONGO_URI", "") or None
    except Exception:
        return None


def _mongo_db_name() -> str:
    return os.environ.get("MONGO_DB", "").strip() or DEFAULT_MONGO_DB


def _read_table_mongo(collection: str) -> pd.DataFrame:
    """Read one collection from MongoDB Atlas into a DataFrame."""
    from pymongo import MongoClient

    client = MongoClient(_mongo_uri(), serverSelectionTimeoutMS=10_000)
    try:
        mongo_collection = MONGO_COLLECTIONS.get(collection, collection)
        docs = list(client[_mongo_db_name()][mongo_collection].find({}))
    finally:
        client.close()
    df = pd.DataFrame(docs)
    if "_id" in df.columns:
        df = df.drop(columns=["_id"])
    return df


def _read_table_csv(collection: str) -> pd.DataFrame:
    """Read one cleaned CSV extract into a DataFrame."""
    path = DATA_DIR / FILES[collection]
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


# --------------------------------------------------------------------------- #
# Raw dimension / fact loaders
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False, ttl=3600)
def load_raw_tables() -> dict[str, pd.DataFrame]:
    """Read every data extract into memory once and cache the result.

    Source is MongoDB Atlas when MONGO_URI is configured, otherwise the
    cleaned CSV extracts — same dict shape, same keys, either way.
    """
    use_mongo = bool(_mongo_uri())

    if use_mongo:
        try:
            tables = {key: _read_table_mongo(key) for key in FILES}
            empty = [k for k, df in tables.items() if df.empty]
            if empty:
                st.warning(
                    "MongoDB returned no documents for collection(s): "
                    + ", ".join(empty)
                    + ". Run `python etl/load_to_atlas.py` first, or unset MONGO_URI to use local CSVs."
                )
        except Exception as exc:  # noqa: BLE001 — degrade gracefully to CSV
            st.warning(
                f"Could not read from MongoDB Atlas ({exc}). "
                "Falling back to local CSV extracts in data/."
            )
            use_mongo = False

    if not use_mongo:
        tables = {key: _read_table_csv(key) for key in FILES}

    # Parse the date dimension once, up front.
    tables["dim_dates"]["full_date"] = pd.to_datetime(tables["dim_dates"]["full_date"])
    return tables


# --------------------------------------------------------------------------- #
# Star-schema joins -> flat analytical tables (one per subject area)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False, ttl=3600)
def get_surveillance_master() -> pd.DataFrame:
    """Disease surveillance fact joined with date / state / disease / source dims."""
    t = load_raw_tables()
    df = (
        t["fact_surveillance"]
        .merge(t["dim_dates"], on="date_id", how="left")
        .merge(t["dim_state"], on="state_id", how="left")
        .merge(t["dim_disease"], on="disease_id", how="left")
        .merge(t["dim_source"], on="source_id", how="left")
    )
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def get_outbreak_master() -> pd.DataFrame:
    """Outbreak fact joined with date / state / disease / source dims."""
    t = load_raw_tables()
    df = (
        t["fact_outbreak"]
        .merge(t["dim_dates"], on="date_id", how="left")
        .merge(t["dim_state"], on="state_id", how="left")
        .merge(t["dim_disease"], on="disease_id", how="left")
        .merge(t["dim_source"], on="source_id", how="left")
    )
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def get_environmental_master() -> pd.DataFrame:
    t = load_raw_tables()
    df = t["fact_environmental"].merge(t["dim_dates"], on="date_id", how="left").merge(
        t["dim_state"], on="state_id", how="left"
    )
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def get_programs_master() -> pd.DataFrame:
    t = load_raw_tables()
    df = (
        t["fact_health_programs"]
        .merge(t["dim_dates"], on="date_id", how="left")
        .merge(t["dim_state"], on="state_id", how="left")
        .merge(t["dim_program"], on="program_id", how="left")
    )
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def get_lab_master() -> pd.DataFrame:
    t = load_raw_tables()
    df = t["fact_lab_healthcare"].merge(t["dim_dates"], on="date_id", how="left").merge(
        t["dim_state"], on="state_id", how="left"
    )
    return df


# --------------------------------------------------------------------------- #
# Filter option helpers (used to populate sidebar widgets)
# --------------------------------------------------------------------------- #
def get_filter_options() -> dict:
    t = load_raw_tables()
    dates = t["dim_dates"]
    return {
        "states": sorted(t["dim_state"]["state_name"].dropna().unique().tolist()),
        "regions": sorted(t["dim_state"]["region"].dropna().unique().tolist()),
        "years": sorted(dates["year"].dropna().unique().tolist()),
        "months": list(
            dates.sort_values("month_num")["month_name"].drop_duplicates().values
        ),
        "diseases": sorted(t["dim_disease"]["disease_name"].dropna().unique().tolist()),
        "disease_categories": sorted(
            t["dim_disease"]["disease_category"].dropna().unique().tolist()
        ),
        "sources": sorted(t["dim_source"]["source_name"].dropna().unique().tolist()),
    }


def apply_common_filters(
    df: pd.DataFrame,
    states: list | None = None,
    regions: list | None = None,
    years: list | None = None,
    months: list | None = None,
    diseases: list | None = None,
    disease_categories: list | None = None,
    sources: list | None = None,
) -> pd.DataFrame:
    """Apply the sidebar filter selections to any joined master table."""
    out = df.copy()
    if states:
        out = out[out["state_name"].isin(states)]
    if regions and "region" in out.columns:
        out = out[out["region"].isin(regions)]
    if years:
        out = out[out["year"].isin(years)]
    if months:
        out = out[out["month_name"].isin(months)]
    if diseases and "disease_name" in out.columns:
        out = out[out["disease_name"].isin(diseases)]
    if disease_categories and "disease_category" in out.columns:
        out = out[out["disease_category"].isin(disease_categories)]
    if sources and "source_name" in out.columns:
        out = out[out["source_name"].isin(sources)]
    return out