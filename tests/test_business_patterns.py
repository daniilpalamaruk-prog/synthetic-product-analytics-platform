from collections import defaultdict
from pathlib import Path

import pyarrow.dataset as ds

from analysis.experiment_analysis import analyze as analyze_experiments
from analysis.validate_patterns import analyze as analyze_patterns


def rows(root: Path, name: str, columns=None):
    return ds.dataset(root / "clean" / name, format="parquet").to_table(columns=columns).to_pylist()


def test_retention_probability_ranges_and_activation_effect(analytical_dataset: Path):
    report = analyze_patterns(analytical_dataset)["observed_descriptive_results"]["retention"]
    activated, inactive = report["activated"], report["not_activated"]
    assert 0.35 <= (activated["d1"] + inactive["d1"]) / 2 <= 0.60
    assert 0.15 <= (activated["d7"] + inactive["d7"]) / 2 <= 0.40
    assert 0.08 <= (activated["d30"] + inactive["d30"]) / 2 <= 0.25
    assert activated["d30"] >= inactive["d30"] + 0.07


def test_referral_ltv_cac_exceeds_tiktok(analytical_dataset: Path):
    channels = {r["user_id"]: r["acquisition_channel"] for r in rows(
        analytical_dataset, "users", ["user_id", "acquisition_channel"])}
    revenue, user_counts, spend = defaultdict(float), defaultdict(int), defaultdict(float)
    for channel in channels.values():
        user_counts[channel] += 1
    for payment in rows(analytical_dataset, "payments", ["user_id", "amount_usd", "refund_amount_usd", "status"]):
        if payment["status"] in {"success", "refunded"}:
            revenue[channels[payment["user_id"]]] += float(payment["amount_usd"] - payment["refund_amount_usd"])
    for item in rows(analytical_dataset, "marketing_spend", ["channel", "spend_usd"]):
        spend[item["channel"]] += float(item["spend_usd"])
    ratio = {c: (revenue[c] / user_counts[c]) / (spend[c] / user_counts[c]) for c in ("referral", "tiktok")}
    assert ratio["referral"] > ratio["tiktok"] * 2


def test_android_incident_and_onboarding_treatment(analytical_dataset: Path):
    patterns = analyze_patterns(analytical_dataset)["observed_descriptive_results"]["android_versions"]
    incident = patterns["3.7.0"]["success_per_attempt"]
    fixed = patterns["3.8.1"]["success_per_attempt"]
    assert incident is not None and fixed is not None
    assert incident <= fixed - 0.12
    experiments = analyze_experiments(analytical_dataset, iterations=200)["experiments"]
    onboarding = experiments["exp_onboarding_v2"]["binary_metrics"]["onboarding_completed"]
    assert onboarding["treatment"]["rate"] >= onboarding["control"]["rate"] + 0.04


def test_experiment_metric_roles_srm_and_secondary_correction(analytical_dataset: Path):
    report = analyze_experiments(analytical_dataset, iterations=100)["experiments"]
    onboarding = report["exp_onboarding_v2"]
    assert onboarding["primary_metric"]["name"] == "onboarding_completed"
    assert "holm_adjusted_p_value" not in onboarding["primary_metric"]["result"]
    assert set(onboarding["secondary_metrics"]) == {"activation", "payment_success"}
    assert all("holm_adjusted_p_value" in result
               for result in onboarding["secondary_metrics"].values())
    assert onboarding["srm"]["expected_split"] == {"control": 0.5, "treatment": 0.5}
    pricing = report["exp_pricing_v2"]
    assert pricing["primary_metric"]["name"] == "revenue_per_assigned_user"
    assert "control_mean_usd" in pricing["primary_metric"]["result"]
