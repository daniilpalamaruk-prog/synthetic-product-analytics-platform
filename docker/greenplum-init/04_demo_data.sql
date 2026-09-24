-- Deterministic demo data used by the local Superset dashboards.
-- The guards make this script safe to run more than once.

INSERT INTO core.dim_users
SELECT md5('user-' || g)::uuid,
       'anon-' || g,
       timestamptz '2026-01-01 00:00:00+00' + (g % 120) * interval '1 day',
       (ARRAY['US','DE','BR','IN','GB'])[1 + (g % 5)],
       (ARRAY['web','ios','android'])[1 + (g % 3)],
       (ARRAY['organic','paid_search','social','partner','referral'])[1 + (g % 5)],
       'campaign-' || (1 + g % 20)
FROM generate_series(1, 10000) AS s(g)
WHERE NOT EXISTS (SELECT 1 FROM core.dim_users LIMIT 1);

INSERT INTO raw.marketing_spend
SELECT d::date,
       channel,
       'campaign-' || (1 + channel_no * 4 + extract(day FROM d)::int % 4),
       'US',
       (180 + channel_no * 35 + extract(day FROM d)::int * 2)::numeric(18,2),
       8 + channel_no,
       now(), 'demo-seed', 'synthetic', '04_demo_data.sql'
FROM generate_series(date '2026-01-01', date '2026-08-31', interval '1 day') AS days(d)
CROSS JOIN (VALUES (0,'organic'),(1,'paid_search'),(2,'social'),(3,'partner'),(4,'referral')) AS c(channel_no,channel)
WHERE NOT EXISTS (SELECT 1 FROM raw.marketing_spend LIMIT 1);

-- Exact D1/D7/D30/D90 activity makes the retention heatmap meaningful.
INSERT INTO core.fct_events
SELECT md5('retention-event-' || u.g || '-' || a.age_day)::uuid,
       md5('user-' || u.g)::uuid,
       md5('retention-session-' || u.g || '-' || a.age_day)::uuid,
       timestamptz '2026-01-01 09:00:00+00' + (u.g % 120) * interval '1 day' + a.age_day * interval '1 day',
       date '2026-01-01' + (u.g % 120) + a.age_day,
       'login', NULL,
       (ARRAY['web','ios','android'])[1 + (u.g % 3)],
       (ARRAY['windows','ios','android'])[1 + (u.g % 3)],
       CASE WHEN u.g % 5 = 0 THEN '3.7.0' ELSE '3.8.1' END,
       NULL, NULL, '{}'::jsonb, now(), 'demo-seed', 'synthetic', '04_demo_data.sql'
FROM generate_series(1, 10000) AS u(g)
CROSS JOIN (VALUES (1),(7),(30),(90)) AS a(age_day)
WHERE NOT EXISTS (SELECT 1 FROM core.fct_events LIMIT 1);

-- Product usage and funnel events across eight months.
INSERT INTO core.fct_events
SELECT md5('activity-event-' || g)::uuid,
       md5('user-' || (1 + g % 10000))::uuid,
       md5('activity-session-' || (g / 4))::uuid,
       timestamptz '2026-01-01 00:00:00+00' + (g % 240) * interval '1 day' + (g % 24) * interval '1 hour',
       date '2026-01-01' + (g % 240),
       (ARRAY['signup','onboarding_completed','feature_viewed','feature_used','checkout_started','login'])[1 + (g % 6)],
       CASE WHEN g % 6 IN (2,3) THEN (ARRAY['reports','automation','collaboration'])[1 + (g % 3)] END,
       (ARRAY['web','ios','android'])[1 + (g % 3)],
       (ARRAY['windows','ios','android'])[1 + (g % 3)],
       CASE WHEN g % 10 < 2 THEN '3.7.0' ELSE '3.8.1' END,
       NULL, NULL,
       '{}'::jsonb, now(), 'demo-activity', 'synthetic', '04_demo_data.sql'
FROM generate_series(1, 120000) AS s(g)
WHERE EXISTS (SELECT 1 FROM core.fct_events LIMIT 1)
  AND NOT EXISTS (SELECT 1 FROM core.fct_events WHERE batch_id='demo-activity' LIMIT 1);

-- Payment attempts: Android 3.7.0 has a visible, intentional success-rate dip.
INSERT INTO core.fct_events
SELECT md5('payment-attempt-' || g)::uuid,
       md5('user-' || (1 + g % 10000))::uuid,
       md5('payment-session-' || g)::uuid,
       timestamptz '2026-07-01 00:00:00+00' + (g % 1440) * interval '1 hour',
       date '2026-07-01' + (g % 1440) / 24,
       'payment_attempted', NULL,
       CASE WHEN g % 4 = 0 THEN 'android' WHEN g % 4 = 1 THEN 'ios' ELSE 'web' END,
       CASE WHEN g % 4 = 0 THEN 'android' WHEN g % 4 = 1 THEN 'ios' ELSE 'windows' END,
       CASE WHEN g % 4 = 0 THEN '3.7.0' ELSE '3.8.1' END,
       NULL, NULL, '{}'::jsonb, now(), 'demo-payments', 'synthetic', '04_demo_data.sql'
FROM generate_series(1, 20000) AS s(g)
WHERE NOT EXISTS (SELECT 1 FROM core.fct_events WHERE batch_id='demo-payments' LIMIT 1);

