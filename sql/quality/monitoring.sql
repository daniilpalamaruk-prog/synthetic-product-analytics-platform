-- Synthetic monitoring queries. They measure generated telemetry, not a real production SLA.

-- Latest available event and table freshness.
SELECT max(event_time) AS latest_available_event,
       dateDiff('minute', max(event_time), now()) AS wall_clock_freshness_minutes
FROM synthetic_saas.events;

-- Latest business timestamp per fact table (interpret against its own delivery cadence).
SELECT 'events' AS table_name, max(event_time) AS latest_available_at FROM synthetic_saas.events
UNION ALL SELECT 'payments', max(payment_at) FROM synthetic_saas.payments
UNION ALL SELECT 'subscriptions', max(started_at) FROM synthetic_saas.subscriptions
UNION ALL SELECT 'sessions', max(session_started_at) FROM synthetic_saas.sessions
UNION ALL SELECT 'pipeline_runs', max(completed_at) FROM synthetic_saas.pipeline_runs;

-- Late-arriving records (properties is serialized JSON in the baseline DDL).
SELECT event_date, countIf(position(properties, 'late_arrival_hours') > 0) AS late_records,
       late_records / count() AS late_record_rate
FROM synthetic_saas.events GROUP BY event_date ORDER BY event_date;

-- Missing event partitions within configured generation period.
WITH bounds AS (SELECT toDate(min(period_start)) start_date, toDate(max(period_end)) end_date FROM synthetic_saas.generator_config),
expected AS (SELECT start_date + number AS event_date FROM bounds ARRAY JOIN range(dateDiff('day', start_date, end_date)) AS number),
actual AS (SELECT DISTINCT event_date FROM synthetic_saas.events)
SELECT e.event_date FROM expected e LEFT JOIN actual a USING event_date WHERE a.event_date IS NULL ORDER BY e.event_date;

-- Robust investigation input for record-volume anomalies.
SELECT event_date, count() AS event_rows,
       avg(event_rows) OVER (ORDER BY event_date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS prior_7d_avg,
       stddevPop(event_rows) OVER (ORDER BY event_date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS prior_7d_stddev
FROM synthetic_saas.events GROUP BY event_date ORDER BY event_date;

-- Completeness, availability, duration, freshness and allowed delay.
SELECT logical_date, completeness_ratio, available_by_sla, duration_minutes, freshness_minutes,
       delay_minutes, partition_present, status
FROM synthetic_saas.pipeline_runs
WHERE completeness_ratio < 0.99 OR NOT available_by_sla OR duration_minutes > 45
   OR freshness_minutes > 60 OR delay_minutes > 180 OR NOT partition_present OR status != 'success'
ORDER BY logical_date;
