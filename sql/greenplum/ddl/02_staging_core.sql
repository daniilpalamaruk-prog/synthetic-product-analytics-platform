CREATE OR REPLACE VIEW staging.users AS
SELECT DISTINCT ON (user_id)
       user_id, anonymous_user_id, registration_at, upper(country) AS country,
       lower(device_type) AS device_type, lower(acquisition_channel) AS acquisition_channel,
       campaign_id, lower(initial_plan) AS initial_plan
FROM raw.users
ORDER BY user_id, ingestion_timestamp DESC;

CREATE OR REPLACE VIEW staging.events AS
SELECT DISTINCT ON (event_id)
       event_id,user_id,session_id,event_time,event_date,lower(event_name) AS event_name,
       feature_name,lower(device_type) AS device_type,os,app_version,experiment_id,experiment_variant
FROM raw.events
WHERE user_id IS NOT NULL AND event_time IS NOT NULL
ORDER BY event_id, ingestion_timestamp DESC;

CREATE OR REPLACE VIEW staging.payments AS
SELECT DISTINCT ON (payment_id)
       payment_id,user_id,subscription_id,payment_at,amount_usd,refund_amount_usd,currency,lower(status) status
FROM raw.payments
WHERE amount_usd >= 0 AND refund_amount_usd >= 0
ORDER BY payment_id, ingestion_timestamp DESC;

CREATE TABLE IF NOT EXISTS core.dim_users (
    user_id uuid NOT NULL, anonymous_user_id text NOT NULL, registration_at timestamptz NOT NULL,
    country text NOT NULL, device_type text NOT NULL, acquisition_channel text NOT NULL,
    campaign_id text NOT NULL
) DISTRIBUTED BY (user_id);

CREATE TABLE IF NOT EXISTS core.dim_user_plan_history (
    user_sk bigserial, user_id uuid NOT NULL, plan text NOT NULL,
    valid_from timestamptz NOT NULL, valid_to timestamptz, is_current boolean NOT NULL,
    UNIQUE (user_id, valid_from)
) DISTRIBUTED BY (user_id);

CREATE TABLE IF NOT EXISTS core.dim_plans (
    plan text NOT NULL, plan_rank smallint NOT NULL
) DISTRIBUTED REPLICATED;

CREATE TABLE IF NOT EXISTS core.dim_campaigns (
    campaign_id text NOT NULL, channel text NOT NULL
) DISTRIBUTED REPLICATED;

CREATE TABLE IF NOT EXISTS core.dim_date (
    date_key date NOT NULL, year smallint NOT NULL, month smallint NOT NULL, day smallint NOT NULL
) DISTRIBUTED REPLICATED;

CREATE TABLE IF NOT EXISTS core.fct_events (LIKE raw.events)
WITH (appendoptimized=true, orientation=column, compresstype=zstd, compresslevel=3)
DISTRIBUTED BY (user_id)
PARTITION BY RANGE (event_date)
(START (date '2025-01-01') INCLUSIVE END (date '2027-01-01') EXCLUSIVE EVERY (INTERVAL '1 month'));

CREATE TABLE IF NOT EXISTS core.fct_payments (LIKE raw.payments)
WITH (appendoptimized=true, orientation=column, compresstype=zstd, compresslevel=3)
DISTRIBUTED BY (user_id)
PARTITION BY RANGE (payment_at)
(START (timestamptz '2025-01-01') INCLUSIVE END (timestamptz '2027-01-01') EXCLUSIVE EVERY (INTERVAL '1 month'));

CREATE TABLE IF NOT EXISTS core.fct_subscriptions (LIKE raw.subscriptions)
DISTRIBUTED BY (user_id);

CREATE TABLE IF NOT EXISTS core.fct_experiments (
    experiment_id text NOT NULL, user_id uuid NOT NULL, variant text NOT NULL, assigned_at timestamptz NOT NULL
) DISTRIBUTED BY (user_id);