INSERT INTO core.fct_events
SELECT md5('payment-success-' || g)::uuid,
       md5('user-' || (1 + g % 10000))::uuid,
       md5('payment-session-' || g)::uuid,
       timestamptz '2026-07-01 00:00:00+00' + (g % 1440) * interval '1 hour' + interval '2 minutes',
       date '2026-07-01' + (g % 1440) / 24,
       CASE WHEN g % 4 = 0 AND g % 10 < 3 THEN 'payment_failed' ELSE 'payment_success' END,
       NULL,
       CASE WHEN g % 4 = 0 THEN 'android' WHEN g % 4 = 1 THEN 'ios' ELSE 'web' END,
       CASE WHEN g % 4 = 0 THEN 'android' WHEN g % 4 = 1 THEN 'ios' ELSE 'windows' END,
       CASE WHEN g % 4 = 0 THEN '3.7.0' ELSE '3.8.1' END,
       NULL, NULL, '{}'::jsonb, now(), 'demo-payment-results', 'synthetic', '04_demo_data.sql'
FROM generate_series(1, 20000) AS s(g)
WHERE NOT EXISTS (SELECT 1 FROM core.fct_events WHERE batch_id='demo-payment-results' LIMIT 1);

INSERT INTO core.fct_payments
SELECT md5('payment-' || g)::uuid,
       md5('user-' || (1 + g % 10000))::uuid,
       md5('subscription-' || (1 + g % 7000))::uuid,
       timestamptz '2026-01-01 12:00:00+00' + (g % 240) * interval '1 day',
       (ARRAY[19,49,99])[1 + (g % 3)]::numeric(18,2),
       CASE WHEN g % 23 = 0 THEN 19 ELSE 0 END,
       'USD', CASE WHEN g % 23 = 0 THEN 'refunded' ELSE 'success' END,
       now(), 'demo-seed', 'synthetic', '04_demo_data.sql'
FROM generate_series(1, 8000) AS s(g)
WHERE NOT EXISTS (SELECT 1 FROM core.fct_payments LIMIT 1);

INSERT INTO core.fct_experiments
SELECT 'checkout_copy_v2', md5('user-' || g)::uuid,
       CASE WHEN g % 2 = 0 THEN 'control' ELSE 'treatment' END,
       timestamptz '2026-04-01 00:00:00+00'
FROM generate_series(1, 8000) AS s(g)
WHERE NOT EXISTS (SELECT 1 FROM core.fct_experiments LIMIT 1);

INSERT INTO core.fct_events
SELECT md5('experiment-checkout-' || g)::uuid,
       md5('user-' || g)::uuid,
       md5('experiment-session-' || g)::uuid,
       timestamptz '2026-04-02 10:00:00+00' + (g % 30) * interval '1 day',
       date '2026-04-02' + (g % 30),
       'checkout_started', NULL,
       (ARRAY['web','ios','android'])[1 + (g % 3)],
       (ARRAY['windows','ios','android'])[1 + (g % 3)], '3.8.1',
       'checkout_copy_v2', CASE WHEN g % 2 = 0 THEN 'control' ELSE 'treatment' END,
       '{}'::jsonb, now(), 'demo-experiment', 'synthetic', '04_demo_data.sql'
FROM generate_series(1, 8000) AS s(g)
WHERE ((g % 2 = 0 AND (g / 2) % 100 < 40)
    OR (g % 2 = 1 AND (g / 2) % 100 < 47))
  AND NOT EXISTS (SELECT 1 FROM core.fct_events WHERE batch_id='demo-experiment' LIMIT 1);

INSERT INTO core.fct_events
SELECT md5('experiment-payment-' || g)::uuid,
       md5('user-' || g)::uuid,
       md5('experiment-session-' || g)::uuid,
       timestamptz '2026-04-02 10:10:00+00' + (g % 30) * interval '1 day',
       date '2026-04-02' + (g % 30),
       'payment_success', NULL,
       (ARRAY['web','ios','android'])[1 + (g % 3)],
       (ARRAY['windows','ios','android'])[1 + (g % 3)], '3.8.1',
       'checkout_copy_v2', CASE WHEN g % 2 = 0 THEN 'control' ELSE 'treatment' END,
       '{}'::jsonb, now(), 'demo-experiment-payment', 'synthetic', '04_demo_data.sql'
FROM generate_series(1, 8000) AS s(g)
WHERE ((g % 2 = 0 AND (g / 2) % 100 < 20)
    OR (g % 2 = 1 AND (g / 2) % 100 < 23))
  AND NOT EXISTS (SELECT 1 FROM core.fct_events WHERE batch_id='demo-experiment-payment' LIMIT 1);

INSERT INTO marts.revenue_daily
SELECT payment_at::date, sum(amount_usd), sum(refund_amount_usd),
       sum(amount_usd-refund_amount_usd), count(DISTINCT user_id),
       sum(amount_usd-refund_amount_usd)/nullif(count(DISTINCT user_id),0)
FROM core.fct_payments
WHERE NOT EXISTS (SELECT 1 FROM marts.revenue_daily LIMIT 1)
GROUP BY 1;

INSERT INTO marts.product_daily
SELECT event_date, count(DISTINCT user_id),
       count(DISTINCT user_id) FILTER (WHERE event_name='signup'),
       count(DISTINCT user_id) FILTER (WHERE event_name='feature_used')
FROM core.fct_events
WHERE NOT EXISTS (SELECT 1 FROM marts.product_daily LIMIT 1)
GROUP BY 1;
