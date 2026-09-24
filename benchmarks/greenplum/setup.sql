\timing on
DROP SCHEMA IF EXISTS benchmark CASCADE;
CREATE SCHEMA benchmark;

-- Baseline: row heap, random distribution, no partition pruning.
CREATE TABLE benchmark.events_unoptimized (
    event_id bigint NOT NULL,
    user_id integer NOT NULL,
    event_time timestamptz NOT NULL,
    event_name text NOT NULL,
    amount_usd numeric(12,2) NOT NULL
) DISTRIBUTED RANDOMLY;

INSERT INTO benchmark.events_unoptimized
SELECT g,
       1 + g % 1000,
       timestamptz '2025-01-01 00:00:00+00'
           + ((g / 5000) % 730) * interval '1 day'
           + (g % 86400) * interval '1 second',
       (ARRAY['login','feature_used','checkout_started','payment_success'])[1 + g % 4],
       ((g % 9900) / 100.0 + 1)::numeric(12,2)
FROM generate_series(1, 3000000) AS s(g);

-- Optimized event layer: columnar, distributed on the grouping key, monthly partitions.
CREATE TABLE benchmark.events_optimized (
    event_id bigint NOT NULL,
    user_id integer NOT NULL,
    event_time timestamptz NOT NULL,
    event_date date NOT NULL,
    event_name text NOT NULL,
    amount_usd numeric(12,2) NOT NULL
)
WITH (appendoptimized=true, orientation=column, compresstype=zstd, compresslevel=3)
DISTRIBUTED BY (user_id)
PARTITION BY RANGE (event_date)
(START (date '2025-01-01') INCLUSIVE END (date '2027-01-01') EXCLUSIVE
 EVERY (INTERVAL '1 month'));

INSERT INTO benchmark.events_optimized
SELECT event_id, user_id, event_time, event_time::date, event_name, amount_usd
FROM benchmark.events_unoptimized;

-- Serving layer: one row per user/day, retaining partition pruning and colocation.
CREATE TABLE benchmark.events_daily_preaggregated (
    event_date date NOT NULL,
    user_id integer NOT NULL,
    event_count bigint NOT NULL,
    revenue_usd numeric(18,2) NOT NULL
)
WITH (appendoptimized=true, orientation=column, compresstype=zstd, compresslevel=3)
DISTRIBUTED BY (user_id)
PARTITION BY RANGE (event_date)
(START (date '2025-01-01') INCLUSIVE END (date '2027-01-01') EXCLUSIVE
 EVERY (INTERVAL '1 month'));

INSERT INTO benchmark.events_daily_preaggregated
SELECT event_date, user_id, count(*), sum(amount_usd)
FROM benchmark.events_optimized
GROUP BY event_date, user_id;

ANALYZE benchmark.events_unoptimized;
ANALYZE ROOTPARTITION benchmark.events_optimized;
ANALYZE ROOTPARTITION benchmark.events_daily_preaggregated;
