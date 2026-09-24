select * from {{ source('synthetic_saas', 'marketing_spend') }}
where spend_local < 0 or spend_usd < 0
   or abs(spend_local * fx_rate_to_usd - spend_usd) > 0.05
