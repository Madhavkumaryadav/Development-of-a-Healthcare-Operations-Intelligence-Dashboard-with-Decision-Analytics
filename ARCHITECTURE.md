# HealthSentinel Architecture

## Data flow

```text
Source CSVs / uploaded extracts
          |
          v
   raw_* Atlas collections  <-- every source row for the run
          |
          v
  ETL validation + cleaning
          |
          v
clean Atlas collections     <-- only collections read by the app
          |
          +--> Streamlit dashboards
          +--> ML outputs: forecast_results, anomaly_flags, risk_clusters
          +--> RAG chunks and feedback
```

`etl/sync_atlas_pipeline.py` creates the raw snapshot first, then cleans the
same snapshot and replaces the corresponding clean collection. The clean
collection names match the stable keys in `src/data_loader.py`.

## Security boundary

`app.py` calls `src.login.require_login()` before navigation. Passwords are
verified with salted scrypt hashes. Failed attempts are temporarily locked,
and the app provides an explicit sign-out action. Hashes can be supplied by
the ignored local sidecar or the `ADMIN_HASHES_JSON` deployment secret.

## Atlas collections

Operational data uses `dim_*` and `fact_*` names. Raw snapshots use the same
name with a `raw_` prefix. Generated collections are `forecast_results`,
`anomaly_flags`, `risk_clusters`, `rag_chunks`, and `feedback`.