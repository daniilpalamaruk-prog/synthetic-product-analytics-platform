# Metric dictionary and ownership

All analytical metrics use clean/deduplicated data, UTC calendar windows, and synthetic daily FX-converted USD for cross-country finance.

| Metric | Definition | Source of truth | Grain/window | Owner |
|---|---|---|---|---|
| Revenue | successful/refunded payment amount minus refunds | fct_payments | payment day/month | Finance analytics |
| DAU/WAU/MAU | distinct active users in 1/7/30-day windows | fct_events | UTC day | Product analytics |
| Activation | onboarding complete and at least two core features within 3 days | fct_events + dim_users | registration cohort | Product analytics |
| D1/D7/D30/D90 | cohort users active on exact age day / eligible cohort | fct_events + dim_users | cohort x age day | Product analytics |
| ARPPU | net recognized revenue / distinct successful payers | fct_payments | month | Finance analytics |
| MRR | USD monthly price of spells active at calendar month end | fct_subscriptions | month end | Finance analytics |
| New MRR | MRR from first paid spell starting in period | fct_subscriptions | month | Finance analytics |
| Churned MRR | prior recurring amount ending in period without continuation | fct_subscriptions | month | Finance analytics |
| Expansion/contraction | positive/negative plan-price movement | plan SCD2 + subscriptions | month | Finance analytics |
| CAC | marketing spend USD / attributed acquired customers | spend + dim_users | cohort month x channel | Growth analytics |
| LTV | cumulative net revenue USD x gross margin / acquired users | payments/users/config | cohort x age month | Growth/Finance |
| LTV/CAC | contribution LTV / CAC per acquired user | unit economics mart | cohort/channel | Growth analytics |
| Payback | first age month cumulative contribution per user >= CAC | unit economics mart | cohort/channel | Growth analytics |
| Payment success | successful attempts / all payment attempts | events/payments | time x platform x version | Product reliability |
| Experiment conversion | assigned users reaching declared post-assignment outcome / eligible assigned users | assignments + events | experiment x variant | Experiment owner |

Rules: failed payments never count as revenue; refunds are subtracted; local currencies are never summed directly; incomplete cohorts are excluded from mature retention/conversion; organic CAC is reported separately when spend is zero. Experiment output includes sample size, absolute/relative uplift, 95% CI, p-value, SRM, metric role, and uncertainty—never an automatic winner.
