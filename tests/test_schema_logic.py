from collections import Counter
from pathlib import Path

import pyarrow.dataset as ds


def table(root: Path, name: str, columns=None):
    return ds.dataset(root / "clean" / name, format="parquet").to_table(columns=columns)


def test_required_columns_and_unique_keys(analytical_dataset: Path):
    required = {
        "users": {"user_id", "registration_at", "acquisition_channel", "first_session_id"},
        "sessions": {"session_id", "user_id", "session_started_at", "session_ended_at"},
        "events": {"event_id", "user_id", "session_id", "event_time", "event_name"},
        "subscriptions": {"subscription_id", "user_id", "plan", "started_at", "ended_at"},
        "payments": {"payment_id", "user_id", "subscription_id", "payment_at", "amount"},
    }
    keys = {"users": "user_id", "sessions": "session_id", "events": "event_id",
            "subscriptions": "subscription_id", "payments": "payment_id"}
    for name, columns in required.items():
        relation = table(analytical_dataset, name)
        assert columns <= set(relation.column_names)
        values = relation[keys[name]].to_pylist()
        assert len(values) == len(set(values))
        assert None not in values


def test_relationships_and_event_session_bounds(analytical_dataset: Path):
    users = set(table(analytical_dataset, "users", ["user_id"])["user_id"].to_pylist())
    sessions = {r["session_id"]: r for r in table(
        analytical_dataset, "sessions", ["session_id", "user_id", "session_started_at", "session_ended_at"]
    ).to_pylist()}
    subscriptions = set(table(analytical_dataset, "subscriptions", ["subscription_id"])["subscription_id"].to_pylist())
    for event in table(analytical_dataset, "events", ["user_id", "session_id", "event_time"]).to_pylist():
        assert event["user_id"] in users
        session = sessions[event["session_id"]]
        assert session["user_id"] == event["user_id"]
        assert session["session_started_at"] <= event["event_time"] <= session["session_ended_at"]
    for payment in table(analytical_dataset, "payments", ["user_id", "subscription_id"]).to_pylist():
        assert payment["user_id"] in users
        assert payment["subscription_id"] in subscriptions


def test_subscription_and_payment_logic(analytical_dataset: Path):
    plan_prices = {"basic": {15.0, 17.0}, "pro": {35.0, 39.0}}
    for row in table(analytical_dataset, "subscriptions").to_pylist():
        assert row["ended_at"] is None or row["ended_at"] >= row["started_at"]
        assert float(row["monthly_price_usd"]) in plan_prices[row["plan"]]
        assert float(row["monthly_price_local"]) == float(row["monthly_price"])
        assert float(row["monthly_price_local"]) > 0
        assert row["status"] in {"active", "cancelled"}
    for row in table(analytical_dataset, "payments").to_pylist():
        amount, refund = float(row["amount_local"]), float(row["refund_amount_local"])
        assert amount >= 0 and 0 <= refund <= amount
        assert abs(amount * float(row["fx_rate_to_usd"]) - float(row["amount_usd"])) < 0.05
        if row["status"] == "failed":
            assert amount == 0


def test_experiment_allocation_is_reasonably_balanced(analytical_dataset: Path):
    rows = table(analytical_dataset, "experiment_assignments", ["experiment_id", "variant"]).to_pylist()
    counts = Counter((r["experiment_id"], r["variant"]) for r in rows)
    for experiment in {key[0] for key in counts}:
        group_counts = [count for (exp, _), count in counts.items() if exp == experiment]
        assert len(group_counts) == 2
        assert 0.80 <= group_counts[0] / group_counts[1] <= 1.25
    assignments_per_user = Counter(r["user_id"] for r in table(
        analytical_dataset, "experiment_assignments", ["user_id"]).to_pylist())
    assert max(assignments_per_user.values(), default=0) == 1


def test_pipeline_monitoring_contract(analytical_dataset: Path):
    runs = table(analytical_dataset, "pipeline_runs").to_pylist()
    assert len(runs) == 360
    assert all(r["simulated"] for r in runs)
    assert sum(not r["partition_present"] for r in runs) == 1
    assert any(r["status"] == "failed_then_recovered" for r in runs)
    assert any(r["completeness_ratio"] < 0.99 for r in runs)


def test_fx_rates_cover_payment_currencies(analytical_dataset: Path):
    fx = table(analytical_dataset, "fx_rates").to_pylist()
    assert {r["currency"] for r in fx} == {"USD", "GBP", "EUR", "BRL", "INR", "CAD"}
    assert all(r["rate_to_usd"] > 0 and r["simulated"] for r in fx)
