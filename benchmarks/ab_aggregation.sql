SELECT experiment_id, experiment_variant,
       uniqExact(user_id) assigned_observed,
       uniqExactIf(user_id, event_name='onboarding_completed') conversions,
       conversions / assigned_observed conversion_rate
FROM synthetic_saas.events WHERE experiment_id IS NOT NULL
GROUP BY experiment_id, experiment_variant;

