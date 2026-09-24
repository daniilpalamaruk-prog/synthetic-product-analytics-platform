# Historical backfill

Use case: the activation definition changes and daily product marts must be rebuilt for a historical range. DAGs have `catchup=True` where interval processing is meaningful, and warehouse predicates are half-open (`>= interval_start`, `< interval_end`). Business logic does not call `datetime.now()`.

Greenplum example:

```bash
psql "$GREENPLUM_DSN" -v ON_ERROR_STOP=1 \
  -v interval_start=2025-05-01T00:00:00Z \
  -v interval_end=2025-08-01T00:00:00Z \
  -f sql/greenplum/ddl/04_incremental_core.sql
psql "$GREENPLUM_DSN" -v ON_ERROR_STOP=1 \
  -v interval_start=2025-05-01T00:00:00Z \
  -v interval_end=2025-08-01T00:00:00Z \
  -f sql/greenplum/ddl/05_data_quality_gate.sql
```

Airflow example: `airflow dags backfill build_analytics_marts --start-date 2025-05-01 --end-date 2025-08-01`. Repeating an interval is safe because facts use business-key anti-joins and marts delete/reinsert only the requested partition range.
