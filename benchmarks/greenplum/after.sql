EXPLAIN (ANALYZE, VERBOSE)
SELECT user_id, sum(event_count) AS event_count, sum(revenue_usd) AS revenue_usd
FROM benchmark.events_daily_preaggregated
WHERE event_date >= date '2026-07-01'
  AND event_date <  date '2026-08-01'
GROUP BY user_id
ORDER BY event_count DESC
LIMIT 100;

