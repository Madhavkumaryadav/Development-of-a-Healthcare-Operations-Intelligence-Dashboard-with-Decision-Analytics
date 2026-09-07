"""Small, reproducible ML jobs for outbreak and vulnerability outputs."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def forecast_cases(outbreaks: pd.DataFrame, periods: int = 6) -> pd.DataFrame:
    """Forecast aggregate monthly historical cases with an ARIMA baseline."""
    frame = outbreaks.copy()
    if "year_month" in frame:
        frame["month"] = pd.to_datetime(frame["year_month"] + "-01", errors="coerce")
    else:
        frame["month"] = pd.to_datetime(frame["full_date"], errors="coerce")
    frame = frame.dropna(subset=["month", "historical_cases"])
    series = frame.groupby("month")["historical_cases"].sum().sort_index()
    if series.empty:
        return pd.DataFrame(columns=["month", "forecast_cases"])
    if len(series) < 4:
        values = [float(series.iloc[-1])] * periods
    else:
        try:
            model = ARIMA(np.log1p(series), order=(1, 1, 1)).fit()
            values = np.maximum(np.expm1(model.forecast(periods)), 0).tolist()
        except Exception:
            values = [float(series.tail(3).mean())] * periods
    dates = pd.date_range(series.index[-1] + pd.DateOffset(months=1), periods=periods, freq="MS")
    return pd.DataFrame({"month": dates, "forecast_cases": np.round(values).astype(int)})


def detect_anomalies(outbreaks: pd.DataFrame) -> pd.DataFrame:
    """Flag unusually large case counts using a robust IQR rule."""
    values = pd.to_numeric(outbreaks["historical_cases"], errors="coerce")
    q1, q3 = values.quantile([0.25, 0.75])
    limit = q3 + 1.5 * (q3 - q1)
    result = outbreaks[["outbreak_id", "state_id", "date_id", "historical_cases"]].copy()
    result["anomaly_flag"] = values > limit
    result["anomaly_threshold"] = limit
    return result[result["anomaly_flag"]].reset_index(drop=True)


def cluster_risk(programs: pd.DataFrame, clusters: int = 3) -> pd.DataFrame:
    """Segment states by vulnerability and coverage using KMeans."""
    from sklearn.cluster import KMeans

    fields = ["health_vulnerability_index", "program_coverage_pct", "socioeconomic_score"]
    grouped = programs.groupby("state_id", as_index=False)[fields].mean().dropna()
    if grouped.empty:
        return grouped.assign(risk_cluster=pd.Series(dtype=int))
    model = KMeans(n_clusters=min(clusters, len(grouped)), random_state=42, n_init=10)
    grouped["risk_cluster"] = model.fit_predict(grouped[fields])
    return grouped


def write_outputs(collections: dict[str, pd.DataFrame]) -> None:
    """Replace generated result collections in Atlas when configured."""
    uri = os.environ.get("MONGO_URI", "").strip()
    if not uri:
        return
    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        db = client[os.environ.get("MONGO_DB", "healthsentinel")]
        for name, frame in collections.items():
            docs = frame.replace({np.nan: None}).to_dict("records")
            if docs:
                db[name].delete_many({})
                db[name].insert_many(docs)
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HealthSentinel ML outputs.")
    parser.add_argument("--periods", type=int, default=6)
    args = parser.parse_args()
    outbreaks = pd.read_csv(DATA_DIR / "fact_outbreak_cleaned.csv")
    dates = pd.read_csv(DATA_DIR / "dim_dates_cleaned.csv")[["date_id", "full_date"]]
    outbreaks = outbreaks.merge(dates, on="date_id", how="left")
    programs = pd.read_csv(DATA_DIR / "fact_health_programs_cleaned.csv")
    outputs = {
        "forecast_results": forecast_cases(outbreaks, args.periods),
        "anomaly_flags": detect_anomalies(outbreaks),
        "risk_clusters": cluster_risk(programs),
    }
    write_outputs(outputs)
    for name, frame in outputs.items():
        print(f"{name}: {len(frame)} record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())