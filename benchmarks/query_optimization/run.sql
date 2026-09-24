\timing on
\o benchmarks/query_optimization/explain_before.txt
EXPLAIN (ANALYZE, BUFFERS) SELECT u.acquisition_channel, e.event_time::date AS event_date,
  count(DISTINCT e.user_id) AS active_users
FROM core.fct_events e JOIN core.dim_users u USING (user_id)
WHERE e.event_time::date BETWEEN date '2025-07-01' AND date '2025-07-31'
GROUP BY u.acquisition_channel, e.event_time::date;
\o benchmarks/query_optimization/explain_after.txt
EXPLAIN (ANALYZE, BUFFERS) SELECT u.acquisition_channel, e.event_date, count(*)
FROM (SELECT event_date,user_id FROM core.fct_events
      WHERE event_date>=date '2025-07-01' AND event_date<date '2025-08-01'
      GROUP BY event_date,user_id) e
JOIN core.dim_users u USING (user_id)
GROUP BY u.acquisition_channel,e.event_date;
\o
