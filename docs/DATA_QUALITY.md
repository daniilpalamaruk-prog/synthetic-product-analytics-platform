# Data quality

Quality is enforced at two boundaries. Source checks in `saasgen.quality` cover contracts, uniqueness, nulls, enums, referential integrity, timestamp ordering, FX reconciliation, freshness, volume, completeness, missing partitions, and synthetic SLA telemetry. Warehouse checks cover fact uniqueness, user foreign keys, non-negative finance, and exactly one current SCD2 row per user.

## Gate policy

- Hard fail: required contract/type/enum violations, duplicate business keys, orphan facts, negative finance, invalid SCD2 state. Marts are not rebuilt.
- Warning: moderate freshness or volume anomalies that do not invalidate facts. Publish may continue with an annotation.
- Quarantine: invalid source rows receive a safe/redacted envelope and are excluded from staging/core.

Raw data with intentionally injected defects is expected to WARN/FAIL; the clean layer should pass critical checks. Thresholds are configuration-driven. The SLA values are synthetic targets and do not describe an operating production service.

Verify with `python quality.py --input <dataset> --layer clean`, `pytest tests/test_warehouse.py -q`, and `sql/greenplum/ddl/05_data_quality_gate.sql`.
