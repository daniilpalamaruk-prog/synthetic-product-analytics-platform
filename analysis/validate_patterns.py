#!/usr/bin/env python3
"""Measure embedded patterns from a generated clean dataset (descriptive, not causal)."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pyarrow.dataset as ds

ACTIVE = {"login", "feature_viewed", "feature_used"}


def rows(root: Path, table: str, columns=None):
    return ds.dataset(root / "clean" / table, format="parquet").to_table(columns=columns).to_pylist()


def ratio(a, b): return round(a / b, 4) if b else None


def analyze(root: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    users = {r["user_id"]: r for r in rows(root, "users", ["user_id", "registration_date", "acquisition_channel", "device_type"])}
    period_end = date.fromisoformat(manifest["period_end"][:10])
    lifecycle, active_days, activation_features, completed = Counter(), defaultdict(set), defaultdict(set), set()
    experiment_users, exp_outcomes = defaultdict(set), defaultdict(lambda: Counter())
    for e in rows(root, "events", ["user_id", "event_date", "event_name", "feature_name", "experiment_id", "experiment_variant", "app_version"]):
        uid = e["user_id"]
        if uid not in users: continue
        age = (e["event_date"] - users[uid]["registration_date"]).days
        lifecycle[(users[uid]["device_type"], e["app_version"], e["event_name"])] += 1
        if e["event_name"] in ACTIVE: active_days[uid].add(age)
        if e["event_name"] == "onboarding_completed": completed.add(uid)
        if e["event_name"] == "feature_used" and 0 <= age <= 3 and e["feature_name"] in {"dashboard", "task_manager", "calendar"}:
            activation_features[uid].add(e["feature_name"])
        if e["experiment_id"]:
            key = (e["experiment_id"], e["experiment_variant"]); experiment_users[key].add(uid)
            if e["event_name"] in {"onboarding_completed", "checkout_started", "payment_success", "notification_disabled"}:
                exp_outcomes[(key, e["event_name"])][uid] = 1
    activated = {u for u in users if u in completed and len(activation_features[u]) >= 2}
    retention = {}
    for segment, population in {"activated": activated, "not_activated": set(users) - activated}.items():
        retention[segment] = {}
        for d in (1, 7, 30, 90):
            eligible = {u for u in population if (period_end - users[u]["registration_date"]).days >= d}
            retention[segment][f"d{d}"] = ratio(sum(d in active_days[u] for u in eligible), len(eligible))
    by_channel = {}
    for channel in sorted({u["acquisition_channel"] for u in users.values()}):
        pop = {uid for uid, u in users.items() if u["acquisition_channel"] == channel}
        eligible = {u for u in pop if (period_end - users[u]["registration_date"]).days >= 30}
        by_channel[channel] = {"users": len(pop), "d30": ratio(sum(30 in active_days[u] for u in eligible), len(eligible))}
    experiments = {}
    for key, pop in experiment_users.items():
        experiments[f"{key[0]}:{key[1]}"] = {"users": len(pop)} | {
            name: ratio(len(exp_outcomes[(key, name)]), len(pop))
            for name in ("onboarding_completed", "checkout_started", "payment_success", "notification_disabled")
        } | {"d7_retention": ratio(sum(7 in active_days[u] for u in pop), len(pop)),
             "d30_retention": ratio(sum(30 in active_days[u] for u in pop), len(pop))}
    incident = {}
    for version in ("3.5.0", "3.6.0", "3.7.0", "3.8.1"):
        attempts = lifecycle[("android", version, "payment_attempted")]
        success = lifecycle[("android", version, "payment_success")]
        signups = lifecycle[("android", version, "signup")]
        incident[version] = {"attempts": attempts, "success_per_attempt": ratio(success, attempts),
                             "success_per_signup": ratio(success, signups)}
    return {"synthetic": True, "manifest": {"seed": manifest["seed"], "totals": manifest["totals"]},
            "observed_descriptive_results": {"retention": retention, "d30_by_channel": by_channel,
                                             "experiments": experiments, "android_versions": incident}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("data"))
    p.add_argument("--output", type=Path)
    args = p.parse_args(); result = analyze(args.input)
    text = json.dumps(result, indent=2)
    if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__": main()
