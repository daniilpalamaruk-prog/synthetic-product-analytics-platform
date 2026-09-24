# Pricing experiment

## Question
Does new pricing create enough value to offset checkout friction?

## Evidence
| Variant | Assigned | Checkout conversion | Revenue / assigned user | Net revenue |
|---|---:|---:|---:|---:|
| control | 635 | 21.10% | $3.94 | $2505.00 |
| new_pricing | 617 | 18.64% | $4.31 | $2661.00 |

## Analysis
Conversion and revenue are evaluated together. Contribution has the same ordering as revenue under the configured common gross margin, but the formal experiment report remains the source for bootstrap confidence intervals, SRM, and guardrails.

## Metric impact
Primary: revenue per assigned user. Secondary: checkout/payment conversion. Guardrails: refunds and D30 retention.

## Interpretation
Point estimates alone are insufficient when sample size or intervals are weak.

## Recommendation
Continue only as a guarded experiment; use the formal CI/SRM report before rollout.

## Limitations
Synthetic assignment, right-censored retention, and one configured price scenario limit generalization.
