from pathlib import Path

import yaml


def test_compose_and_required_documentation_are_present():
    compose = yaml.safe_load(Path("compose.yaml").read_text(encoding="utf-8"))
    assert {"airflow-webserver", "airflow-scheduler", "greenplum", "superset"} <= set(compose["services"])
    required = {
        "ARCHITECTURE.md", "DATA_FLOW.md", "DWH.md", "ETL_ELT.md", "AIRFLOW.md",
        "GREENPLUM.md", "DATA_QUALITY.md", "SECURITY.md", "BI.md", "METRICS.md",
        "EXPERIMENTS.md", "PERFORMANCE.md", "BUSINESS_CASES.md", "LEARNING_PATH.md",
        "CURRENT_STATE_AUDIT.md",
    }
    assert required <= {path.name for path in Path("docs").glob("*.md")}


def test_generated_datasets_are_not_kept_in_repository_workspace():
    assert not Path("data/analytics_ready").exists()
    assert not Path("sample/fx_release").exists()
    assert Path("data/.gitkeep").exists()
