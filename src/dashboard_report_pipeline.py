"""Generate and index automatic snapshots for data-backed dashboards."""

from __future__ import annotations

import io
import threading
import zipfile
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from src.data_loader import (
    get_environmental_master,
    get_lab_master,
    get_outbreak_master,
    get_programs_master,
    get_surveillance_master,
)
from src.pdf_report import build_pdf_report
from src.report_store import REPORTS_DIR, build_report_payload, save_report_artifacts

SNAPSHOT_DIR = REPORTS_DIR / "dashboard_snapshots"
_generation_lock = threading.Lock()
_generation_started = False

SNAPSHOTS: dict[str, tuple[str, Callable[[], pd.DataFrame]]] = {
    "executive-public-health-overview": ("Executive Public Health Overview", get_surveillance_master),
    "geographic-environmental-intelligence": ("Geographic & Environmental Intelligence", get_environmental_master),
    "laboratory-healthcare-capacity": ("Laboratory & Healthcare Capacity", get_lab_master),
    "outbreak-monitoring-forecasting": ("Outbreak Monitoring & Forecasting", get_outbreak_master),
    "health-programs-population-vulnerability": ("Health Programs & Population Vulnerability", get_programs_master),
}


def _classify(frame: pd.DataFrame) -> tuple[list[str], list[str], str | None]:
    """Find report-compatible numeric, categorical, and date columns."""
    numeric = frame.select_dtypes(include="number").columns.tolist()
    datetime_col = next((column for column in frame.columns if pd.api.types.is_datetime64_any_dtype(frame[column])), None)
    if datetime_col is None:
        for column in frame.select_dtypes(include="object").columns:
            parsed = pd.to_datetime(frame[column], errors="coerce")
            if parsed.notna().mean() > 0.85:
                frame[column] = parsed
                datetime_col = column
                break
    categorical = [column for column in frame.select_dtypes(exclude="number").columns if column != datetime_col]
    return numeric[:8], categorical[:8], datetime_col


def _snapshot_payload(slug: str, title: str, frame: pd.DataFrame) -> tuple[dict[str, Any], bytes]:
    """Create a stable dashboard report payload and PDF."""
    numeric, categorical, date_column = _classify(frame)
    frame = frame.copy()
    if date_column:
        frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
    payload = build_report_payload(
        frame, title, "HealthSentinel automatic dashboard snapshot",
        {"dashboard": title, "scope": "current clean dataset"},
        ["overview", "insights", "numeric_summary", "distributions", "correlation", "category_comparison", "trend"],
        numeric, categorical, date_column,
        [f"{len(frame):,} clean records are available in the {title} dataset."],
    )
    payload["report_id"] = f"dashboard-{slug}"
    pdf = build_pdf_report(
        frame, f"{slug}.csv", numeric, categorical, date_column,
        [f"{len(frame):,} clean records are available in the {title} dataset."],
        report_title=title, branding="HealthSentinel automatic dashboard snapshot",
        sections=list(payload["sections"]),
    )
    return payload, pdf


def generate_dashboard_reports() -> list[Path]:
    """Generate one PDF/JSON snapshot per data-backed dashboard and index it."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for slug, (title, loader) in SNAPSHOTS.items():
        frame = loader()
        if frame.empty:
            continue
        payload, pdf = _snapshot_payload(slug, title, frame)
        pdf_path, json_path = save_report_artifacts(payload, pdf, f"dashboard_{slug}")
        paths.extend([pdf_path, json_path])
    return paths


def _background_generate_dashboard_reports() -> None:
    """Generate dashboard snapshots without writing Streamlit UI output."""
    try:
        with _generation_lock:
            generate_dashboard_reports()
    except Exception:
        # Background preparation must never prevent the dashboard from opening.
        return


def start_background_report_generation() -> None:
    """Start one non-blocking dashboard snapshot job per Python process."""
    global _generation_started
    if _generation_started:
        return
    _generation_started = True
    threading.Thread(
        target=_background_generate_dashboard_reports,
        name="healthsentinel-report-indexer",
        daemon=True,
    ).start()


def build_dashboard_report_bundle() -> bytes:
    """Return all generated dashboard PDF and JSON snapshots as a ZIP file."""
    generate_dashboard_reports()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(REPORTS_DIR.glob("dashboard_*.pdf")) + sorted(REPORTS_DIR.glob("dashboard_*.json")):
            archive.write(path, path.name)
    return output.getvalue()