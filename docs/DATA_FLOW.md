# Data flow and lineage

Each generated record starts in Parquet with a deterministic seed. Contracts validate source shape. User contact fields are normalized and HMAC-pseudonymized before warehouse load; reversible encrypted PII is stored only when `PII_ENCRYPTION_KEY` is supplied. Invalid data receives a redacted quarantine envelope.

Warehouse batches use `[watermark_from, watermark_to)`. Raw tables add `ingestion_timestamp`, `batch_id`, `source`, and `source_file`. Staging standardizes values and deduplicates. Core establishes dimensions/facts and plan SCD2. A critical DQ gate runs before marts. Batch metadata feeds `mart_pipeline_health`.

## Key lineage

| Metric | Source → warehouse → mart → BI |
|---|---|
| Revenue/ARPPU | payments Parquet → raw/stg payments → `fct_payments` → `mart_revenue_daily` → Executive |
| Activation | events/users → raw/stg → `fct_events` + `dim_users` → product/funnel marts → Product |
| Retention | events/users → core facts/dimension → retention cohort mart → Product |
| CAC | marketing spend + users → core → acquisition/unit economics mart → Acquisition |
| LTV | payments + users + generator gross margin/FX → core → cumulative contribution mart → Acquisition/Executive |
| Incident | events → `fct_events` → platform quality by Android/version/time → Incident |

The existing ClickHouse marts provide the detailed retention, MRR, and unit-economics calculations. Greenplum DDL supplies the production-shaped layer boundaries; additional mart SQL can be ported without changing metric definitions.
