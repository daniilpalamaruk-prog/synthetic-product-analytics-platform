SELECT feature_name, uniqExact(user_id) adopters,
       count() uses
FROM synthetic_saas.events
WHERE event_name='feature_used' AND feature_name IS NOT NULL
GROUP BY feature_name ORDER BY adopters DESC;

