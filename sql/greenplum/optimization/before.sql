-- Before: repeated raw scan, timestamp cast in the predicate and join before aggregation.
SELECT u.acquisition_channel, e.event_time::date AS event_date,
       count(DISTINCT e.user_id) AS active_users
FROM core.fct_events e
JOIN core.dim_users u ON u.user_id = e.user_id
WHERE e.event_time::date BETWEEN date '2025-07-01' AND date '2025-07-31'
GROUP BY u.acquisition_channel, e.event_time::date;
