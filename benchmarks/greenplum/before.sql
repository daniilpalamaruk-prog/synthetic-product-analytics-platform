EXPLAIN (ANALYZE, VERBOSE)
SELECT user_id, count(*) AS event_count, sum(amount_usd) AS revenue_usd
FROM benchmark.events_unoptimized
WHERE event_time >= timestamptz '2026-07-01 00:00:00+00'
  AND event_time <  timestamptz '2026-08-01 00:00:00+00'
GROUP BY user_id
ORDER BY event_count DESC
LIMIT 100;

