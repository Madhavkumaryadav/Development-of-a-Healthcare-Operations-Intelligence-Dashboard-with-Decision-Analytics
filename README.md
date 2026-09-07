# HealthSentinel

HealthSentinel is a Streamlit public-health analytics workspace for India. It
combines disease surveillance, environmental intelligence, laboratory and
healthcare capacity, outbreak monitoring, health-program performance,
custom reports, and report-grounded question answering.

The application uses a star-schema data model, a cleaning pipeline, optional
MongoDB Atlas storage, local PDF/JSON reports, and a local file-backed RAG
index. Dashboard data is never sent to an LLM unless a separate provider is
configured by the operator.

## Current Features

- Secure login screen with salted scrypt password verification.
- One active admin account stored as metadata plus a git-ignored hash file.
- Eight Streamlit pages with native navigation.
- Clean CSV fallback for local development.
- Optional MongoDB Atlas source for cleaned application collections.
- Raw-to-clean ETL pipeline with provenance snapshots.
- Idempotent Atlas loading by natural keys.
- Dashboard-specific top-left `Export PDF` controls.
- Selectable report charts and matching JSON report artifacts.
- Local report indexing for Ask HealthSentinel.
- Cited, report-grounded Q&A with honest no-match responses.
- Local Q&A feedback logging.
- ARIMA forecasts, anomaly flags, and KMeans risk clusters.
- Dockerfile, Docker Compose, health check, and deployment documentation.

## Dashboard Pages

| Page | Purpose |
|---|---|
| Home | Full-screen branded landing page and dashboard report bundle action |
| Executive Public Health Overview | Executive KPIs, disease surveillance, outcomes, alerts, and state comparisons |
| Geographic & Environmental Intelligence | Environmental risk, geographic patterns, and disease burden |
| Laboratory & Healthcare Capacity | Testing, positivity, vaccination, hospital, ICU, and laboratory performance |
| Outbreak Monitoring & Forecasting | Alerts, containment, outbreak patterns, and ARIMA forecasting |
| Health Programs & Population Vulnerability | Program coverage, reach, population structure, and vulnerability |
| Upload & Custom Analysis | Upload datasets, analyze them, generate scoped PDF/JSON reports, and review reports |
| Ask HealthSentinel | Ask questions using generated report excerpts only |

The app no longer has a global filter. Each dashboard owns its own filters.
Each data-backed dashboard has a top-left `Export PDF` button that uses the
currently filtered data and opens a chart-selection dialog.

## Project Layout

```text
app.py                         Streamlit entry point and page navigation
assets/                        Logos and Home hero image
dashboards/                    Streamlit dashboard pages
src/data_loader.py            Cached CSV/Atlas loading and star-schema joins
src/admin_auth.py             Scrypt password hashing and authentication
src/login.py                  Application-wide login gate
src/filters.py                Shared dashboard filters
src/kpis.py                   KPI calculations and formatting
src/styling.py                Shared visual components and CSS
src/chart_colors.py           Shared chart palette constants
src/report_generator.py       Dashboard PDF report dialog and chart builders
src/pdf_report.py             Custom dataset PDF generator
src/report_store.py           Local JSON report store, vectors, retrieval, feedback
src/dashboard_report_pipeline.py  Automatic dashboard snapshot generation
src/ml_pipeline.py            Forecasting, anomaly, and clustering jobs
etl/export_and_clean.py       Raw snapshot and CSV cleaning stage
etl/load_to_atlas.py          Clean CSV to Atlas loader
etl/sync_atlas_pipeline.py    Raw and clean Atlas collection sync
reports/                      Local generated reports and RAG index; git-ignored
data/                         Clean CSVs, account metadata, and review state
Dockerfile                    Production container image
docker-compose.yml            Local container orchestration
DEPLOYMENT.md                 Docker and free-host deployment procedure
ARCHITECTURE.md               System architecture and data flow
RAG_DESIGN.md                 Local report-grounded RAG design
RUNBOOK.md                    Operations troubleshooting guide
CHANGELOG.md                  Dashboard/report change log
```

## Requirements

- Python 3.12 or newer is recommended.
- Windows PowerShell, macOS/Linux shell, or Docker.
- Docker Desktop is required only for container deployment.
- MongoDB Atlas is optional for local CSV mode and required only when using
  Atlas-backed data.

## Local Setup

From the project root:

### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Start the app:

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

The app requires login before rendering dashboard content. The local account
metadata is in `data/admin_credentials.csv`; password hashes are stored in the
git-ignored `data/.admin_hashes.csv`.

## Admin Login

The current local account is intentionally not documented with its password in
this README. Passwords are never stored in plaintext and cannot be recovered
from scrypt hashes.

Check the account store:

```bash
python -m src.admin_auth check
```

Generate a fresh password for every account. The command prints each password
once and stores only hashes:

```bash
python -m src.admin_auth rotate
python -m src.admin_auth rotate --length 20
```

For deployment, provide `ADMIN_HASHES_JSON` through the platform secret store
instead of placing password hashes in a public repository or image.

## Data Flow

```text
Source CSVs
    |
    v
Raw snapshot files / raw_* Atlas collections
    |
    v
Validation and cleaning pipeline
    |
    v
Clean CSVs / clean Atlas collections
    |
    v
Streamlit dashboards and reports
    |
    v
Local report JSON chunks -> local vector index -> Ask HealthSentinel
```

The dashboard loader reads cleaned CSVs by default. When `MONGO_URI` is set,
it reads the corresponding clean Atlas collections and keeps the same public
function signatures and dashboard-facing table names.

