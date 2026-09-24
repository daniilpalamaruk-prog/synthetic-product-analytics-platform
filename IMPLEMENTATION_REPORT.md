# Implementation report

## 1. What existed before

A deterministic chunked SaaS generator, Parquet raw/clean/quarantine outputs, JSON contracts, broad DQ checks, ClickHouse staging/intermediate/ten marts, experiment statistics, historical FX/MRR/unit economics, business cases, benchmarks, and 24 passing tests. See `docs/CURRENT_STATE_AUDIT.md`.

## 2. What was added

Portable DWH execution, Greenplum MPP SQL/profile, incremental/idempotent batches, plan SCD2, common quarantine envelope, hard DQ gate, protected synthetic PII, RBAC, five Airflow DAGs, Superset specification, Compose profiles, CI, security review, generated business reports, portfolio README, and learning documentation.

## 3. Architecture

Parquet sources are orchestrated through contract validation and PII protection into raw → staging → core → marts. Critical DQ blocks publication; rejects are redacted; operational batches feed pipeline health. SQLite is the executable fallback and Greenplum is the optional MPP target. Existing ClickHouse SQL remains supported.

## 4. DWH

Core facts/dimensions have documented grains and keys. Plan history is SCD2 with exclusive validity bounds and exactly one current row. The acceptance database contained 1,000 users, 30,000 events, 342 payments, 434 experiment assignments, 1,154 plan-history rows, 357 product days, and 213 revenue days.

## 5. ETL / ELT

ETL normalizes and protects PII before storage. ELT performs warehouse normalization/aggregation. Watermarks are half-open; batches persist read/load/reject counts and status. Running batch `acceptance-001` twice retained exactly 30,000 fact events and one batch-health record.

## 6. Greenplum

DDL creates layer schemas, append-optimized column facts, `user_id` distribution, replicated small dimensions, and monthly event/payment partitions. SQL includes skew/Motion diagnostics, incremental anti-joins, SCD2 changes, partition checks, DQ gates, and an honest before/after optimization benchmark.

## 7. Airflow

Five TaskFlow-oriented DAGs cover event/billing ingestion, DWH, marts, and DQ. Schedules, catchup, retries, retry delay, timeouts, and maximum active runs are explicit/configurable. DAGs delegate to Python/SQL components. Backfill is documented with interval-safe commands.

## 8. Data Quality

Contracts, keys, nulls, enums, integrity, time, FX, freshness, volume, partitions, completeness, and SLA checks are retained. New warehouse gates cover duplicates, orphan facts, negative finance, and SCD2 current-state validity. Acceptance clean DQ had all data checks PASS and expected WARNs for deliberately simulated monitoring incidents.

## 9. Security

Synthetic names/emails/phones/IPs use reserved patterns. Email/phone normalization precedes HMAC-SHA256. Fernet provides optional authenticated encryption. Quarantine redacts contact data; marts have no raw PII; SQL roles enforce layer access. No real secrets are committed.

## 10. BI

Compose includes Superset and an idempotent bootstrap for Executive, Retention,
Acquisition, Experiments, and Incident dashboards over Greenplum marts. Ten
charts were rendered in Superset 4.1.1 and five real captures are committed
under `docs/images`.

## 11. Tests

The final automated result was **37 passed** from a fresh clone after literal
`make setup` and `make test` in Ubuntu WSL. Coverage includes existing
business/statistical/financial regressions plus contracts, HMAC/encryption/tamper
handling, incremental reruns, idempotency, SCD2, no-PII marts, Airflow source
contracts, Greenplum distribution/partition SQL, required artifacts, and
source-to-mart integration. The source repository and the Windows-side clean
clone both finished with a clean Git worktree (the clone's `.venv` is ignored).

## 12. Benchmarks

Measured generator benchmark on 2026-09-24: Windows 11, Python 3.14.3, 12 logical CPUs, 10,000 users, 400,000 events, chunk size 100,000. Runtime 12.639 s, 31,648 events/s, 36,256,362 Parquet bytes. Python/native peak memory was not measured. Source: `benchmarks/results/generator_2026-09-24.json`.

The real two-segment Greenplum run used 3,000,000 events. Five warm-cache
executions improved from a 107.077 ms median to 10.908 ms through monthly
partition pruning, `user_id` distribution, and user-day preaggregation.
Methodology and plans are in
`benchmarks/results/greenplum_query_optimization.md`.

## 13. How to run

Install requirements and the editable package, generate a dataset, run clean quality, set `PII_HMAC_SECRET`, then execute `python warehouse.py --input <dataset> --database <db>`. `pytest -q` verifies the portable path. Make targets expose generation, quality, warehouse, acceptance, Docker profiles, and benchmarks.

## 14. Limitations

All data/business effects are synthetic. The Docker profile is a single-host
educational environment, not a production capacity or HA claim. Airflow,
Greenplum, and Superset startup/health, Greenplum plans, Superset rendering,
and container restart were verified locally. KMS/HA/backups/network policy
remain out of scope.

## 15. Files changed

Key additions: `src/saasgen/warehouse.py`, `src/saasgen/contracts.py`, `src/saasgen/security`, `sql/greenplum`, `airflow`, `security/roles.sql`, `compose.yaml`, `bi/superset`, `analysis/business_cases.py`, `.github/workflows/ci.yml`, new tests, required docs, `SECURITY_REVIEW.md`, and this report. Generator/contracts gained explicitly synthetic PII. README/Makefile/ignore/dependency configuration were upgraded.

## 16. What this proves

The code demonstrates product analytics, experiment discipline, financial metric modeling, secure analytical ingestion, dimensional modeling/SCD2, incremental/idempotent processing, data-quality gates, MPP design, orchestration, BI semantic planning, testing, performance measurement, and honest operational limitations.
