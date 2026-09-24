-- Ten required analytical marts. Apply clickhouse_ddl.sql, staging.sql and intermediate.sql first.

CREATE VIEW IF NOT EXISTS synthetic_saas.mart_product_daily AS
SELECT event_date,
       uniqExactIf(user_id, event_name IN ('login','feature_viewed','feature_used')) AS dau,
       uniqExactIf(user_id, event_name = 'signup') AS signups,
       uniqExactIf(user_id, event_name = 'onboarding_completed') AS onboarded_users,
       uniqExactIf(user_id, event_name = 'feature_used') AS feature_users
FROM synthetic_saas.events GROUP BY event_date;

CREATE VIEW IF NOT EXISTS synthetic_saas.mart_acquisition AS
WITH spend AS (
  SELECT toStartOfMonth(date) month, channel, country, sum(spend_usd) spend_usd
  FROM synthetic_saas.marketing_spend GROUP BY month, channel, country
), cohorts AS (
  SELECT toStartOfMonth(registration_date) cohort_month, acquisition_channel, country,
         uniqExact(user_id) acquired_users, sum(net_revenue_usd) cohort_net_revenue_usd
  FROM synthetic_saas.int_user_revenue GROUP BY cohort_month, acquisition_channel, country
)
SELECT c.cohort_month, c.acquisition_channel, c.country, c.acquired_users, s.spend_usd,
       s.spend_usd / nullIf(c.acquired_users, 0) AS cac_usd, c.cohort_net_revenue_usd
FROM cohorts c LEFT JOIN spend s
ON s.month = c.cohort_month AND s.channel = c.acquisition_channel AND s.country = c.country;

CREATE VIEW IF NOT EXISTS synthetic_saas.mart_funnel_daily AS
SELECT event_date, device_type, app_version,
       uniqExactIf(user_id, event_name = 'signup') AS signup_users,
       uniqExactIf(user_id, event_name = 'onboarding_completed') AS onboarded_users,
       uniqExactIf(user_id, event_name = 'checkout_started') AS checkout_users,
       uniqExactIf(user_id, event_name = 'payment_success') AS payer_users
FROM synthetic_saas.events GROUP BY event_date, device_type, app_version;

CREATE VIEW IF NOT EXISTS synthetic_saas.mart_retention_cohort AS
SELECT u.registration_date AS cohort_date, u.acquisition_channel, a.activated,
       dateDiff('day', u.registration_date, e.event_date) AS age_day,
       uniqExact(e.user_id) AS retained_users
FROM synthetic_saas.events e
INNER JOIN synthetic_saas.users u ON u.user_id = e.user_id
LEFT JOIN synthetic_saas.int_user_activation a ON a.user_id = u.user_id
WHERE e.event_name IN ('login','feature_viewed','feature_used') AND age_day IN (1,7,30,90)
GROUP BY cohort_date, u.acquisition_channel, a.activated, age_day;

