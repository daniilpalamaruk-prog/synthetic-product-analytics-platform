-- Segment row counts and coefficient-like max/min ratio for large facts.
SELECT gp_segment_id, count(*) AS rows_on_segment
FROM core.fct_events
GROUP BY gp_segment_id
ORDER BY gp_segment_id;

WITH counts AS (
  SELECT gp_segment_id, count(*)::numeric AS n
  FROM core.fct_events GROUP BY gp_segment_id
)
SELECT max(n) AS max_rows, min(n) AS min_rows,
       round(max(n) / nullif(avg(n), 0), 3) AS max_to_average_ratio
FROM counts;

-- Motion nodes indicate data redistribution in a distributed plan.
EXPLAIN
SELECT u.acquisition_channel, count(*)
FROM core.fct_events e JOIN core.dim_users u USING (user_id)
GROUP BY u.acquisition_channel;
