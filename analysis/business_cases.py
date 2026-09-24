"""Generate evidence-led synthetic business case reports from a dataset."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.dataset as ds


def rows(root: Path, table: str, columns: list[str]):
    scanner = ds.dataset(root / "clean" / table, format="parquet").scanner(columns=columns, batch_size=100_000)
    for batch in scanner.to_batches():
        yield from batch.to_pylist()


def _rate(successes: int, attempts: int) -> float | None:
    return successes / attempts if attempts else None


def android_case(root: Path) -> str:
    versions: dict[str, Counter] = defaultdict(Counter)
    for row in rows(root, "events", ["device_type", "app_version", "event_name"]):
        if row["device_type"] == "android" and row["event_name"] in {"payment_attempted", "payment_success"}:
            versions[row["app_version"]][row["event_name"]] += 1
    evidence = []
    for version, counts in sorted(versions.items()):
        rate = _rate(counts["payment_success"], counts["payment_attempted"])
        evidence.append(f"| {version} | {counts['payment_attempted']} | {counts['payment_success']} | {rate:.2%} |" if rate is not None else
                        f"| {version} | {counts['payment_attempted']} | {counts['payment_success']} | n/a |")
    affected = _rate(versions["3.7.0"]["payment_success"], versions["3.7.0"]["payment_attempted"])
    fixed = _rate(versions["3.8.1"]["payment_success"], versions["3.8.1"]["payment_attempted"])
    gap = (fixed - affected) if affected is not None and fixed is not None else None
    recommendation = ("Keep 3.7.0 blocked and monitor the fixed release." if gap is not None and gap > 0.1
                      else "Do not attribute an incident until more attempts are available.")
    return f"""# Android payment incident

## Question
Can the payment-success drop be localized to Android version 3.7.0?

## Evidence
| Version | Attempts | Successes | Success rate |
|---|---:|---:|---:|
{chr(10).join(evidence)}

## Analysis
The fixed-minus-affected success-rate difference is {f'{gap:.2%}' if gap is not None else 'not estimable'}.

## Metric impact
The affected metric is payment success per attempt, segmented by platform, version, and time.

## Interpretation
This is a designed synthetic incident; the table is calculated from events rather than hardcoded as a finding.

## Recommendation
{recommendation}

## Limitations
Descriptive rates do not isolate gateway, country, retry, or user-mix effects and are not real operational evidence.
"""


def pricing_case(root: Path) -> str:
    assigned: dict[str, str] = {}
    for row in rows(root, "experiment_assignments", ["experiment_id", "user_id", "variant"]):
        if row["experiment_id"] == "exp_pricing_v2":
            assigned[row["user_id"]] = row["variant"]
    counts = Counter(assigned.values())
    checkout_users: dict[str, set[str]] = defaultdict(set)
    for row in rows(root, "events", ["user_id", "event_name"]):
        variant = assigned.get(row["user_id"])
        if variant and row["event_name"] == "checkout_started":
            checkout_users[variant].add(row["user_id"])
    revenue = defaultdict(float)
    for row in rows(root, "payments", ["user_id", "amount_usd", "refund_amount_usd", "status"]):
        variant = assigned.get(row["user_id"])
        if variant and row["status"] in {"success", "refunded"}:
            revenue[variant] += float(row["amount_usd"] - row["refund_amount_usd"])
    lines = []
    for variant in ("control", "new_pricing"):
        n = counts[variant]
        conversion = len(checkout_users[variant]) / n if n else 0
        arpa = revenue[variant] / n if n else 0
        lines.append(f"| {variant} | {n} | {conversion:.2%} | ${arpa:.2f} | ${revenue[variant]:.2f} |")
    recommendation = "Continue only as a guarded experiment; use the formal CI/SRM report before rollout."
    return f"""# Pricing experiment

## Question
Does new pricing create enough value to offset checkout friction?

## Evidence
| Variant | Assigned | Checkout conversion | Revenue / assigned user | Net revenue |
|---|---:|---:|---:|---:|
{chr(10).join(lines)}

## Analysis
Conversion and revenue are evaluated together. Contribution has the same ordering as revenue under the configured common gross margin, but the formal experiment report remains the source for bootstrap confidence intervals, SRM, and guardrails.

## Metric impact
Primary: revenue per assigned user. Secondary: checkout/payment conversion. Guardrails: refunds and D30 retention.

## Interpretation
Point estimates alone are insufficient when sample size or intervals are weak.

## Recommendation
{recommendation}

## Limitations
Synthetic assignment, right-censored retention, and one configured price scenario limit generalization.
"""


def acquisition_case(root: Path) -> str:
    users: dict[str, str] = {}
    user_counts = Counter()
    for row in rows(root, "users", ["user_id", "acquisition_channel"]):
        users[row["user_id"]] = row["acquisition_channel"]
        user_counts[row["acquisition_channel"]] += 1
    revenue = defaultdict(float)
    for row in rows(root, "payments", ["user_id", "amount_usd", "refund_amount_usd", "status"]):
        if row["status"] in {"success", "refunded"}:
            revenue[users[row["user_id"]]] += float(row["amount_usd"] - row["refund_amount_usd"])
    spend = defaultdict(float)
    for row in rows(root, "marketing_spend", ["channel", "spend_usd"]):
        spend[row["channel"]] += float(row["spend_usd"])
    margin = next(rows(root, "generator_config", ["gross_margin"]))["gross_margin"]
    lines, ratios = [], {}
    for channel in sorted(user_counts):
        n = user_counts[channel]
        cac = spend[channel] / n if n else 0
        ltv = revenue[channel] * float(margin) / n if n else 0
        ratio = ltv / cac if cac else None
        ratios[channel] = ratio
        lines.append(f"| {channel} | {n} | ${cac:.2f} | ${ltv:.2f} | {ratio:.2f} |" if ratio is not None else
                     f"| {channel} | {n} | ${cac:.2f} | ${ltv:.2f} | n/a |")
    recommendation = ("Prefer incremental Referral investment over TikTok until TikTok cohort economics improve."
                      if ratios.get("referral", 0) > ratios.get("tiktok", 0) else
                      "Do not reallocate between Referral and TikTok from the current evidence.")
    return f"""# Acquisition quality

## Question
Which channels combine useful volume with contribution quality?

## Evidence
| Channel | Registrations | CAC | Observed contribution LTV | LTV/CAC |
|---|---:|---:|---:|---:|
{chr(10).join(lines)}

## Analysis
Registration volume is separated from contribution-based cohort quality. Spend and finance use synthetic USD FX fields.

## Metric impact
Registrations, CAC, observed contribution LTV, and LTV/CAC by channel.

## Interpretation
Low CAC is not sufficient when downstream contribution is weak.

## Recommendation
{recommendation}

## Limitations
Observed LTV is horizon-censored, attribution is synthetic, and payback should be confirmed on mature cohorts.
"""


def generate_reports(root: Path, output: Path) -> dict[str, str]:
    reports = {
        "android_incident": android_case(root),
        "pricing": pricing_case(root),
        "acquisition": acquisition_case(root),
    }
    for name, content in reports.items():
        target = output / name / "report.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    manifest = {"synthetic": True, "dataset": str(root), "reports": sorted(reports)}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic analytical business cases")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("business_cases"))
    args = parser.parse_args()
    reports = generate_reports(args.input, args.output)
    print(f"Generated {len(reports)} reports in {args.output}")


if __name__ == "__main__":
    main()
