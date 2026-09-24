# Data warehouse

## Layers

- Raw: minimally transformed, protected source records with ingestion metadata. Plain names/emails/phones/IPs are not loaded.
- Staging: normalized enums/types, deduplicated business keys, and invalid-row exclusion.
- Core: `dim_users`, `dim_plans`, `dim_campaigns`, `dim_date`, `fct_events`, `fct_payments`, `fct_subscriptions`, and `fct_experiments`.
- Marts: daily product/revenue/pipeline health in the fallback; the retained ClickHouse model adds funnel, retention, MRR, acquisition, experiments, feature adoption, platform quality, and unit economics.

## Grain and keys

| Relation | Grain | Business key |
|---|---|---|
| dim_users | one registered user | user_id |
| dim_user_plan_history | one user plan version | user_id + valid_from |
| fct_events | one event occurrence | event_id |
| fct_payments | one payment attempt/renewal | payment_id |
| fct_subscriptions | one subscription spell | subscription_id |
| fct_experiments | one assignment per experiment/user | experiment_id + user_id |
| mart_revenue_daily | one UTC payment date | payment_date |
| mart_product_daily | one UTC event date | event_date |

## SCD Type 2

Plan is historized because plan changes affect segmentation at event/payment time. Rows have `user_sk`, `user_id`, `plan`, `valid_from`, exclusive `valid_to`, and `is_current`. Adjacent duplicate plans collapse; a changed plan closes the current row and opens another. Other dimensions are not SCD2 because no analytical requirement justifies the complexity.

Verify with `pytest tests/test_warehouse.py -q` and the Greenplum checks in `05_data_quality_gate.sql`.
