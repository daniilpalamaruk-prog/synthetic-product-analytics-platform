CREATE TABLE IF NOT EXISTS marts.revenue_daily (
    payment_date date NOT NULL, gross_revenue_usd numeric(20,2) NOT NULL,
    refunds_usd numeric(20,2) NOT NULL, net_revenue_usd numeric(20,2) NOT NULL,
    paid_users bigint NOT NULL, arppu_usd numeric(20,4)
) DISTRIBUTED BY (payment_date);

CREATE TABLE IF NOT EXISTS marts.product_daily (
    event_date date NOT NULL, active_users bigint NOT NULL, signups bigint NOT NULL,
    activated_users bigint NOT NULL
) DISTRIBUTED BY (event_date);

CREATE TABLE IF NOT EXISTS marts.pipeline_health (
    dag text NOT NULL, run_id text NOT NULL, started_at timestamptz NOT NULL,
    finished_at timestamptz, duration_seconds numeric, status text NOT NULL,
    rows_processed bigint, freshness_seconds numeric, sla_met boolean NOT NULL
) DISTRIBUTED BY (run_id);

CREATE OR REPLACE VIEW marts.funnel_daily AS
SELECT event_date,device_type,app_version,
       count(DISTINCT user_id) FILTER (WHERE event_name='signup') AS signups,
       count(DISTINCT user_id) FILTER (WHERE event_name='onboarding_completed') AS onboarding_users,
       count(DISTINCT user_id) FILTER (WHERE event_name='feature_used') AS core_feature_users,
       count(DISTINCT user_id) FILTER (WHERE event_name='checkout_started') AS checkout_users,
       count(DISTINCT user_id) FILTER (WHERE event_name='payment_success') AS paid_users
FROM core.fct_events GROUP BY event_date,device_type,app_version;

CREATE OR REPLACE VIEW marts.retention_cohort AS
SELECT date_trunc('month',u.registration_at)::date AS cohort_month,
       (e.event_date-u.registration_at::date) AS age_day,
       u.acquisition_channel,count(DISTINCT e.user_id) AS retained_users
FROM core.fct_events e JOIN core.dim_users u USING(user_id)
WHERE e.event_name IN ('login','feature_viewed','feature_used')
  AND (e.event_date-u.registration_at::date) IN (1,7,30,90)
GROUP BY 1,2,3;

CREATE OR REPLACE VIEW marts.platform_quality AS
SELECT date_trunc('hour',event_time) AS event_hour,device_type,app_version,
       count(*) FILTER (WHERE event_name='payment_attempted') AS payment_attempts,
       count(*) FILTER (WHERE event_name='payment_success') AS payment_successes,
       count(*) FILTER (WHERE event_name='payment_success')::numeric /
         nullif(count(*) FILTER (WHERE event_name='payment_attempted'),0) AS payment_success_rate
FROM core.fct_events
WHERE event_name IN ('payment_attempted','payment_success','payment_failed')
GROUP BY 1,2,3;

CREATE OR REPLACE VIEW marts.experiments AS
SELECT a.experiment_id,a.variant,count(DISTINCT a.user_id) AS sample_size,
       count(DISTINCT e.user_id) FILTER (WHERE e.event_name='checkout_started')::numeric /
         nullif(count(DISTINCT a.user_id),0) AS checkout_conversion,
       count(DISTINCT e.user_id) FILTER (WHERE e.event_name='payment_success')::numeric /
         nullif(count(DISTINCT a.user_id),0) AS paid_conversion
FROM core.fct_experiments a
LEFT JOIN core.fct_events e ON e.user_id=a.user_id
 AND e.event_time>=a.assigned_at AND e.experiment_id=a.experiment_id
GROUP BY a.experiment_id,a.variant;

CREATE OR REPLACE VIEW marts.acquisition AS
WITH users_by_channel AS (
  SELECT acquisition_channel,count(*) AS registrations FROM core.dim_users GROUP BY 1
), spend AS (
  SELECT channel,sum(spend_usd) AS spend_usd FROM raw.marketing_spend GROUP BY 1
), contribution AS (
  SELECT u.acquisition_channel,sum(p.amount_usd-p.refund_amount_usd)*max(g.gross_margin) AS contribution_usd
  FROM core.fct_payments p JOIN core.dim_users u USING(user_id)
  CROSS JOIN ops.metric_parameters g
  WHERE p.status IN ('success','refunded') GROUP BY 1
)
SELECT u.acquisition_channel,u.registrations,
       s.spend_usd/nullif(u.registrations,0) AS cac_usd,
       c.contribution_usd/nullif(u.registrations,0) AS observed_contribution_ltv_usd,
       c.contribution_usd/nullif(s.spend_usd,0) AS ltv_cac
FROM users_by_channel u LEFT JOIN spend s ON s.channel=u.acquisition_channel
LEFT JOIN contribution c USING(acquisition_channel);
