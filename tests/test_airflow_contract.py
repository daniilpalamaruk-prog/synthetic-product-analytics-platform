import ast
from pathlib import Path


def test_airflow_dag_file_compiles_and_declares_required_dags():
    path = Path("airflow/dags/synthetic_analytics.py")
    source = path.read_text(encoding="utf-8")
    ast.parse(source)
    for dag_id in ("ingest_events", "ingest_billing", "build_dwh", "build_analytics_marts", "data_quality"):
        assert f'dag_id="{dag_id}"' in source
    assert "extract >> validated >> protected >> loaded" in source
    assert "core >> quality >> publish" in source
    assert "retries" in source and "retry_delay" in source and "execution_timeout" in source
