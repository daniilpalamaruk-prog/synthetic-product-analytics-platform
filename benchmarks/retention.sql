WITH cohorts AS (
  SELECT user_id, registration_date FROM synthetic_saas.users
)
SELECT c.registration_date, dateDiff('day', c.registration_date, e.event_date) age_day,
       uniqExact(e.user_id) retained_users
FROM synthetic_saas.events e INNER JOIN cohorts c USING user_id
WHERE e.event_name IN ('login','feature_used') AND age_day IN (1,7,30,90)
GROUP BY c.registration_date, age_day ORDER BY c.registration_date, age_day;

