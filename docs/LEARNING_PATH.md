# Guided learning path

Use a small clean dataset (`data/demo`) and set `PII_HMAC_SECRET` before warehouse steps.

## 1. Synthetic source data

Read: `config/*.yaml`, `src/saasgen/generator.py`. Run: `python generate.py --users 1000 --target-events 30000 --seed 42 --output data/demo --inject-data-quality-issues false`. Observe: deterministic Parquet tables and `manifest.json`. Key concept: correlated business simulation with bounded chunks.

## 2. Data contracts

Read: `contracts/*.schema.json`, `src/saasgen/contracts.py`. Run: `pytest tests/test_contracts.py -q`. Observe: schemas parse and invalid required fields fail. Key concept: explicit source expectations.

## 3. ETL

Read: `src/saasgen/security/pii.py`, `src/saasgen/warehouse.py`. Run: `python warehouse.py --input data/demo --database data/demo.db`. Observe: protected identifiers and batch metadata. Key concept: transform sensitive data before load.

## 4. Raw layer

Read: `sql/greenplum/ddl/01_raw.sql`. Run: query `raw_users` in SQLite or `raw.users` in Greenplum. Observe: ingestion fields and no open PII. Key concept: traceable, minimally transformed ingestion.

## 5. Staging

Read: `sql/greenplum/ddl/02_staging_core.sql`. Run: compare raw/staging counts. Observe: normalized/deduplicated records. Key concept: stable typed boundary.

## 6. Core DWH

Read: `docs/DWH.md`. Run: inspect `dim_users` and `fct_events`. Observe: declared grains and business keys. Key concept: reusable facts and dimensions.

## 7. SCD2

Read: `_apply_scd2` and `04_incremental_core.sql`. Run: `pytest tests/test_warehouse.py -q`. Observe: ordered plan versions and one current row. Key concept: valid-time history only where justified.

## 8. Incremental processing

Read: `BatchMetadata` and Greenplum half-open predicates. Run: repeat the same warehouse batch. Observe: unchanged counts and zero duplicates. Key concept: watermarks plus idempotency.

## 9. Greenplum distribution

Read: `docs/GREENPLUM.md`, `distribution/skew_diagnostics.sql`. Run: `make greenplum-up`, then the diagnostics. Observe: segment row counts and Motion in plans. Key concept: colocated joins versus redistribution.

## 10. Partitioning

Read: Greenplum raw/core DDL. Run: `partitioning/partition_checks.sql`. Observe: monthly children and partition pruning. Key concept: align time filters with partition keys.

## 11. Airflow orchestration

Read: `airflow/dags/synthetic_analytics.py`. Run: `pytest tests/test_airflow_contract.py -q` or `make airflow-up`. Observe: five DAGs and explicit dependencies. Key concept: thin orchestration around testable components.

## 12. Data quality

Read: `src/saasgen/quality.py`, `05_data_quality_gate.sql`. Run: `python quality.py --input data/demo --layer clean`. Observe: PASS/WARN/FAIL checks. Key concept: hard gates versus operational warnings.

## 13. Security / PII

Read: `docs/SECURITY.md`, `security/roles.sql`. Run: `pytest tests/test_security.py -q`. Observe: normalization, stable keyed hashes, encryption roundtrip, tamper rejection. Key concept: minimize, pseudonymize, encrypt, and authorize.

## 14. Analytics marts

Read: `sql/marts.sql` and `03_marts.sql`. Run: query `mart_revenue_daily` and `mart_product_daily`. Observe: business-ready grains only after DQ. Key concept: reusable semantic outputs.

## 15. Product analytics

Read: `docs/METRICS.md`, `analysis/validate_patterns.py`. Run: the pattern report command from README. Observe: activation, retention, channel quality, and incident patterns. Key concept: precise cohort/window definitions.

## 16. Experiments

Read: `analysis/experiment_analysis.py`, `docs/EXPERIMENTS.md`. Run: generate the experiment report. Observe: SRM, CI, p-values, role labels, and scoped corrections. Key concept: uncertainty-aware decisions.

## 17. Unit economics

Read: the `mart_unit_economics` section in `sql/marts.sql`. Run: the SQL on ClickHouse or inspect SQL tests. Observe: cumulative contribution LTV and first payback month. Key concept: historical FX and contribution, not a revenue shortcut.

## 18. Superset

Read: `bi/superset/dashboard_spec.yaml`. Run: `make bi-up`. Observe: a BI service ready to connect only to marts. Key concept: governed semantic consumption. Docker run remains environment-dependent.

## 19. Business cases

Read: `docs/business_cases` and `docs/BUSINESS_CASES.md`. Run: `python analysis/business_cases.py --input data/demo --output business_cases`. Observe: evidence-led incident, pricing, and acquisition reports. Key concept: recommendation follows measured synthetic evidence.

## 20. Performance optimization

Read: `benchmarks/query_optimization`. Run: its `psql` command on Greenplum. Observe: real before/after plans and timings. Key concept: pruning, preaggregation, distribution, and honest environment disclosure.
