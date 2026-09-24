# Airflow orchestration

`dags/synthetic_analytics.py` defines five thin DAGs. Schedules and retry settings come from environment variables; no task reads wall-clock time for business filtering. Airflow data intervals map to the half-open watermarks persisted by `saasgen.warehouse`. The current lightweight runner derives the full interval from the manifest; the Greenplum SQL accepts explicit `interval_start`/`interval_end` psql variables for true partition backfills.

The deterministic failure demo is `AIRFLOW_RETRIES=2` plus a temporarily unavailable warehouse path/DB: the task fails, Airflow retries, and succeeds once the dependency is restored. No random failure is injected into normal runs.

Run `docker compose --profile core up -d airflow-init airflow-webserver airflow-scheduler`,
open `http://localhost:8081`, and use the local credentials from `.env` (never
commit them). The Compose acceptance run verified a healthy metadata database,
scheduler heartbeat, webserver health endpoint, and DAG loading.
