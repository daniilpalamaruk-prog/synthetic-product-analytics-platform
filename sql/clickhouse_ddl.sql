-- ClickHouse baseline. Replace /path/to/data with an absolute dataset path.
CREATE DATABASE IF NOT EXISTS synthetic_saas;

CREATE TABLE IF NOT EXISTS synthetic_saas.events
(
    event_id UUID,
    user_id Nullable(UUID),
    session_id UUID,
    event_time DateTime64(3, 'UTC'),
    event_date Date,
    event_name LowCardinality(String),
    feature_name Nullable(LowCardinality(String)),
    device_type LowCardinality(String),
    os LowCardinality(String),
    app_version LowCardinality(String),
    experiment_id Nullable(LowCardinality(String)),
    experiment_variant Nullable(LowCardinality(String)),
    properties String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, event_name, device_type, user_id, event_time);

CREATE TABLE IF NOT EXISTS synthetic_saas.users
(
    user_id UUID, registration_at DateTime64(3, 'UTC'), country LowCardinality(String),
    region LowCardinality(String), device_type LowCardinality(String), os LowCardinality(String),
    acquisition_channel LowCardinality(String), campaign_id String, referral_source Nullable(String),
    age_group LowCardinality(String), language LowCardinality(String), registration_date Date,
    initial_plan LowCardinality(String), first_session_id UUID
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(registration_date)
ORDER BY (registration_date, acquisition_channel, user_id);

CREATE TABLE IF NOT EXISTS synthetic_saas.payments
(
    payment_id UUID, user_id UUID, subscription_id UUID, payment_at DateTime64(3, 'UTC'),
    amount Decimal(18, 2), amount_local Decimal(18,2), amount_usd Decimal(18,2),
    currency LowCardinality(String), fx_rate_to_usd Float64, payment_method LowCardinality(String),
    status LowCardinality(String), failure_reason Nullable(LowCardinality(String)),
    refund_amount Decimal(18,2), refund_amount_local Decimal(18,2), refund_amount_usd Decimal(18,2),
    refund_at Nullable(DateTime64(3, 'UTC'))
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(payment_at)
ORDER BY (toDate(payment_at), status, user_id, payment_at);

CREATE TABLE IF NOT EXISTS synthetic_saas.sessions
(
    session_id UUID, user_id UUID, session_started_at DateTime64(3, 'UTC'),
    session_ended_at DateTime64(3, 'UTC'), device_type LowCardinality(String),
    os LowCardinality(String), app_version LowCardinality(String), country LowCardinality(String),
    traffic_source LowCardinality(String)
)
ENGINE = MergeTree PARTITION BY toYYYYMM(session_started_at)
ORDER BY (toDate(session_started_at), user_id, session_started_at);

CREATE TABLE IF NOT EXISTS synthetic_saas.subscriptions
(
    subscription_id UUID, user_id UUID, plan LowCardinality(String), started_at DateTime64(3, 'UTC'),
    ended_at Nullable(DateTime64(3, 'UTC')), monthly_price Decimal(18,2), currency LowCardinality(String),
    monthly_price_local Decimal(18,2), monthly_price_usd Decimal(18,2), billing_period LowCardinality(String),
    status LowCardinality(String), cancel_reason Nullable(LowCardinality(String)), auto_renew Bool,
    acquisition_channel_at_start LowCardinality(String)
)
ENGINE = MergeTree PARTITION BY toYYYYMM(started_at)
ORDER BY (toDate(started_at), plan, user_id, started_at);

CREATE TABLE IF NOT EXISTS synthetic_saas.marketing_spend
(
    date Date, channel LowCardinality(String), campaign_id String, country LowCardinality(String),
    currency LowCardinality(String), impressions UInt64, clicks UInt64, spend Decimal(18,2),
    spend_local Decimal(18,2), fx_rate_to_usd Float64, spend_usd Decimal(18,2), attributed_signups UInt64
)
ENGINE = MergeTree PARTITION BY toYYYYMM(date)
ORDER BY (date, channel, country, campaign_id);

CREATE TABLE IF NOT EXISTS synthetic_saas.fx_rates
(
    date Date, currency LowCardinality(String), rate_to_usd Float64,
    source LowCardinality(String), simulated Bool
)
ENGINE = MergeTree PARTITION BY toYYYYMM(date)
ORDER BY (date, currency);

CREATE TABLE IF NOT EXISTS synthetic_saas.experiments
(
    experiment_id String, experiment_name String, started_at DateTime64(3,'UTC'),
    ended_at DateTime64(3,'UTC'), primary_metric LowCardinality(String), status LowCardinality(String)
)
ENGINE = MergeTree ORDER BY experiment_id;

CREATE TABLE IF NOT EXISTS synthetic_saas.experiment_assignments
(
    experiment_id String, user_id UUID, variant LowCardinality(String), assigned_at DateTime64(3,'UTC')
)
ENGINE = MergeTree PARTITION BY toYYYYMM(assigned_at)
ORDER BY (experiment_id, variant, user_id);

CREATE TABLE IF NOT EXISTS synthetic_saas.feature_catalog
(
    feature_name String, category LowCardinality(String), available_on_plan LowCardinality(String), release_date DateTime64(3,'UTC')
)
ENGINE = MergeTree ORDER BY feature_name;

CREATE TABLE IF NOT EXISTS synthetic_saas.app_releases
(
    app_version String, platform LowCardinality(String), released_at DateTime64(3,'UTC'), description String
)
ENGINE = MergeTree ORDER BY (platform, released_at, app_version);

CREATE TABLE IF NOT EXISTS synthetic_saas.generator_config
(
    config_id String, gross_margin Float64, seed UInt64, period_start DateTime64(3,'UTC'),
    period_end DateTime64(3,'UTC'), currency_policy LowCardinality(String), model_config_hash String
)
ENGINE = TinyLog;

CREATE TABLE IF NOT EXISTS synthetic_saas.business_timeline
(
    story_month UInt8, effective_at DateTime64(3,'UTC'), story_event LowCardinality(String),
    description String, simulated Bool
)
ENGINE = MergeTree ORDER BY (effective_at, story_month);

CREATE TABLE IF NOT EXISTS synthetic_saas.pipeline_runs
(
    run_id UUID, logical_date Date, started_at DateTime64(3,'UTC'), completed_at DateTime64(3,'UTC'),
    source_watermark DateTime64(3,'UTC'), expected_event_rows UInt64, actual_event_rows UInt64,
    completeness_ratio Float64, duration_minutes UInt32, freshness_minutes UInt32, delay_minutes UInt32,
    available_by_sla Bool, partition_present Bool, status LowCardinality(String), simulated Bool
)
ENGINE = MergeTree PARTITION BY toYYYYMM(logical_date)
ORDER BY logical_date;

-- Example load:
-- INSERT INTO synthetic_saas.events SELECT * FROM file('/path/to/data/clean/events/*.parquet', Parquet);
-- Repeat for every clean entity; sql/load_clickhouse.sql contains the complete template.
