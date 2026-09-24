from pathlib import Path


def test_greenplum_facts_have_distribution_and_partitioning():
    raw = Path("sql/greenplum/ddl/01_raw.sql").read_text(encoding="utf-8").lower()
    core = Path("sql/greenplum/ddl/02_staging_core.sql").read_text(encoding="utf-8").lower()
    assert "distributed by (user_id)" in raw
    assert raw.count("partition by range") >= 2
    assert "distributed replicated" in core
    assert "dim_user_plan_history" in core


def test_incremental_sql_uses_half_open_intervals_and_idempotency_guards():
    sql = Path("sql/greenplum/ddl/04_incremental_core.sql").read_text(encoding="utf-8").lower()
    assert ">= :'interval_start'" in sql
    assert "< :'interval_end'" in sql
    assert "not exists" in sql
    assert "is_current=false" in sql
