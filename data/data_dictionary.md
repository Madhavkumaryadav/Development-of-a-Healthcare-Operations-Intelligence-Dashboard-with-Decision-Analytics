# Public Health Surveillance Dashboard — Data Dictionary

## Schema type: Star Schema
5 conformed dimensions shared across 5 fact tables (one fact table family per
dashboard focus area). All fact tables reference `dim_date` and `dim_state`;
disease-level facts additionally reference `dim_disease`.

## Dimension Tables

### dim_date (36 rows — Jan 2022 to Dec 2024, monthly grain)
| Column | Type | Description |
|---|---|---|
| date_id | INT (PK) | Surrogate key |
| full_date | DATE | First of month, ISO format |
| year | INT | 2022–2024 |
| month_num | INT | 1–12 |
| month_name | TEXT | January–December |
| quarter | TEXT | Q1–Q4 |
| year_month | TEXT | e.g. 2023-07 |

### dim_state (32 rows — Indian states & UTs)
| Column | Type | Description |
|---|---|---|
| state_id | INT (PK) | Surrogate key |
| state_name | TEXT | State/UT name |
| region | TEXT | North/South/East/West/Central/Northeast |
| latitude / longitude | FLOAT | For map visuals |
| population | INT | Approx. population |
| area_sq_km | INT | Land area |
| **Known issues** | | 1 row has trailing whitespace in `region`; 1 row has a null `population` (intentional — see Data Quality Notes) |

### dim_disease (12 rows)
| Column | Type | Description |
|---|---|---|
| disease_id | INT (PK) | Surrogate key |
| disease_name | TEXT | e.g. COVID-19, Dengue, Tuberculosis |
| disease_category | TEXT | Infectious / Vector-Borne / Water-Borne / Zoonotic / Non-Communicable |

### dim_source (6 rows)
| Column | Type | Description |
|---|---|---|
| source_id | INT (PK) | Surrogate key |
| source_name | TEXT | Hospital Report, Laboratory Report, Community Health Worker, Sentinel Surveillance Site, Self-Reported (App), NGO/Field Survey |

### dim_program (6 rows)
| Column | Type | Description |
|---|---|---|
| program_id | INT (PK) | Surrogate key |
| program_name | TEXT | National health program names |

## Fact Tables

### fact_disease_surveillance (~13,962 rows) — powers Dashboard 1 & feeds 2/4
Grain: date x state x disease
Key columns: total_reported_cases, active_cases, recovered_cases, deaths,
urban_cases, rural_cases, hospitalized_cases, icu_admissions,
case_fatality_rate, recovery_rate, public_health_risk_score,
population_under_surveillance, report_date_raw (messy duplicate of date_id
in mixed text formats — for a data-cleaning exercise).

### fact_environmental (~1,169 rows) — powers Dashboard 2
Grain: date x state
Key columns: aqi, rainfall_mm, temperature_c, water_quality_index,
sanitation_coverage_pct, healthcare_accessibility_score,
mosquito_breeding_index, zoonotic_disease_incidence, geographic_risk_score,
environmental_risk_score, case_rate_per_100k, hotspot_flag.

### fact_lab_healthcare (~1,163 rows) — powers Dashboard 3
Grain: date x state
Key columns: total_tests, positive_tests, positivity_rate,
vaccination_coverage_pct, booster_coverage_pct, hospital_beds, doctors,
phc_count, chc_count, icu_utilization_pct, bed_occupancy_pct,
reporting_compliance_pct, turnaround_time_days, reporting_rate_pct.

### fact_outbreak (~2,530 rows) — powers Dashboard 4
Grain: one row per outbreak event
Key columns: new_outbreak_flag, controlled_flag, containment_rate_pct,
response_time_hours, alert_level, predicted_cases, historical_cases,
forecast_accuracy_pct, hospital_readiness_score, resource_readiness_score,
emergency_alert_flag, state_name_raw (free-text state field simulating an
un-normalized source extract — must be reconciled to state_id during
cleaning).

### fact_health_programs (~6,981 rows) — powers Dashboard 5
Grain: date x state x program
Key columns: program_coverage_pct, people_screened, beneficiaries_reached,
maternal_health_beneficiaries, child_immunization_count,
children_population, adults_population, elderly_population,
high_risk_individuals, chronic_disease_patients, health_vulnerability_index,
socioeconomic_score.

## Data Quality Issues Deliberately Injected (for the cleaning exercise)

| Issue type | Where | Approx. rate |
|---|---|---|
| Missing values (nulls) | Multiple measure columns across all 5 fact tables | 3–4% per targeted column |
| Duplicate rows (same key repeated) | All fact tables | 1.0–1.5% of rows |
| Numeric fields stored as text placeholders (`N/A`, `unknown`, `-`, `?`) | hospitalized_cases, total_tests | ~1% |
| Negative values on inherently non-negative measures | deaths, active_cases, doctors, high_risk_individuals | ~0.4–0.5% |
| Percentages exceeding 100% | case_fatality_rate, recovery_rate, icu_utilization_pct, bed_occupancy_pct, program_coverage_pct | ~0.4–0.6% |
| Outlier spikes (3–6x max) | aqi, response_time_hours | ~0.5–0.6% |
| Inconsistent categorical casing/whitespace | alert_level, hotspot_flag/boolean columns, dim_state.region | 4–5% |
| Inconsistent boolean encodings (Yes/YES/Y/1/TRUE mixed with No/NO/N/0/FALSE) | hotspot_flag, new_outbreak_flag, controlled_flag, emergency_alert_flag | Throughout |
| Mixed date formats in a free-text column (ISO, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY) | fact_disease_surveillance.report_date_raw | ~10% |
| Un-normalized free-text dimension value needing reconciliation to surrogate key | fact_outbreak.state_name_raw | Throughout (case/typo variants on ~6%) |

## Suggested Cleaning Steps
1. Standardize categorical text (trim whitespace, normalize case) — `alert_level`, `region`, boolean flag columns.
2. Map all boolean-like values to a single Yes/No or 1/0 standard.
3. Parse `report_date_raw` and `state_name_raw` back to their canonical `date_id` / `state_id` and drop the raw columns once validated.
4. Convert placeholder text (`N/A`, `unknown`, `-`, `?`) to true nulls, then decide an imputation or exclusion strategy.
5. Cap/flag percentage fields at 0–100; investigate and correct or null any value outside that range.
6. Flag and correct/remove negative values on count-based measures.
7. Investigate statistical outliers (e.g., AQI > 3x the 95th percentile, response_time_hours > 200) before deciding to cap, winsorize, or remove.
8. De-duplicate on natural business key (date_id + state_id + disease_id/program_id, or outbreak_id) — keep first occurrence, log removed count.
9. Re-validate referential integrity (all foreign keys resolve to a valid dimension row) after cleaning.
