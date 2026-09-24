-- Each query must return zero before marts are published.
SELECT count(*)-count(DISTINCT event_id) AS duplicate_event_ids FROM core.fct_events;
SELECT count(*)-count(DISTINCT payment_id) AS duplicate_payment_ids FROM core.fct_payments;
SELECT count(*) AS orphan_events
FROM core.fct_events e LEFT JOIN core.dim_users u USING(user_id) WHERE u.user_id IS NULL;
SELECT count(*) AS orphan_payments
FROM core.fct_payments p LEFT JOIN core.dim_users u USING(user_id) WHERE u.user_id IS NULL;
SELECT count(*) AS invalid_amounts
FROM core.fct_payments WHERE amount_usd < 0 OR refund_amount_usd < 0;
SELECT count(*) AS invalid_scd2_current_rows
FROM (SELECT user_id FROM core.dim_user_plan_history WHERE is_current GROUP BY user_id HAVING count(*)<>1) q;
