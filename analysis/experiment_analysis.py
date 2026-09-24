#!/usr/bin/env python3
"""Frequentist, intent-to-treat analysis for the synthetic experiments."""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pyarrow.dataset as ds

NORMAL = NormalDist()
ACTIVE = {"login", "feature_viewed", "feature_used"}
CORE_FEATURES = {"dashboard", "task_manager", "calendar"}


def rows(root: Path, table: str, columns=None):
    path = root / "clean" / table
    if not path.exists():
        return []
    return ds.dataset(path, format="parquet").to_table(columns=columns).to_pylist()


def two_proportion(x0: int, n0: int, x1: int, n1: int, alpha: float = 0.05) -> dict:
    if n0 <= 0 or n1 <= 0:
        raise ValueError("Both experiment variants must have eligible users")
    p0, p1 = x0 / n0, x1 / n1
    diff = p1 - p0
    pooled = (x0 + x1) / (n0 + n1)
    se0 = math.sqrt(max(1e-15, pooled * (1 - pooled) * (1 / n0 + 1 / n1)))
    z = diff / se0
    p_value = 2 * (1 - NORMAL.cdf(abs(z)))
    se_diff = math.sqrt(p0 * (1 - p0) / n0 + p1 * (1 - p1) / n1)
    z_alpha = NORMAL.inv_cdf(1 - alpha / 2)
    ci = [diff - z_alpha * se_diff, diff + z_alpha * se_diff]
    ncp = abs(diff) / max(se_diff, 1e-15)
    power = NORMAL.cdf(-z_alpha - ncp) + 1 - NORMAL.cdf(z_alpha - ncp)
    z_beta = NORMAL.inv_cdf(0.80)
    balanced_n = 2 / (1 / n0 + 1 / n1)
    mde = math.sqrt(2 * pooled * (1 - pooled) * (z_alpha + z_beta) ** 2
                    / max(balanced_n, 1))
    return {
        "control": {"successes": x0, "n": n0, "rate": p0},
        "treatment": {"successes": x1, "n": n1, "rate": p1},
        "absolute_uplift": diff,
        "relative_uplift": diff / p0 if p0 else None,
        "ci_95_absolute": ci,
        "z_statistic": z,
        "p_value": p_value,
        "observed_power_approx": power,
        "mde_80_power_absolute_approx": mde,
        "alpha": alpha,
        "target_beta": 0.20,
    }


def holm_adjust(items: list[tuple[str, float]]) -> dict[str, float]:
    ordered = sorted(items, key=lambda item: item[1])
    adjusted, running = {}, 0.0
    m = len(ordered)
    for rank, (key, p_value) in enumerate(ordered):
        running = max(running, min(1.0, (m - rank) * p_value))
        adjusted[key] = running
    return adjusted


def srm_test(observed: dict[str, int], expected_split: dict[str, float], alpha: float = 0.01) -> dict:
    """Pearson chi-square SRM test. Current designs have two variants (df=1)."""
    variants = list(expected_split)
    total = sum(observed.get(variant, 0) for variant in variants)
    expected_total = sum(float(expected_split[variant]) for variant in variants)
    if total == 0 or expected_total <= 0:
        raise ValueError("SRM requires non-empty assignments and a positive expected split")
    normalized = {variant: float(expected_split[variant]) / expected_total for variant in variants}
    expected_counts = {variant: total * normalized[variant] for variant in variants}
    chi_square = sum(
        (observed.get(variant, 0) - expected_counts[variant]) ** 2 / expected_counts[variant]
        for variant in variants
    )
    if len(variants) != 2:
        raise ValueError("The dependency-free SRM implementation supports two variants")
    p_value = math.erfc(math.sqrt(chi_square / 2))
    return {
        "expected_split": normalized,
        "observed_counts": {variant: observed.get(variant, 0) for variant in variants},
        "observed_split": {variant: observed.get(variant, 0) / total for variant in variants},
        "chi_square": chi_square,
        "degrees_of_freedom": 1,
        "p_value": p_value,
        "alpha": alpha,
        "srm_detected": p_value < alpha,
    }


