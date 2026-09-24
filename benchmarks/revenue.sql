SELECT toStartOfMonth(payment_at) month, currency,
       sumIf(amount, status IN ('success','refunded')) - sum(refund_amount) net_revenue,
       uniqExactIf(user_id, status IN ('success','refunded')) payers
FROM synthetic_saas.payments GROUP BY month, currency ORDER BY month;

