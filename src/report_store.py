"""Local report artifacts and report-grounded retrieval.

Reports are stored as JSON plus PDF bytes in ``reports/``. The vector index is
file-backed and deliberately has no network or database dependency. When
``sentence-transformers`` is installed it uses the local model configured by
``REPORT_EMBEDDING_MODEL``; otherwise a deterministic TF-IDF embedding keeps
the workflow usable in the lightweight project environment.
"""

from __future__ import annotations

import hashlib
import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
INDEX_PATH = REPORTS_DIR / "rag_index.json"
FEEDBACK_PATH = REPORTS_DIR / "feedback.jsonl"
GROUNDING_INSTRUCTION = (
    "Answer only using the provided report excerpts. If they don't contain "
    "the answer, say so explicitly - do not guess or use outside knowledge."
)


def _json_value(value: Any) -> Any:
    """Convert pandas/numpy values into JSON-safe values."""
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if pd.isna(value):
        return None
    return value


def build_report_payload(
    df: pd.DataFrame,
    title: str,
    branding: str,
    filters: dict[str, Any],
    sections: list[str],
    numeric_cols: list[str],
    categorical_cols: list[str],
    datetime_col: str | None,
    insights: list[str],
) -> dict[str, Any]:
    """Build the structured report contract consumed by PDF and RAG code."""
    data: dict[str, Any] = {
        "overview": {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "numeric_fields": len(numeric_cols),
            "categorical_fields": len(categorical_cols),
            "date_field": datetime_col,
            "missing_percent": round(float(df.isna().mean().mean() * 100), 2),
        }
    }
    if "insights" in sections:
        data["insights"] = {"items": [str(item) for item in insights]}
    if "numeric_summary" in sections and numeric_cols:
        summary = df[numeric_cols].describe().T[["count", "mean", "std", "min", "max"]].round(2)
        data["numeric_summary"] = {
            str(index): {str(key): _json_value(value) for key, value in row.items()}
            for index, row in summary.iterrows()
        }
    if "distributions" in sections and numeric_cols:
        data["distributions"] = {
            column: {
                "count": int(df[column].count()),
                "min": _json_value(df[column].min()),
                "max": _json_value(df[column].max()),
                "mean": _json_value(round(float(df[column].mean()), 4)),
            }
            for column in numeric_cols[:4]
        }
    if "correlation" in sections and len(numeric_cols) >= 2:
        data["correlation"] = df[numeric_cols].corr().round(2).to_dict()
    if "category_comparison" in sections and categorical_cols and numeric_cols:
        category = categorical_cols[0]
        metric = numeric_cols[0]
        grouped = df.groupby(category)[metric].agg(["count", "mean", "std"]).sort_values("count", ascending=False).head(10)
        data["category_comparison"] = {
            "category": category,
            "metric": metric,
            "groups": {
                str(index): {key: _json_value(value) for key, value in row.items()}
                for index, row in grouped.iterrows()
            },
        }
    if "trend" in sections and datetime_col and numeric_cols:
        metric = numeric_cols[0]
        trend = df[[datetime_col, metric]].dropna().sort_values(datetime_col)
        trend = trend.groupby(pd.Grouper(key=datetime_col, freq="MS"))[metric].mean().dropna()
        data["trend"] = {str(index.date()): _json_value(value) for index, value in trend.items()}
    return {
        "report_id": hashlib.sha256(f"{title}|{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:16],
        "report_title": title,
        "branding": branding,
        "filters": filters,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": data,
    }


def save_report_artifacts(payload: dict[str, Any], pdf_bytes: bytes, filename_stem: str) -> tuple[Path, Path]:
    """Save a generated PDF and its matching JSON artifact."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename_stem).strip(".") or "report"
    pdf_path = REPORTS_DIR / f"{safe_stem}.pdf"
    json_path = REPORTS_DIR / f"{safe_stem}.json"
    pdf_path.write_bytes(pdf_bytes)
    json_path.write_text(json.dumps(payload, indent=2, default=_json_value), encoding="utf-8")
    index_report(payload)
    return pdf_path, json_path


def _embed(texts: list[str]) -> list[list[float]]:
    """Embed text locally, using sentence-transformers or TF-IDF fallback."""
    model_name = os.environ.get("REPORT_EMBEDDING_MODEL", "").strip()
    if model_name:
        try:
            from sentence_transformers import SentenceTransformer
            return SentenceTransformer(model_name).encode(texts, normalize_embeddings=True).tolist()
        except ImportError:
            pass
    vectors = []
    for text in texts:
        vector = np.zeros(512, dtype=float)
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            vector[int.from_bytes(digest[:2], "big") % 512] += 1.0
        norm = np.linalg.norm(vector)
        vectors.append((vector / norm if norm else vector).tolist())
    return vectors


def _chunks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn each report section into one concise searchable chunk."""
    prefix = f"Report '{payload['report_title']}' filters: {json.dumps(payload['filters'], default=_json_value)}."
    return [{"report_id": payload["report_id"], "chunk_text": prefix + f" Section {name}: {json.dumps(value, default=_json_value)}", "filters": payload["filters"], "generated_at": payload["generated_at"], "report_title": payload["report_title"]} for name, value in payload["sections"].items()]


def index_report(payload: dict[str, Any]) -> None:
    """Append report chunks to the local JSON vector index."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    existing = json.loads(INDEX_PATH.read_text(encoding="utf-8")) if INDEX_PATH.exists() else []
    existing = [item for item in existing if item["report_id"] != payload["report_id"]]
    chunks = _chunks(payload)
    vectors = _embed([item["chunk_text"] for item in chunks])
    for item, vector in zip(chunks, vectors):
        item["embedding"] = vector
    INDEX_PATH.write_text(json.dumps(existing + chunks, default=_json_value), encoding="utf-8")


def search_reports(question: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Return the most similar indexed report chunks using cosine similarity."""
    if not INDEX_PATH.exists():
        return []
    rows = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    if not rows:
        return []
    query_vector = np.asarray(_embed([question])[0], dtype=float)
    scored = []
    for row in rows:
        vector = np.asarray(row["embedding"], dtype=float)
        score = float(np.dot(query_vector, vector) / (np.linalg.norm(query_vector) * np.linalg.norm(vector) or 1))
        scored.append((score, row))
    return [dict(row, score=round(score, 4)) for score, row in sorted(scored, reverse=True, key=lambda pair: pair[0])[:top_k]]


def answer_from_reports(question: str, top_k: int = 5) -> dict[str, Any]:
    """Answer extractively from matching report chunks without outside knowledge."""
    matches = search_reports(question, top_k)
    stop_words = {"what", "which", "where", "when", "how", "many", "much", "does", "did", "is", "are", "the", "a", "an", "of", "in", "for", "to", "from", "this", "that", "report", "reports", "data", "dataset"}
    words = set(re.findall(r"[a-z0-9]+", question.lower())) - stop_words
    useful = [
        row for row in matches
        if row.get("score", 0) >= 0.30
        and words.intersection(set(re.findall(r"[a-z0-9]+", row["chunk_text"].lower())))
    ]
    if not useful:
        return {"answer": "I don't have that in any generated report yet.", "sources": []}
    answer = f"{GROUNDING_INSTRUCTION}\n\nBased on the generated report excerpts:\n\n" + "\n\n".join(f"- {row['chunk_text']}" for row in useful[:3])
    return {"answer": answer, "sources": useful[:3]}


def save_feedback(question: str, answer: str, reports_used: list[dict[str, Any]], rating: str, comment: str) -> None:
    """Append local Q&A feedback as one JSON object per line."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    record = {"question": question, "answer": answer, "reports_used": [row.get("report_id") for row in reports_used], "rating": rating, "comment": comment, "timestamp": datetime.now(timezone.utc).isoformat()}
    with FEEDBACK_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")