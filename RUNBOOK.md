# Operations Runbook

## ETL failure

Run `python etl/sync_atlas_pipeline.py --dry-run`. Inspect the first failing
table, correct its source schema, and rerun. Raw snapshots remain available
locally under `data/raw_exports/`.

## Atlas capacity

Check collection counts and remove obsolete raw snapshots only after retaining
an external archive. Keep only the latest raw run on M0 and avoid storing PDF
binary data in Atlas.

## Authentication incident

Rotate admin passwords with `python -m src.admin_auth rotate`, update
`ADMIN_HASHES_JSON` or the protected sidecar, and restart the deployment.
Rotate MongoDB credentials separately in Atlas if exposed.

## RAG provider exhaustion

The page remains grounded and refuses to guess when no LLM provider is
available. Continue using dashboard data, or switch providers through
deployment secrets after checking current free-tier limits.