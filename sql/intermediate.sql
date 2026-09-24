CREATE VIEW IF NOT EXISTS synthetic_saas.int_user_activation AS
SELECT u.user_id, u.registration_date, u.acquisition_channel, u.country, u.device_type,
       countIf(e.event_name = 'onboarding_completed') > 0 AS onboarding_completed,
       uniqExactIf(e.feature_name, e.event_name = 'feature_used'
          AND e.feature_name IN ('dashboard','task_manager','calendar')
          AND e.event_time < u.registration_at + INTERVAL 3 DAY) AS core_features_first_3d,
       onboarding_completed AND core_features_first_3d >= 2 AS activated
FROM synthetic_saas.users u LEFT JOIN synthetic_saas.events e ON e.user_id = u.user_id
GROUP BY u.user_id, u.registration_date, u.acquisition_channel, u.country, u.device_type;

CREATE VIEW IF NOT EXISTS synthetic_saas.int_user_revenue AS
SELECT u.user_id, u.registration_date, u.acquisition_channel, u.country,
       sumIf(p.amount_usd - p.refund_amount_usd, p.status IN ('success','refunded')) AS net_revenue_usd,
       countIf(p.status IN ('success','refunded')) AS successful_payments
FROM synthetic_saas.users u LEFT JOIN synthetic_saas.payments p ON p.user_id = u.user_id
GROUP BY u.user_id, u.registration_date, u.acquisition_channel, u.country;

CREATE VIEW IF NOT EXISTS synthetic_saas.int_subscription_transitions AS
SELECT old.user_id,
       old.subscription_id AS old_subscription_id,
       new.subscription_id AS new_subscription_id,
       old.plan AS old_plan, new.plan AS new_plan,
       old.ended_at AS changed_at,
       old.monthly_price_usd AS old_mrr_usd,
       new.monthly_price_usd AS new_mrr_usd,
       new.monthly_price_usd - old.monthly_price_usd AS mrr_delta_usd
FROM synthetic_saas.subscriptions old
INNER JOIN synthetic_saas.subscriptions new
  ON new.user_id = old.user_id AND old.ended_at = new.started_at
WHERE old.ended_at IS NOT NULL AND old.subscription_id != new.subscription_id;