## Raw-to-Clean Pipeline

The project keeps raw provenance separately from cleaned application data.
Raw snapshots are written to `data/raw_exports/` and are git-ignored.
`manifest.json` records whether each snapshot came from an original raw file,
a preserved raw snapshot, or a cleaned fallback where an original raw source
was unavailable.

Run the local preparation stage:

```bash
python etl/export_and_clean.py
```

Options:

```bash
python etl/export_and_clean.py --raw-only
python etl/export_and_clean.py --clean-only
```

Cleaning performs header/value trimming, date parsing, missing-key removal,
and duplicate natural-key removal. The available project data currently
produces 25,701 raw snapshot rows and 25,632 clean rows; the main reduction is
`fact_health_programs` from 6,981 raw rows to 6,912 clean rows.

## MongoDB Atlas

Create `.env` from `.env.example` and set:

```dotenv
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>
MONGO_DB=healthsentinel
```

Never commit `.env` or expose the URI in documentation, screenshots, or logs.

### Validate and load clean collections

```bash
python etl/load_to_atlas.py --dry-run
python etl/load_to_atlas.py
```

### Publish raw and clean collections

```bash
python etl/sync_atlas_pipeline.py --dry-run
python etl/sync_atlas_pipeline.py
```

The sync pipeline publishes raw snapshots under `raw_*` collection names and
clean application data under the normal names:

```text
raw_dim_state                    -> dim_state
raw_fact_health_programs         -> fact_health_programs
raw_fact_outbreak                -> fact_outbreak
...
```

The application reads only the clean collections. Atlas writes are safe to
rerun for the normal loader because documents use natural-key `_id` values.
The sync pipeline replaces each raw snapshot and clean collection for the run.

Load a subset with the normal loader:

```bash
python etl/load_to_atlas.py --collections dim_state,fact_outbreak
```

## Custom PDF and JSON Reports

The Upload & Custom Analysis page supports CSV and Excel files. After loading a
dataset, choose:

- Date range, when a date column is detected.
- States, when a state-like categorical column is detected.
- Disease/program subject values, when available.
- Report title and organisation/branding text.
- Individual report sections.

The selected rows are used consistently for the on-screen analysis, PDF, and
JSON artifact. The generated files contain:

```text
report_title
branding
filters
generated_at
sections
report_id
```

Generated report artifacts are stored locally under `reports/` and can also be
downloaded from the page. Dashboard PDF reports use the top-left `Export PDF`
action and allow chart selection before compilation.

## Local Report-Grounded RAG

`src/report_store.py` provides a local file-backed report index:

```text
reports/*.json       Structured report artifacts
reports/*.pdf        Matching report PDFs
reports/rag_index.json   Indexed report chunks and embeddings
reports/feedback.jsonl   Q&A feedback records
```

Every generated report is split into section chunks and indexed. The Ask
HealthSentinel page searches across all generated report chunks and displays
the report title, report ID, excerpt, and similarity score.

The answer guardrail is:

> Answer only using the provided report excerpts. If they don't contain the
> answer, say so explicitly - do not guess or use outside knowledge.

An unrelated question returns:

```text
I don't have that in any generated report yet.
```

The default embedding is deterministic and local, so no paid API is required.
To use a local sentence-transformers model, install the optional package and
set:

```dotenv
REPORT_EMBEDDING_MODEL=all-MiniLM-L6-v2
```

This is retrieval/indexing, not model training or fine-tuning.

## ML Jobs

Run the local ML pipeline:

```bash
python -m src.ml_pipeline
```

It produces:

- Six-period ARIMA case forecasts in `forecast_results` when Atlas is set.
- IQR-based anomaly flags in `anomaly_flags`.
- KMeans state risk clusters in `risk_clusters`.

Without `MONGO_URI`, the command runs locally and prints record counts.

## Docker

The image runs Streamlit as an unprivileged `appuser`, includes a health check,
and does not copy `.env` into the image.

Check Docker:

```powershell
docker --version
docker compose version
docker info
```

Start locally:

```powershell
docker compose build --pull
docker compose up -d
docker compose ps
```

Open `http://localhost:8501`. Check health at:

```text
http://localhost:8501/_stcore/health
```

Useful commands:

```powershell
docker compose logs -f healthsentinel
docker compose restart healthsentinel
docker compose down
```

For the full Streamlit Community Cloud, Docker host, and Hugging Face
procedure, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Verification

Compile the project:

```powershell
$sourceFiles = Get-ChildItem src -Filter '*.py' | ForEach-Object { $_.FullName }
$dashboardFiles = Get-ChildItem dashboards -Filter '*.py' | ForEach-Object { $_.FullName }
& .\venv\Scripts\python.exe -m py_compile app.py $sourceFiles $dashboardFiles
```

Validate cleaned ETL input:

```powershell
python etl/load_to_atlas.py --dry-run
```

Check login security:

```powershell
python -m src.admin_auth check
```

The dashboard test suite has been run through the real multipage app context;
all eight pages render with zero Streamlit exceptions.

## Security Notes

- Rotate the MongoDB password if it has ever been exposed in chat, source,
  screenshots, or logs.
- Never commit `.env`, `data/.admin_hashes.csv`, `reports/`, databases, or raw
  exports.
- Use a least-privilege Atlas database user.
- Do not place plaintext admin passwords in CSV files or deployment images.
- Keep Atlas Network Access restricted to the deployment environment whenever
  possible.
- Use the login gate before exposing the application publicly.
