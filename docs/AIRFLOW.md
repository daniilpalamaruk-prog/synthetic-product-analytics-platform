# Apache Airflow

Airflow is the orchestrator, not the business-logic layer. `airflow/dags/synthetic_analytics.py` calls the existing quality and warehouse modules.

| DAG | Schedule default | Purpose |
|---|---|---|
| ingest_events | hourly | validate, protect, and incrementally load events |
| ingest_billing | hourly at :15 | validate, protect, and load billing |
| build_dwh | triggered | staging/core build and critical DQ |
| build_analytics_marts | daily 06:00 | interval rebuild, DQ, publish |
| data_quality | hourly at :30 | contracts/integrity/freshness/volume |

Schedules, retries, retry delay, and timeout are environment-configurable. Catchup is enabled for interval-oriented DAGs; `max_active_runs=1` prevents overlapping writes in the lightweight database. The deterministic retry demo is a temporarily unavailable DB dependency—never random failure injection.

Run the static contract test with `pytest tests/test_airflow_contract.py -q`. With Docker, use `make airflow-up` and `airflow dags list-import-errors`. The latter was not run in the acceptance environment because Docker/Airflow is unavailable.

Asset-aware scheduling is intentionally omitted from the first implementation: the explicit DAG/data-interval path is stable and testable, while assets were a secondary requirement and would add version coupling without improving the current local flow.
