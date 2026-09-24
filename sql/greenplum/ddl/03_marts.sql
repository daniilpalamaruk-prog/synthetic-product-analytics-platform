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

-- Idempotent partition rebuild: delete the requested interval, then insert it again.
-- psql variables :interval_start and :interval_end are half-open UTC boundaries.
DELETE FROM marts.revenue_daily
WHERE payment_date >= :'interval_start'::date AND payment_date < :'interval_end'::date;

INSERT INTO marts.revenue_daily
SELECT payment_at::date,
       sum(amount_usd) FILTER (WHERE status IN ('success','refunded')),
       sum(refund_amount_usd),
       sum(amount_usd-refund_amount_usd) FILTER (WHERE status IN ('success','refunded')),
       count(DISTINCT user_id) FILTER (WHERE status IN ('success','refunded')),
       sum(amount_usd-refund_amount_usd) FILTER (WHERE status IN ('success','refunded'))
         / nullif(count(DISTINCT user_id) FILTER (WHERE status IN ('success','refunded')),0)
FROM core.fct_payments
WHERE payment_at >= :'interval_start'::timestamptz AND payment_at < :'interval_end'::timestamptz
GROUP BY payment_at::date;

DELETE FROM marts.product_daily
WHERE event_date >= :'interval_start'::date AND event_date < :'interval_end'::date;

INSERT INTO marts.product_daily
SELECT event_date, count(DISTINCT user_id),
       count(DISTINCT user_id) FILTER (WHERE event_name='signup'),
       count(DISTINCT user_id) FILTER (WHERE event_name='onboarding_completed')
FROM core.fct_events
WHERE event_date >= :'interval_start'::date AND event_date < :'interval_end'::date
GROUP BY event_date;
