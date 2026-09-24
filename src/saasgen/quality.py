from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

import pyarrow.dataset as ds

from .catalog import EVENT_NAMES
from .io import write_json
from .settings import deep_get


def _rows(root: Path, table: str, columns=None, layer: str = "raw"):
    path = root / layer / table
    if not path.exists():
        return
    scanner = ds.dataset(path, format="parquet").scanner(columns=columns, batch_size=100_000)
    for batch in scanner.to_batches():
        yield from batch.to_pylist()


def _result(name: str, failures: int, total: int, warn_rate=0.001, fail_rate=0.01, detail=""):
    rate = failures / total if total else 0.0
    status = "FAIL" if rate > fail_rate else ("WARN" if rate > warn_rate else "PASS")
    return {"check": name, "status": status, "failures": failures, "rows_scanned": total,
            "failure_rate": round(rate, 6), "detail": detail}


def run_quality(root: Path, layer: str = "raw") -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    raw_users = list(_rows(root, "users", ["user_id", "registration_at", "campaign_id", "acquisition_channel"], layer))
    registrations = {r["user_id"]: r["registration_at"] for r in raw_users}
    user_ids = set(registrations)
    invalid_campaigns = sum(not r["campaign_id"].startswith(f"{r['acquisition_channel']}_") for r in raw_users)
    subscription_ids = {r["subscription_id"] for r in _rows(root, "subscriptions", ["subscription_id"], layer)}
    event_seen, payment_seen = set(), set()
    event_total = duplicate_events = null_users = orphan_events = invalid_events = invalid_variants = impossible = late = 0
    daily_volume = Counter()
    max_event = None
    variants = {"exp_onboarding_v2": {"control", "treatment"}, "exp_pricing_v2": {"control", "new_pricing"},
                "exp_notifications": {"control", "treatment"}}
    for row in _rows(root, "events", ["event_id", "user_id", "event_name", "event_time", "event_date", "properties", "experiment_id", "experiment_variant"], layer):
        event_total += 1
        daily_volume[row["event_date"]] += 1
        if row["event_id"] in event_seen: duplicate_events += 1
        event_seen.add(row["event_id"])
        if row["user_id"] is None: null_users += 1
        elif row["user_id"] not in user_ids: orphan_events += 1
        if row["event_name"] not in EVENT_NAMES: invalid_events += 1
        if row["experiment_id"] is not None and row["experiment_variant"] not in variants.get(row["experiment_id"], set()):
            invalid_variants += 1
        if (row["event_time"].year < 2024 or
            (row["user_id"] in registrations and row["event_name"] not in {"ad_impression", "ad_click"}
             and row["event_time"] < registrations[row["user_id"]])):
            impossible += 1
        if row.get("properties") and "late_arrival_hours" in row["properties"]: late += 1
        max_event = max(max_event, row["event_time"]) if max_event else row["event_time"]
    payment_total = duplicate_payments = negative = orphan_payments = payment_fx_mismatch = 0
    for row in _rows(root, "payments", ["payment_id", "subscription_id", "amount", "amount_local", "amount_usd", "fx_rate_to_usd"], layer):
        payment_total += 1
        if row["payment_id"] in payment_seen: duplicate_payments += 1
        payment_seen.add(row["payment_id"])
        if row["amount"] < 0: negative += 1
        if abs(row["amount_local"] * row["fx_rate_to_usd"] - row["amount_usd"]) > 0.05:
            payment_fx_mismatch += 1
        if row["subscription_id"] not in subscription_ids: orphan_payments += 1
    impossible_subscriptions = sum(
        1 for r in _rows(root, "subscriptions", ["started_at", "ended_at"], layer)
        if r["ended_at"] is not None and r["ended_at"] < r["started_at"]
    )
    subscription_total = len(subscription_ids)
    marketing_rows = list(_rows(root, "marketing_spend", ["spend_local", "spend_usd", "fx_rate_to_usd"], layer))
    marketing_fx_mismatch = sum(abs(r["spend_local"] * r["fx_rate_to_usd"] - r["spend_usd"]) > 0.05
                                for r in marketing_rows)
    pipeline = manifest.get("pipeline", {})
    model = manifest.get("model_config", {})
    logical_run = datetime.fromisoformat(str(pipeline.get("logical_run_at", manifest["period_end"])))
    watermark = datetime.fromisoformat(str(pipeline.get("source_watermark", manifest["period_end"])))
    freshness_gap = max(0.0, (logical_run.timestamp() - watermark.timestamp()) / 3600)
    if freshness_gap <= 1:
        freshness_status = "PASS"
    elif freshness_gap <= 3:
        freshness_status = "WARN"
    else:
        freshness_status = "FAIL"
    ordered_dates = sorted(daily_volume)
    ordered_counts = [daily_volume[d] for d in ordered_dates]
    log_changes = [math.log((b + 1) / (a + 1)) for a, b in zip(ordered_counts, ordered_counts[1:])]
    if log_changes:
        center = statistics.median(log_changes)
        mad = statistics.median(abs(x - center) for x in log_changes)
        threshold = max(0.75, 6 * 1.4826 * mad)
        anomaly_dates = [ordered_dates[i + 1] for i, x in enumerate(log_changes) if abs(x - center) > threshold]
    else:
        anomaly_dates = []
    timeline_path = root / layer / "business_timeline"
    planned_dates = {r["effective_at"].date() for r in _rows(root, "business_timeline", ["effective_at"], layer)} if timeline_path.exists() else set()
    expected_volume_anomalies = sum(any(abs((day - planned).days) <= 2 for planned in planned_dates) for day in anomaly_dates)
    unexpected_volume_anomalies = len(anomaly_dates) - expected_volume_anomalies
    volume_status = ("FAIL" if unexpected_volume_anomalies > max(3, len(log_changes) * 0.05)
                     else ("WARN" if unexpected_volume_anomalies else "PASS"))
    pipeline_path = root / layer / "pipeline_runs"
    pipeline_runs = list(_rows(root, "pipeline_runs", layer=layer)) if pipeline_path.exists() else []
    completeness_target = float(deep_get(model, "sla.completeness_ratio", 0.99))
    duration_target = int(deep_get(model, "sla.max_pipeline_duration_minutes", 45))
    allowed_delay_target = int(deep_get(model, "sla.allowed_delay_minutes", 180))
    success_target = float(deep_get(model, "sla.target_success_rate", 0.995))
    missing_partitions = sum(not r["partition_present"] for r in pipeline_runs)
    incomplete_runs = sum(r["completeness_ratio"] < completeness_target for r in pipeline_runs)
    unavailable_runs = sum(not r["available_by_sla"] for r in pipeline_runs)
    slow_runs = sum(r["duration_minutes"] > duration_target for r in pipeline_runs)
    excessive_delay_runs = sum(r["delay_minutes"] > allowed_delay_target for r in pipeline_runs)
    pipeline_success_rate = (sum(r["status"] == "success" for r in pipeline_runs) / len(pipeline_runs)
                             if pipeline_runs else 0.0)
    checks = [
        _result("event_id_uniqueness", duplicate_events, event_total),
        _result("event_user_id_not_null", null_users, event_total),
        _result("event_user_referential_integrity", orphan_events, event_total),
        _result("event_name_accepted_values", invalid_events, event_total),
        _result("experiment_variant_accepted_values", invalid_variants, event_total),
        _result("campaign_id_known", invalid_campaigns, len(raw_users)),
        _result("event_timestamp_possible", impossible, event_total),
        _result("late_arriving_events", late, event_total, warn_rate=0.01, fail_rate=0.03,
                detail="Controlled defects target 1-2% when enabled"),
        _result("payment_id_uniqueness", duplicate_payments, payment_total),
        _result("payment_amount_non_negative", negative, payment_total),
        _result("payment_fx_reconciliation", payment_fx_mismatch, payment_total),
        _result("marketing_fx_reconciliation", marketing_fx_mismatch, len(marketing_rows)),
        _result("payment_subscription_referential_integrity", orphan_payments, payment_total),
        _result("subscription_date_order", impossible_subscriptions, subscription_total,
                warn_rate=0.0001, fail_rate=0.05,
                detail="Controlled raw defect target is 0.07%; clean layer must have zero"),
        {"check": "dataset_freshness", "status": freshness_status,
         "failures": 0, "rows_scanned": event_total, "failure_rate": 0,
         "detail": f"{freshness_gap:.2f} hours from source watermark to logical pipeline run; SLA <1h"},
        {"check": "table_freshness_events", "status": freshness_status,
         "failures": 0 if freshness_status != "FAIL" else 1, "rows_scanned": event_total,
         "failure_rate": 0, "detail": f"latest event={max_event}; watermark lag={freshness_gap:.2f}h"},
        {"check": "row_count_anomaly", "status": "PASS" if event_total >= manifest["totals"]["events"] else "FAIL",
         "failures": max(0, manifest["totals"]["events"] - event_total), "rows_scanned": event_total,
         "failure_rate": 0, "detail": "Raw count must be >= clean target because duplicates may be injected"},
        {"check": "volume_anomaly", "status": volume_status, "failures": unexpected_volume_anomalies,
         "rows_scanned": len(ordered_counts), "failure_rate": round(unexpected_volume_anomalies / max(1, len(log_changes)), 6),
         "detail": (f"Robust median/MAD check found {len(anomaly_dates)} shifts; "
                    f"{expected_volume_anomalies} align ±2d with declared synthetic timeline events")},
        {"check": "latest_available_event", "status": "PASS" if max_event else "FAIL",
         "failures": 0 if max_event else 1, "rows_scanned": event_total, "failure_rate": 0,
         "detail": str(max_event) if max_event else "No event available"},
        _result("missing_daily_partitions", missing_partitions, len(pipeline_runs), warn_rate=0, fail_rate=0.02,
                detail="Expected partitions are declared by synthetic pipeline_runs"),
        _result("completeness_sla", incomplete_runs, len(pipeline_runs), warn_rate=0, fail_rate=0.02,
                detail=f"Daily actual/expected event rows target >= {completeness_target:.3f}"),
        _result("data_availability_sla", unavailable_runs, len(pipeline_runs), warn_rate=0, fail_rate=0.02,
                detail="Daily mart target is available by configured UTC deadline"),
        _result("pipeline_duration_sla", slow_runs, len(pipeline_runs), warn_rate=0, fail_rate=0.02,
                detail=f"Target <= {duration_target} minutes"),
        _result("allowed_delay_sla", excessive_delay_runs, len(pipeline_runs), warn_rate=0, fail_rate=0.02,
                detail=f"Maximum allowed delay <= {allowed_delay_target} minutes"),
        {"check": "pipeline_success_sla", "status": "PASS" if pipeline_success_rate >= success_target else "FAIL",
         "failures": sum(r["status"] != "success" for r in pipeline_runs), "rows_scanned": len(pipeline_runs),
         "failure_rate": round(1 - pipeline_success_rate, 6),
         "detail": f"Observed {pipeline_success_rate:.4f}; target {success_target:.4f}"},
    ]
    overall = "FAIL" if any(c["status"] == "FAIL" for c in checks) else ("WARN" if any(c["status"] == "WARN" for c in checks) else "PASS")
    report = {"overall_status": overall, "synthetic": True, "layer": layer, "checks": checks}
    output_name = "quality_report.json" if layer == "raw" else f"quality_report_{layer}.json"
    write_json(root / output_name, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a generated SaaS dataset")
    parser.add_argument("--input", type=Path, default=Path("data"))
    parser.add_argument("--layer", choices=["raw", "clean"], default="raw")
    args = parser.parse_args()
    report = run_quality(args.input, args.layer)
    for check in report["checks"]:
        print(f"{check['status']:4} {check['check']}: {check['failures']}/{check['rows_scanned']}")
    print(f"Overall: {report['overall_status']}")
