"""Thin Airflow orchestration: business logic remains in saasgen modules/SQL."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone

from airflow.decorators import dag, task
from airflow.operators.empty import EmptyOperator

DEFAULT_ARGS = {
    "owner": "analytics-engineering",
    "retries": int(os.getenv("AIRFLOW_RETRIES", "2")),
    "retry_delay": timedelta(minutes=int(os.getenv("AIRFLOW_RETRY_DELAY_MINUTES", "5"))),
    "execution_timeout": timedelta(minutes=int(os.getenv("AIRFLOW_TASK_TIMEOUT_MINUTES", "45"))),
}
DATASET = os.getenv("SYNTHETIC_DATASET", "/opt/airflow/data/small")
DATABASE = os.getenv("WAREHOUSE_DATABASE", "/opt/airflow/data/warehouse.db")


def _run(*command: str) -> None:
    subprocess.run(command, check=True, timeout=40 * 60)


@task
def validate_contracts() -> str:
    _run("python", "quality.py", "--input", DATASET, "--layer", "clean")
    return "contracts-valid"


@task
def protect_pii() -> str:
    if not os.getenv("PII_HMAC_SECRET"):
        raise RuntimeError("PII_HMAC_SECRET must be provided by the runtime secret store")
    return "pii-key-present"


@task
def build_warehouse() -> str:
    _run("python", "-m", "saasgen.warehouse", "--input", DATASET, "--database", DATABASE)
    return DATABASE


@task
def run_dq_gate() -> str:
    _run("python", "quality.py", "--input", DATASET, "--layer", "clean")
    return "dq-pass"


@dag(
    dag_id="ingest_events",
    schedule=os.getenv("AIRFLOW_INGEST_CRON", "0 * * * *"),
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=True,
    default_args=DEFAULT_ARGS,
    max_active_runs=1,
    tags=["synthetic", "ingestion"],
)
def ingest_events_dag():
    extract = EmptyOperator(task_id="extract_event_partitions")
    validated = validate_contracts.override(task_id="validate_events")()
    protected = protect_pii.override(task_id="protect_event_pii")()
    loaded = build_warehouse.override(task_id="load_events_incrementally")()
    extract >> validated >> protected >> loaded


@dag(
    dag_id="ingest_billing",
    schedule=os.getenv("AIRFLOW_BILLING_CRON", "15 * * * *"),
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=True,
    default_args=DEFAULT_ARGS,
    max_active_runs=1,
    tags=["synthetic", "billing"],
)
def ingest_billing_dag():
    extract = EmptyOperator(task_id="extract_billing_partitions")
    validated = validate_contracts.override(task_id="validate_billing")()
    protected = protect_pii.override(task_id="protect_billing_pii")()
    loaded = build_warehouse.override(task_id="load_billing_incrementally")()
    extract >> validated >> protected >> loaded


@dag(
    dag_id="build_dwh",
    schedule=None,
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["synthetic", "dwh"],
)
def build_dwh_dag():
    raw_ready = EmptyOperator(task_id="raw_ready")
    core = build_warehouse.override(task_id="build_staging_and_core")()
    quality = run_dq_gate.override(task_id="core_quality_gate")()
    raw_ready >> core >> quality


@dag(
    dag_id="build_analytics_marts",
    schedule=os.getenv("AIRFLOW_MARTS_CRON", "0 6 * * *"),
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=True,
    default_args=DEFAULT_ARGS,
    max_active_runs=1,
    tags=["synthetic", "marts"],
)
def build_analytics_marts_dag():
    core = build_warehouse.override(task_id="incremental_core_and_marts")()
    quality = run_dq_gate.override(task_id="mart_quality_gate")()
    publish = EmptyOperator(task_id="publish_marts")
    core >> quality >> publish


@dag(
    dag_id="data_quality",
    schedule=os.getenv("AIRFLOW_DQ_CRON", "30 * * * *"),
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["synthetic", "quality"],
)
def data_quality_dag():
    run_dq_gate.override(task_id="contracts_integrity_freshness_volume")()


ingest_events = ingest_events_dag()
ingest_billing = ingest_billing_dag()
build_dwh = build_dwh_dag()
build_analytics_marts = build_analytics_marts_dag()
data_quality = data_quality_dag()
