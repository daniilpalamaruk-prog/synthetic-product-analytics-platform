CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.etl_batch_runs (
    batch_id text PRIMARY KEY,
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    rows_read bigint NOT NULL DEFAULT 0,
    rows_loaded bigint NOT NULL DEFAULT 0,
    rows_rejected bigint NOT NULL DEFAULT 0,
    watermark_from timestamptz NOT NULL,
    watermark_to timestamptz NOT NULL,
    status text NOT NULL CHECK (status IN ('running', 'success', 'failed'))
) DISTRIBUTED BY (batch_id);

CREATE TABLE IF NOT EXISTS ops.quarantine_records (
    source text NOT NULL,
    record_identifier text,
    validation_error text NOT NULL,
    rejected_at timestamptz NOT NULL,
    batch_id text NOT NULL,
    safe_payload jsonb NOT NULL
) DISTRIBUTED BY (record_identifier);

CREATE TABLE IF NOT EXISTS ops.metric_parameters (
    config_id text NOT NULL, gross_margin numeric(6,5) NOT NULL CHECK (gross_margin > 0 AND gross_margin <= 1)
) DISTRIBUTED REPLICATED;
INSERT INTO ops.metric_parameters
SELECT 'default',0.78
WHERE NOT EXISTS (SELECT 1 FROM ops.metric_parameters WHERE config_id='default');