CREATE VIEW IF NOT EXISTS synthetic_saas.mart_subscriptions AS
WITH months AS (
  SELECT DISTINCT toStartOfMonth(logical_date) AS month_start FROM synthetic_saas.pipeline_runs
), ending AS (
  SELECT m.month_start,
         uniqExactIf(s.subscription_id,
           s.started_at < addMonths(m.month_start, 1)
           AND (s.ended_at IS NULL OR s.ended_at >= addMonths(m.month_start, 1))) AS active_subscriptions,
         sumIf(s.monthly_price_usd,
           s.started_at < addMonths(m.month_start, 1)
           AND (s.ended_at IS NULL OR s.ended_at >= addMonths(m.month_start, 1))) AS ending_mrr_usd
  FROM months m CROSS JOIN synthetic_saas.subscriptions s GROUP BY m.month_start
), new_logo AS (
  SELECT toStartOfMonth(s.started_at) month_start,
         sumIf(s.monthly_price_usd, t.new_subscription_id IS NULL) new_mrr_usd
  FROM synthetic_saas.subscriptions s
  LEFT JOIN synthetic_saas.int_subscription_transitions t ON t.new_subscription_id = s.subscription_id
  GROUP BY month_start
), churn AS (
  SELECT toStartOfMonth(s.ended_at) month_start,
         sumIf(s.monthly_price_usd, s.ended_at IS NOT NULL AND t.old_subscription_id IS NULL) churned_mrr_usd
  FROM synthetic_saas.subscriptions s
  LEFT JOIN synthetic_saas.int_subscription_transitions t ON t.old_subscription_id = s.subscription_id
  WHERE s.ended_at IS NOT NULL GROUP BY month_start
), changes AS (
  SELECT toStartOfMonth(changed_at) month_start,
         sumIf(mrr_delta_usd, mrr_delta_usd > 0) expansion_mrr_usd,
         sumIf(-mrr_delta_usd, mrr_delta_usd < 0) contraction_mrr_usd
  FROM synthetic_saas.int_subscription_transitions GROUP BY month_start
)
SELECT m.month_start AS month,
       coalesce(n.new_mrr_usd, 0) AS new_mrr_usd,
       coalesce(c.churned_mrr_usd, 0) AS churned_mrr_usd,
       coalesce(x.expansion_mrr_usd, 0) AS expansion_mrr_usd,
       coalesce(x.contraction_mrr_usd, 0) AS contraction_mrr_usd,
       e.active_subscriptions, e.ending_mrr_usd,
       e.ending_mrr_usd * 12 AS ending_arr_usd
FROM months m
LEFT JOIN ending e USING month_start
LEFT JOIN new_logo n USING month_start
LEFT JOIN churn c USING month_start
LEFT JOIN changes x USING month_start
ORDER BY month;

CREATE VIEW IF NOT EXISTS synthetic_saas.mart_revenue AS
SELECT toDate(p.payment_at) AS payment_date, s.plan, u.acquisition_channel, p.currency,
       sumIf(p.amount_local, p.status IN ('success','refunded')) AS gross_revenue_local,
       sum(p.refund_amount_local) AS refunds_local, gross_revenue_local - refunds_local AS net_revenue_local,
       sumIf(p.amount_usd, p.status IN ('success','refunded')) AS gross_revenue_usd,
       sum(p.refund_amount_usd) AS refunds_usd, gross_revenue_usd - refunds_usd AS net_revenue_usd,
       uniqExactIf(p.user_id, p.status IN ('success','refunded')) AS payers,
       countIf(p.status = 'failed') / nullIf(count(), 0) AS payment_failure_rate
FROM synthetic_saas.payments p
LEFT JOIN synthetic_saas.subscriptions s ON s.subscription_id = p.subscription_id
LEFT JOIN synthetic_saas.users u ON u.user_id = p.user_id
GROUP BY payment_date, s.plan, u.acquisition_channel, p.currency;

