-- PII is protected by ETL before this boundary. Raw contact values are not stored.
CREATE TABLE IF NOT EXISTS raw.users (
    user_id uuid NOT NULL,
    anonymous_user_id text NOT NULL,
    email_hmac text NOT NULL,
    phone_hmac text NOT NULL,
    encrypted_pii bytea,
    registration_at timestamptz NOT NULL,
    country text NOT NULL,
    device_type text NOT NULL,
    acquisition_channel text NOT NULL,
    campaign_id text NOT NULL,
    initial_plan text NOT NULL,
    ingestion_timestamp timestamptz NOT NULL,
    batch_id text NOT NULL,
    source text NOT NULL,
    source_file text
) DISTRIBUTED BY (user_id);

CREATE TABLE IF NOT EXISTS raw.events (
    event_id uuid NOT NULL,
    user_id uuid NOT NULL,
    session_id uuid NOT NULL,
    event_time timestamptz NOT NULL,
    event_date date NOT NULL,
    event_name text NOT NULL,
    feature_name text,
    device_type text,
    os text,
    app_version text,
    experiment_id text,
    experiment_variant text,
    properties jsonb,
    ingestion_timestamp timestamptz NOT NULL,
    batch_id text NOT NULL,
    source text NOT NULL,
    source_file text
) WITH (appendoptimized=true, orientation=column, compresstype=zstd, compresslevel=3)
  DISTRIBUTED BY (user_id)
  PARTITION BY RANGE (event_date)
  (START (date '2025-01-01') INCLUSIVE END (date '2027-01-01') EXCLUSIVE EVERY (INTERVAL '1 month'));

CREATE TABLE IF NOT EXISTS raw.payments (
    payment_id uuid NOT NULL,
    user_id uuid NOT NULL,
    subscription_id uuid NOT NULL,
    payment_at timestamptz NOT NULL,
    amount_usd numeric(18,2) NOT NULL,
    refund_amount_usd numeric(18,2) NOT NULL,
    currency char(3) NOT NULL,
    status text NOT NULL,
    ingestion_timestamp timestamptz NOT NULL,
    batch_id text NOT NULL,
    source text NOT NULL,
    source_file text
) WITH (appendoptimized=true, orientation=column, compresstype=zstd, compresslevel=3)
  DISTRIBUTED BY (user_id)
  PARTITION BY RANGE (payment_at)
  (START (timestamptz '2025-01-01') INCLUSIVE END (timestamptz '2027-01-01') EXCLUSIVE EVERY (INTERVAL '1 month'));

CREATE TABLE IF NOT EXISTS raw.subscriptions (
    subscription_id uuid NOT NULL, user_id uuid NOT NULL, plan text NOT NULL,
    started_at timestamptz NOT NULL, ended_at timestamptz,
    monthly_price_usd numeric(18,2) NOT NULL, status text NOT NULL,
    ingestion_timestamp timestamptz NOT NULL, batch_id text NOT NULL,
    source text NOT NULL, source_file text
) DISTRIBUTED BY (user_id);

CREATE TABLE IF NOT EXISTS raw.marketing_spend (
    spend_date date NOT NULL, channel text NOT NULL, campaign_id text NOT NULL,
    country text NOT NULL, spend_usd numeric(18,2) NOT NULL,
    attributed_signups bigint NOT NULL, ingestion_timestamp timestamptz NOT NULL,
    batch_id text NOT NULL, source text NOT NULL, source_file text
) DISTRIBUTED BY (campaign_id);

CREATE TABLE IF NOT EXISTS raw.experiment_assignments (
    experiment_id text NOT NULL, user_id uuid NOT NULL, variant text NOT NULL,
    assigned_at timestamptz NOT NULL, ingestion_timestamp timestamptz NOT NULL,
    batch_id text NOT NULL, source text NOT NULL, source_file text
) DISTRIBUTED BY (user_id);
