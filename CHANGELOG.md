# Change Log

## Dashboard cleanup and report-grounded RAG

### `dashboards/00_Home.py`

- Audited navigation/landing behavior; no data charts or filter-dependent
  empty state needed on this page.
- Kept the existing shared styling and hero-only layout unchanged.

### `dashboards/0_Executive_Public_Health_Overview.py`

- Verified the page-level empty-state guard before KPI/chart rendering.
- Verified KPI values use the existing shared number formatter and chart
  palettes from `src/chart_colors.py`.

### `dashboards/1_Geographic_Environmental_Intelligence.py`

- Verified environmental and surveillance empty states after filtering.
- Verified risk visuals use shared heatmap/hotspot palettes and retain axis
  labels for the state-level views.

### `dashboards/2_Laboratory_Healthcare_Capacity.py`

- Verified the no-record filter guard prevents empty KPI calculations.
- Verified testing, vaccination, capacity, and laboratory charts use shared
  semantic palette constants and percentage labels.

### `dashboards/3_Outbreak_Monitoring_Forecasting.py`

- Corrected the standalone fallback loader to use the cleaned extracts rather
  than removed raw CSV paths.
- Preserved the existing empty-state guard before forecast calculations.

### `dashboards/4_Health_Programs_Population_Vulnerability.py`

- Verified the page-level empty-state guard before KPI/chart rendering.
- Verified category and vulnerability charts use shared palette constants.

### `dashboards/5_Upload_Custom_Analysis.py`

- Added date-range, state, disease/program, report-title, branding, and
  per-section checklist controls.
- Added scoped PDF generation plus a matching structured JSON artifact.
- Added automatic local report chunk indexing after every report.
- Added an empty-state message when selected report filters return no rows.

### `dashboards/6_Ask_HealthSentinel.py`

- Replaced the Atlas-dependent Q&A path with local report-file retrieval.
- Added cited report IDs/titles, honest no-match responses, and local thumbs/
  comment feedback logging.

## Validation

- Report payload, PDF, local vector index, and cited answer smoke-tested.
- Edited modules compile cleanly with Python and show no workspace diagnostics.