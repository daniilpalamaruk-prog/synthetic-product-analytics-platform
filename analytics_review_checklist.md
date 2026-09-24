# Analytics Review Checklist

## SQL

- [ ] Output grain and candidate key are declared.
- [ ] Every join has justified cardinality; possible fanout is measured.
- [ ] Null behavior and default values are intentional.
- [ ] Numerator and denominator use the same eligible population.
- [ ] UTC/business timezone and calendar boundaries are explicit.
- [ ] Raw duplicates are excluded or deliberately measured.
- [ ] Partition filters and expected scan volume are reviewed.

## Experiments

- [ ] Hypothesis and direction were defined before analysis.
- [ ] Primary metric and guardrails were chosen in advance.
- [ ] Assignment unit, eligibility and intent-to-treat population are correct.
- [ ] Sample size, MDE, alpha and power are documented.
- [ ] Confidence interval is reported with the point estimate.
- [ ] Statistical test matches the metric distribution.
- [ ] Sample-ratio mismatch and metric maturity are checked.
- [ ] Multiple comparisons and negative guardrails are addressed.

## Metrics

- [ ] Business definition, owner and source of truth are documented.
- [ ] Numerator, denominator, exclusions, grain and time window are explicit.
- [ ] Currency, refunds, censoring and late-arrival treatment are explicit where relevant.
- [ ] Change is classified as backward-compatible or breaking.

## Communication

- [ ] Generator facts are separated from measured analytical findings.
- [ ] Simulated incidents and synthetic benchmarks are labeled.
- [ ] Recommendations use “Proposed decision” and include uncertainty/risks.
- [ ] No claim implies real production impact or mentoring experience.

