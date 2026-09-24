# Repository audit (before the extension)

Audit date: 2026-09-24. Baseline command: `python -m pytest -q`; result: **24 passed in 17.23s**. The directory supplied for the task had no `.git` metadata, so commit history and tracked/untracked status could not be audited.

## Existing

- Entrypoints: `generate.py`, `quality.py`, `analysis/validate_patterns.py`, `analysis/experiment_analysis.py`, and benchmark scripts.
- Python package: deterministic, chunked PyArrow/Parquet generator under `src/saasgen`.
- Storage: partition-like Parquet parts in `raw`, `clean`, and `quarantine`; compact generated samples were present under `data/analytics_ready` and `sample/fx_release`.
- Sources/entities: users, sessions, events, subscriptions, payments, marketing spend, FX, experiments, assignments, catalog, releases, business timeline, configuration, and synthetic pipeline runs.
- Contracts: JSON Schema files plus SQL relationship checks.
- Quality: uniqueness, null, enum, referential integrity, timestamp, FX reconciliation, freshness, volume, partition, completeness, availability, duration, and SLA checks.
- Analytics: ClickHouse staging/intermediate SQL and ten marts; historical MRR movement and contribution-based unit economics.
- Experiments: mutually exclusive enrollment, SRM, confidence intervals, binary tests, user bootstrap for revenue, metric roles, and scoped Holm correction.
- Business cases: retention, onboarding, pricing, Android payment incident, and acquisition reallocation.
- Tests/CI: 24 tests existed; no CI workflow existed.
- Infrastructure: ClickHouse SQL existed; Docker, Airflow, Greenplum, Superset, RBAC, and DWH-layer orchestration did not.

## Reusable

- Generator behavior, seeds, scenario YAML, bounded chunks, Parquet writer, manifests, and synthetic monitoring.
- Existing business definitions in `docs/METRICS.md`, financial SQL, experiment analysis, contracts, and DQ checks.
- ClickHouse model as an independent analytics target; it is retained for backward compatibility.
- Existing business-pattern tests as regression protection for the intended synthetic story.

## Needs refactoring

- The architecture stopped at clean Parquet/ClickHouse and did not expose explicit raw/staging/core/marts warehouse ownership.
- Quarantine records carried issue labels but lacked a common batch/error envelope and explicit PII redaction contract.
- `pipeline_runs` simulated source reliability but did not record real local ETL batch execution.
- The Makefile covered only install/test/sample/quality/reports.
- Several Markdown files contained literal Unicode replacement characters, so portions of the prose were irrecoverable.
- The old README described the generator well but was not a portfolio-first guide to the requested end-to-end platform.

## Missing

- Greenplum DDL, distribution keys, monthly partitioning, skew diagnostics, and a reproducible optimization case.
- Incremental/idempotent warehouse loader, SCD2 implementation, and a hard DQ publication gate.
- PII normalization, keyed HMAC pseudonymization, authenticated encryption, no-PII mart tests, and SQL RBAC.
- Airflow DAGs, schedules, retries/timeouts, backfill documentation, and DAG tests.
- Superset deployment/specification and dashboard groups.
- Docker Compose profiles, GitHub Actions, security review, implementation report, and learning path.

## Risks

- Changing event/finance/experiment definitions could invalidate the strongest existing tests; those definitions were preserved.
- A mandatory local Greenplum cluster would make CI and Windows onboarding impractical; the design therefore adds Greenplum as an optional real profile and SQLite as the executable fallback.
- Adding plaintext PII to analytics outputs would create an avoidable leak; synthetic contact fields exist only to exercise protection and are excluded from warehouse marts.
- Rebuilding all history on each schedule would undermine incremental semantics; all production-shaped SQL uses half-open intervals and business-key guards.
- Generated datasets and Docker volumes can be large; only deterministic generation commands should be the source of truth.
