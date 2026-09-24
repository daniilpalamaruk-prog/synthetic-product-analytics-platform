import sqlite3
from datetime import timedelta
from pathlib import Path

from cryptography.fernet import Fernet

from saasgen.config import GeneratorConfig
from saasgen.generator import generate
from saasgen.warehouse import WarehousePipeline


def test_incremental_pipeline_is_idempotent_and_marts_have_no_raw_pii(tmp_path: Path):
    source = tmp_path / "source"
    config = GeneratorConfig(users=100, target_events=2_000, seed=19, output=source,
                             chunk_size=1_000, inject_data_quality_issues=False)
    generate(config)
    database = tmp_path / "warehouse.db"
    pipeline = WarehousePipeline(database, hmac_secret="test-secret-at-least-32-bytes-long",
                                 encryption_key=Fernet.generate_key().decode())
    end = config.start_date + timedelta(days=config.months * 30)
    first = pipeline.run(source, config.start_date, end, batch_id="same-batch")
    with sqlite3.connect(database) as connection:
        before = connection.execute("SELECT COUNT(*) FROM fct_events").fetchone()[0]
    second = pipeline.run(source, config.start_date, end, batch_id="same-batch")
    with sqlite3.connect(database) as connection:
        after = connection.execute("SELECT COUNT(*) FROM fct_events").fetchone()[0]
        duplicates = connection.execute(
            "SELECT COUNT(*)-COUNT(DISTINCT event_id) FROM fct_events"
        ).fetchone()[0]
        assert connection.execute("SELECT COUNT(*) FROM mart_revenue_daily").fetchone()[0] > 0
        assert connection.execute("SELECT COUNT(*) FROM mart_product_daily").fetchone()[0] > 0
        assert connection.execute("SELECT COUNT(*) FROM mart_pipeline_health").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM fct_experiments").fetchone()[0] > 0
        current = connection.execute(
            "SELECT COUNT(*) FROM (SELECT user_id FROM dim_user_plan_history "
            "WHERE is_current=1 GROUP BY user_id HAVING COUNT(*)<>1)"
        ).fetchone()[0]
        assert current == 0
        mart_columns = {
            row[1] for table in ("mart_revenue_daily", "mart_product_daily", "mart_pipeline_health")
            for row in connection.execute(f"PRAGMA table_info({table})")
        }
    assert first.status == second.status == "success"
    assert before == after == 2_000
    assert duplicates == 0
    assert mart_columns.isdisjoint({"name", "email", "phone", "ip_address", "encrypted_pii"})


def test_quarantine_payload_redacts_pii(tmp_path: Path):
    source = tmp_path / "source"
    config = GeneratorConfig(users=40, target_events=400, seed=20, output=source,
                             chunk_size=1_000, inject_data_quality_issues=False)
    generate(config)
    # Corruption is exercised at the ingestion function boundary without mutating generated Parquet.
    from saasgen.warehouse import _safe_payload
    payload = _safe_payload({"user_id": "u", "email": "secret@example.test", "phone": "+1555"})
    assert "secret@example.test" not in payload
    assert "+1555" not in payload
    assert payload.count("[REDACTED]") == 2