CREATE VIEW IF NOT EXISTS synthetic_saas.mart_unit_economics AS
WITH gm AS (SELECT any(gross_margin) gross_margin FROM synthetic_saas.generator_config),
spend AS (
  SELECT toStartOfMonth(date) cohort_month, channel acquisition_channel, sum(spend_usd) spend_usd
  FROM synthetic_saas.marketing_spend GROUP BY cohort_month, acquisition_channel
), cohorts AS (
  SELECT toStartOfMonth(registration_date) cohort_month, acquisition_channel,
         uniqExact(user_id) acquired_users
  FROM synthetic_saas.users GROUP BY cohort_month, acquisition_channel
), monthly_revenue AS (
  SELECT toStartOfMonth(u.registration_date) cohort_month, u.acquisition_channel,
         dateDiff('month', toStartOfMonth(u.registration_date), toStartOfMonth(p.payment_at)) month_number,
         sumIf(p.amount_usd - p.refund_amount_usd, p.status IN ('success','refunded')) net_revenue_usd
  FROM synthetic_saas.users u INNER JOIN synthetic_saas.payments p ON p.user_id = u.user_id
  GROUP BY cohort_month, u.acquisition_channel, month_number
), grid AS (
  SELECT c.cohort_month, c.acquisition_channel, c.acquired_users, number AS month_number
  FROM cohorts c
  ARRAY JOIN range(toUInt32(dateDiff('month', c.cohort_month,
    toStartOfMonth((SELECT max(period_end) FROM synthetic_saas.generator_config))) + 1)) AS number
), monthly AS (
  SELECT g.cohort_month, g.acquisition_channel, g.acquired_users, g.month_number,
         coalesce(r.net_revenue_usd, 0) AS monthly_net_revenue_usd,
         coalesce(s.spend_usd, 0) / nullIf(g.acquired_users, 0) AS cac_usd,
         monthly_net_revenue_usd * gm.gross_margin AS monthly_contribution_usd
  FROM grid g
  LEFT JOIN monthly_revenue r USING (cohort_month, acquisition_channel, month_number)
  LEFT JOIN spend s USING (cohort_month, acquisition_channel)
  CROSS JOIN gm
), curve AS (
  SELECT *,
         sum(monthly_net_revenue_usd) OVER (
           PARTITION BY cohort_month, acquisition_channel ORDER BY month_number) AS cumulative_net_revenue_usd,
         sum(monthly_contribution_usd) OVER (
           PARTITION BY cohort_month, acquisition_channel ORDER BY month_number) AS cumulative_contribution_usd
  FROM monthly
), payback AS (
  SELECT cohort_month, acquisition_channel,
         if(countIf(cumulative_contribution_usd / acquired_users >= cac_usd) > 0,
            toNullable(minIf(month_number, cumulative_contribution_usd / acquired_users >= cac_usd)),
            CAST(NULL, 'Nullable(UInt64)')) AS payback_month
  FROM curve GROUP BY cohort_month, acquisition_channel
)
SELECT c.cohort_month, c.acquisition_channel, c.month_number, c.acquired_users,
       c.monthly_net_revenue_usd, c.monthly_contribution_usd, c.cac_usd,
       c.cumulative_net_revenue_usd / nullIf(c.acquired_users, 0) AS realized_ltv_usd,
       c.cumulative_contribution_usd / nullIf(c.acquired_users, 0) AS contribution_ltv_usd,
       contribution_ltv_usd / nullIf(c.cac_usd, 0) AS ltv_cac,
       p.payback_month
FROM curve c LEFT JOIN payback p USING (cohort_month, acquisition_channel)
ORDER BY c.cohort_month, c.acquisition_channel, c.month_number;

CREATE VIEW IF NOT EXISTS synthetic_saas.mart_experiments AS
SELECT a.experiment_id, a.variant,
       uniqExact(a.user_id) AS assigned_users,
       uniqExactIf(a.user_id, e.event_name = 'onboarding_completed') AS onboarding_users,
       uniqExactIf(a.user_id, e.event_name = 'payment_success') AS payer_users,
       uniqExactIf(a.user_id, e.event_name = 'notification_disabled') AS notification_disabled_users
FROM synthetic_saas.experiment_assignments a
LEFT JOIN synthetic_saas.events e ON e.user_id = a.user_id AND e.event_time >= a.assigned_at
GROUP BY a.experiment_id, a.variant;

CREATE VIEW IF NOT EXISTS synthetic_saas.mart_feature_adoption AS
SELECT toStartOfMonth(u.registration_date) AS cohort_month, e.feature_name, u.acquisition_channel,
       uniqExact(e.user_id) AS adopters, count() AS uses,
       uniqExactIf(e.user_id, dateDiff('day', u.registration_date, e.event_date) = 30) AS d30_users
FROM synthetic_saas.events e INNER JOIN synthetic_saas.users u ON u.user_id = e.user_id
WHERE e.event_name = 'feature_used' AND e.feature_name IS NOT NULL
GROUP BY cohort_month, e.feature_name, u.acquisition_channel;

CREATE VIEW IF NOT EXISTS synthetic_saas.mart_platform_quality AS
SELECT toStartOfHour(event_time) AS hour, device_type, os, app_version,
       uniqExactIf(user_id, event_name = 'checkout_started') AS checkout_users,
       countIf(event_name = 'payment_attempted') AS payment_attempts,
       countIf(event_name = 'payment_success') AS payment_successes,
       payment_successes / nullIf(payment_attempts, 0) AS payment_success_rate
FROM synthetic_saas.events
WHERE event_name IN ('checkout_started','payment_attempted','payment_success','payment_failed')
GROUP BY hour, device_type, os, app_version;
