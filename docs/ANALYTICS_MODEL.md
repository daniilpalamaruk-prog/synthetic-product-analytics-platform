# Analytics Model

```text
raw Parquet → staging validation → intermediate user journeys → marts
                    ├─ invalid → quarantine
                    └─ valid   → clean
```

## Source grain

| Relation | Grain | Primary key |
|---|---|---|
| users / dim_users | one row per registered user | user_id |
| sessions | one row per user activity day/session | session_id |
| events / fct_events | one row per event occurrence | event_id |
| subscriptions | one row per subscription spell | subscription_id |
| payments / fct_payments | one row per payment attempt/renewal | payment_id |
| marketing_spend | one row per date × channel × campaign × country | composite |
| fx_rates | one row per date × currency | composite |
| experiments | one row per experiment | experiment_id |
| experiment_assignments | one row per experiment × assigned user | composite |
| feature_catalog | one row per feature | feature_name |
| app_releases | one row per platform release record | platform × version × release |
| business_timeline | one row per declared synthetic story event | story_month × story_event |
| generator_config | one row per generated run configuration | config_id |
| pipeline_runs | one row per synthetic logical daily pipeline run | run_id |

Raw intentionally may violate keys. Clean is the source for analysis. Local monetary aliases (`amount`, `spend`, `monthly_price`) remain for compatibility; financial aggregation uses explicit `*_usd` fields. Staging casts and renames; intermediate models compute activation, user revenue and subscription plan transitions.

## Recommended marts

| Mart | Grain | Purpose |
|---|---|---|
| mart_product_daily | date | DAU, signups, activation, feature use |
| mart_acquisition | registration cohort × channel × country | CAC and downstream quality |
| mart_funnel_daily | date × platform × app version | lifecycle conversion |
| mart_retention_cohort | registration cohort × age day × segment | cohort retention |
| mart_subscriptions | calendar month | historical month-end MRR, new/churned/expansion/contraction MRR |
| mart_revenue | payment date × plan × channel × currency | local and USD revenue/refunds |
| mart_unit_economics | cohort × channel × age month | cumulative USD LTV and first cumulative-contribution payback |
| mart_experiments | experiment × variant | users, funnel, revenue, retention |
| mart_feature_adoption | cohort × feature | adoption and retained-user association |
| mart_platform_quality | hour/day × platform × version | failure rate and incident detection |

`sql/marts.sql` provides executable baseline views for all ten marts. `sql/staging.sql` and `sql/intermediate.sql` implement the preceding layers. A production adaptation should materialize/incrementalize by event date and replace source views with orchestrated models.
