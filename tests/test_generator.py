from pathlib import Path

import pyarrow.dataset as ds

from saasgen.config import GeneratorConfig
from saasgen.generator import generate
from saasgen.quality import run_quality


def count(root: Path, layer: str, table: str) -> int:
    return ds.dataset(root / layer / table, format="parquet").count_rows()


def test_end_to_end_exact_volume_and_layers(tmp_path: Path):
    cfg = GeneratorConfig(users=120, target_events=2400, seed=7, output=tmp_path,
                          chunk_size=1000, inject_data_quality_issues=True)
    manifest = generate(cfg)
    assert manifest["totals"]["events"] == 2400
    assert count(tmp_path, "clean", "users") == 120
    assert count(tmp_path, "clean", "events") == 2400
    assert count(tmp_path, "clean", "business_timeline") == 12
    assert count(tmp_path, "clean", "generator_config") == 1
    assert count(tmp_path, "raw", "events") > 2400
    assert count(tmp_path, "quarantine", "events") > 0
    assert (tmp_path / "manifest.json").exists()
    report = run_quality(tmp_path)
    assert report["overall_status"] in {"WARN", "FAIL"}


def test_seed_reproduces_clean_ids(tmp_path: Path):
    a, b = tmp_path / "a", tmp_path / "b"
    base = dict(users=50, target_events=1000, seed=99, chunk_size=1000,
                inject_data_quality_issues=False)
    generate(GeneratorConfig(output=a, **base))
    generate(GeneratorConfig(output=b, **base))
    cols = ["event_id", "user_id", "event_name", "event_time"]
    rows_a = ds.dataset(a / "clean/events", format="parquet").to_table(columns=cols).to_pylist()
    rows_b = ds.dataset(b / "clean/events", format="parquet").to_table(columns=cols).to_pylist()
    assert rows_a == rows_b


def test_clean_referential_integrity(tmp_path: Path):
    cfg = GeneratorConfig(users=100, target_events=2000, seed=11, output=tmp_path,
                          chunk_size=1000, inject_data_quality_issues=False)
    generate(cfg)
    users = set(ds.dataset(tmp_path / "clean/users", format="parquet").to_table(columns=["user_id"])["user_id"].to_pylist())
    event_users = set(ds.dataset(tmp_path / "clean/events", format="parquet").to_table(columns=["user_id"])["user_id"].to_pylist())
    assert event_users <= users


def test_anomalies_absent_when_disabled(tmp_path: Path):
    cfg = GeneratorConfig(users=100, target_events=2000, seed=55, output=tmp_path,
                          chunk_size=1000, inject_data_quality_issues=False)
    generate(cfg)
    assert count(tmp_path, "raw", "events") == count(tmp_path, "clean", "events")
    assert count(tmp_path, "raw", "payments") == count(tmp_path, "clean", "payments")
    assert not (tmp_path / "quarantine").exists()
