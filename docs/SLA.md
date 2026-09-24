# Synthetic Pipeline SLA / Reliability Model

Это proposed operating model для портфолио, не утверждение о работающем production pipeline.

## Targets

| SLI | Target | Measurement |
|---|---|---|
| Daily mart availability | by 07:00 local | successful publish timestamp |
| Event freshness | < 1 hour | warehouse ingest time − source event time |
| Pipeline success | 99.5% rolling 30 days | successful scheduled runs / eligible runs |
| Contract validity | 100% clean rows | rejected rows go to quarantine |
| Completeness | ≥99% declared rows per daily run | actual event rows / source-manifest expected rows |
| Data availability | by 07:00 UTC | completed publish timestamp versus deadline |
| Pipeline duration | ≤45 minutes | completed_at − started_at |
| Allowed delay | ≤180 minutes | minutes after availability deadline |

## Severity and response

- FAIL: broken referential integrity above threshold, missing partition, negative revenue in clean, freshness >3h. Block publish; preserve prior mart snapshot.
- WARN: expected controlled defect, freshness 1–3h, volume outside rolling warning band. Publish with annotation if metrics remain safe.
- PASS: contract and threshold satisfied.

Suggested observability: row counts by partition, max event/ingest timestamp, rejected rate by rule, duration, retry count and source-to-mart reconciliation. Alert routing and on-call response are simulated design elements.

`quality.py` evaluates freshness from the manifest's logical run time and source watermark: ≤1h PASS, 1–3h WARN, >3h FAIL. Daily volume uses robust day-over-day log changes with median/MAD; detected anomalies are WARN and become FAIL when they exceed the configured frequency threshold. These are executable synthetic checks, not claims about an operating service.

Every generated run contains `clean/pipeline_runs`, `raw/pipeline_runs` and `monitoring_report.json`. The telemetry includes one controlled completeness event and one failed-then-recovered duration/availability incident so monitoring queries can find non-ideal behavior. Values are deterministic for config/version/seed and explicitly `simulated=true`.

`sql/quality/monitoring.sql` implements latest-event, late-record, table-freshness, missing-partition, volume and pipeline-SLA queries. `quality.py` provides the filesystem/Parquet equivalent.

## Recovery

Runs must be idempotent per logical date and seed/config hash. Keep raw immutable, rebuild clean and marts from raw, quarantine rejected records with rule/version, and backfill affected partitions after a fix. Target RPO is one source delivery; proposed RTO is 4 hours.
