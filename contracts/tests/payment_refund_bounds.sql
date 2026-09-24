select * from {{ source('synthetic_saas', 'payments') }}
where amount_local < 0 or amount_usd < 0
   or refund_amount_local < 0 or refund_amount_local > amount_local
   or refund_amount_usd < 0 or refund_amount_usd > amount_usd
   or abs(amount_local * fx_rate_to_usd - amount_usd) > 0.05
