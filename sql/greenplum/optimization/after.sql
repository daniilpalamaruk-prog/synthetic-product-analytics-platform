-- After: direct partition-key predicate, colocated user_id join and daily preaggregation.
SELECT u.acquisition_channel, e.event_date, sum(e.active_users) AS active_users
FROM (
  SELECT event_date, user_id, 1 AS active_users
  FROM core.fct_events
  WHERE event_date >= date '2025-07-01' AND event_date < date '2025-08-01'
  GROUP BY event_date, user_id
) e
JOIN core.dim_users u ON u.user_id = e.user_id
GROUP BY u.acquisition_channel, e.event_date;
