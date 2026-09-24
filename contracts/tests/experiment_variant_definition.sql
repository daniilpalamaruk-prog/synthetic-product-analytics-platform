select * from {{ source('synthetic_saas', 'experiment_assignments') }}
where not (
  (experiment_id = 'exp_onboarding_v2' and variant in ('control','treatment')) or
  (experiment_id = 'exp_pricing_v2' and variant in ('control','new_pricing')) or
  (experiment_id = 'exp_notifications' and variant in ('control','treatment'))
)

