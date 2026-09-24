# Statistical Analysis

`analysis/experiment_analysis.py` measures one selected synthetic run. It does not contain pre-filled outcomes and does not claim real business impact.

## Prespecified metric roles

Each experiment design is stored in `config/business_rules.yaml`:

- **Primary** — the single decision metric for the main hypothesis.
- **Secondary** — a prespecified family; Holm correction is applied only within this family and separately for each experiment.
- **Guardrails** — harm indicators reported separately, without being folded into the efficacy family.
- **Exploratory** — hypothesis-generating results, not confirmatory evidence.

The analysis is intent-to-treat: denominators contain assigned users, outcomes must occur at or after assignment, and immature D7/D30 cohorts are excluded only from the relevant retention metric. Revenue includes zero-revenue assigned users and uses USD converted at payment-date synthetic FX.

## Implemented checks and estimators

- Pearson chi-square sample-ratio-mismatch test against the configured split; `p < 0.01` raises `srm_detected`.
- Two-proportion z-test for binary metrics.
- Absolute/relative uplift and unpooled 95% confidence interval.
- Approximate observed power and 80%-power MDE for descriptive diagnostics.
- User-level bootstrap CI for revenue per assigned user in USD.
- Holm family-wise correction for the predefined secondary family only.

```bash
python analysis/experiment_analysis.py \
  --input data/small \
  --output data/small/experiment_report.json \
  --bootstrap-iterations 5000
```

Default `alpha=0.05` applies to outcome tests; SRM uses `alpha=0.01`. Observed power must not replace prospective sizing. Before interpreting outcomes, review SRM, assignment timing, metric maturity, confidence intervals and any guardrail movement. A non-significant result is inconclusive unless the experiment had adequate power for the decision-relevant effect.

Current generation intentionally assigns each user to at most one experiment. The persistent assignment key remains `(experiment_id, user_id)` so overlapping enrollment can be introduced later without changing relation grain.