def bootstrap_mean_difference(control: np.ndarray, treatment: np.ndarray,
                              rng: np.random.Generator, iterations: int = 2000) -> dict:
    if not len(control) or not len(treatment):
        raise ValueError("Both variants must have assigned users")
    differences = np.empty(iterations)
    for i in range(iterations):
        differences[i] = (rng.choice(treatment, len(treatment), replace=True).mean()
                          - rng.choice(control, len(control), replace=True).mean())
    return {
        "control_mean_usd": float(control.mean()),
        "treatment_mean_usd": float(treatment.mean()),
        "absolute_uplift_usd": float(treatment.mean() - control.mean()),
        "ci_95_bootstrap_usd": np.quantile(differences, [0.025, 0.975]).tolist(),
        "iterations": iterations,
        "analysis_unit": "assigned_user",
    }


def analyze(root: Path, iterations: int = 2000) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    period_end = date.fromisoformat(manifest["period_end"][:10])
    designs = manifest.get("model_config", {}).get("experiment_analysis", {})
    users = {r["user_id"]: r["registration_date"] for r in rows(
        root, "users", ["user_id", "registration_date"])}
    assignments = rows(root, "experiment_assignments",
                       ["experiment_id", "user_id", "variant", "assigned_at"])
    assignment_by_user = {r["user_id"]: r for r in assignments}

    outcomes = defaultdict(set)
    active_days = defaultdict(set)
    core_features = defaultdict(set)
    for event in rows(root, "events", [
            "user_id", "event_name", "event_date", "event_time", "feature_name"]):
        uid = event["user_id"]
        assignment = assignment_by_user.get(uid)
        if assignment is None or event["event_time"] < assignment["assigned_at"]:
            continue
        experiment_id = assignment["experiment_id"]
        if event["event_name"] in {
                "onboarding_completed", "checkout_started", "payment_success",
                "notification_disabled"}:
            outcomes[(experiment_id, event["event_name"])].add(uid)
        if event["event_name"] in ACTIVE:
            active_days[uid].add((event["event_date"] - users[uid]).days)
        if (event["event_name"] == "feature_used"
                and event["feature_name"] in CORE_FEATURES
                and event["event_time"].date() <= users[uid] + timedelta(days=3)):
            core_features[uid].add(event["feature_name"])

    revenue = defaultdict(float)
    refunded_users = defaultdict(set)
    for payment in rows(root, "payments", [
            "user_id", "payment_at", "amount_usd", "refund_amount_usd", "status"]):
        uid = payment["user_id"]
        assignment = assignment_by_user.get(uid)
        if assignment is None or payment["payment_at"] < assignment["assigned_at"]:
            continue
        if payment["status"] in {"success", "refunded"}:
            revenue[uid] += float(payment["amount_usd"] - payment["refund_amount_usd"])
        if payment["status"] == "refunded":
            refunded_users[assignment["experiment_id"]].add(uid)

    variants = defaultdict(lambda: defaultdict(set))
    for row in assignments:
        variants[row["experiment_id"]][row["variant"]].add(row["user_id"])

    def binary_result(experiment_id: str, metric: str, control: set, treatment: set):
        if metric.startswith("d") and metric.endswith("_retention"):
            day = int(metric[1:].split("_")[0])
            c_eligible = {u for u in control if (period_end - users[u]).days >= day}
            t_eligible = {u for u in treatment if (period_end - users[u]).days >= day}
            x0 = sum(day in active_days[u] for u in c_eligible)
            x1 = sum(day in active_days[u] for u in t_eligible)
        elif metric == "activation":
            c_eligible = {u for u in control if (period_end - users[u]).days >= 3}
            t_eligible = {u for u in treatment if (period_end - users[u]).days >= 3}
            completed = outcomes[(experiment_id, "onboarding_completed")]
            x0 = sum(u in completed and len(core_features[u]) >= 2 for u in c_eligible)
            x1 = sum(u in completed and len(core_features[u]) >= 2 for u in t_eligible)
        elif metric == "refund_rate":
            c_eligible, t_eligible = control, treatment
            x0 = len(control & refunded_users[experiment_id])
            x1 = len(treatment & refunded_users[experiment_id])
        else:
            c_eligible, t_eligible = control, treatment
            x0 = len(control & outcomes[(experiment_id, metric)])
            x1 = len(treatment & outcomes[(experiment_id, metric)])
        if not c_eligible or not t_eligible:
            return None
        return two_proportion(x0, len(c_eligible), x1, len(t_eligible))

    rng = np.random.default_rng(int(manifest["seed"]) + 773)
    report = {}
    default_metrics = ["onboarding_completed", "checkout_started", "payment_success",
                       "notification_disabled", "activation", "refund_rate",
                       "d7_retention", "d30_retention"]
    for experiment_id, groups in variants.items():
        design = designs.get(experiment_id, {})
        expected_split = design.get("expected_split") or {
            variant: 1 / len(groups) for variant in groups}
        treatment_name = next((v for v in expected_split if v != "control"),
                              "new_pricing" if "new_pricing" in groups else "treatment")
        control, treatment = groups["control"], groups[treatment_name]
        configured_metrics = ([design.get("primary_metric")]
                              + list(design.get("secondary_metrics", []))
                              + list(design.get("guardrail_metrics", []))
                              + list(design.get("exploratory_metrics", [])))
        metric_names = list(dict.fromkeys(m for m in configured_metrics if m)) or default_metrics
        binary_metrics = {}
        revenue_result = bootstrap_mean_difference(
            np.array([revenue[u] for u in control], dtype=float),
            np.array([revenue[u] for u in treatment], dtype=float), rng, iterations)
        for metric in metric_names:
            if metric != "revenue_per_assigned_user":
                result = binary_result(experiment_id, metric, control, treatment)
                if result is not None:
                    binary_metrics[metric] = result

        secondary_names = [m for m in design.get("secondary_metrics", []) if m in binary_metrics]
        adjusted = holm_adjust([(m, binary_metrics[m]["p_value"]) for m in secondary_names])
        for metric in secondary_names:
            binary_metrics[metric]["holm_adjusted_p_value"] = adjusted[metric]
            binary_metrics[metric]["significant_after_holm_0_05"] = adjusted[metric] < 0.05

        def metric_result(name: str):
            return revenue_result if name == "revenue_per_assigned_user" else binary_metrics.get(name)

        primary_name = design.get("primary_metric", "onboarding_completed")
        report[experiment_id] = {
            "control_variant": "control",
            "treatment_variant": treatment_name,
            "srm": srm_test({v: len(groups.get(v, set())) for v in expected_split}, expected_split),
            "primary_metric": {"name": primary_name, "result": metric_result(primary_name)},
            "secondary_metrics": {m: metric_result(m) for m in design.get("secondary_metrics", [])},
            "guardrail_metrics": {m: metric_result(m) for m in design.get("guardrail_metrics", [])},
            "exploratory_metrics": {m: metric_result(m) for m in design.get("exploratory_metrics", [])},
            "multiplicity": {
                "method": "Holm family-wise correction",
                "family": "predefined secondary metrics within this experiment",
                "metrics": secondary_names,
            },
            "revenue_per_assigned_user": revenue_result,
            "binary_metrics": binary_metrics,
        }

    return {
        "synthetic": True,
        "analysis_type": "measured statistical results for one generated run",
        "seed": manifest["seed"],
        "analysis_population": "intent-to-treat; outcomes at or after assignment",
        "assignment_model": "mutually exclusive experiment enrollment",
        "multiple_comparisons": "Holm correction within each predefined secondary family only",
        "srm_policy": "Pearson chi-square against configured allocation; flag at p < 0.01",
        "revenue_currency": "USD, converted at synthetic event-date FX rates",
        "experiments": report,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze synthetic A/B experiments")
    parser.add_argument("--input", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bootstrap-iterations", type=int, default=2000)
    args = parser.parse_args()
    result = analyze(args.input, args.bootstrap_iterations)
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
