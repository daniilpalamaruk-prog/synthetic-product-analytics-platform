-- Half-open data interval supplied by Airflow/psql. Anti-joins make reruns idempotent.
INSERT INTO core.dim_users (user_id,anonymous_user_id,registration_at,country,device_type,acquisition_channel,campaign_id)
SELECT s.user_id,s.anonymous_user_id,s.registration_at,s.country,s.device_type,s.acquisition_channel,s.campaign_id
FROM staging.users s LEFT JOIN core.dim_users d USING (user_id)
WHERE d.user_id IS NULL
  AND s.registration_at >= :'interval_start'::timestamptz
  AND s.registration_at < :'interval_end'::timestamptz;

INSERT INTO core.fct_events
SELECT r.* FROM raw.events r
LEFT JOIN core.fct_events f USING (event_id)
WHERE f.event_id IS NULL
  AND r.event_time >= :'interval_start'::timestamptz
  AND r.event_time < :'interval_end'::timestamptz;

INSERT INTO core.fct_payments
SELECT r.* FROM raw.payments r
LEFT JOIN core.fct_payments f USING (payment_id)
WHERE f.payment_id IS NULL
  AND r.payment_at >= :'interval_start'::timestamptz
  AND r.payment_at < :'interval_end'::timestamptz;

-- SCD2 is justified only for plan history. A changed plan closes the current row,
-- then opens exactly one new current version. The NOT EXISTS guard is rerun-safe.
WITH changed AS (
  SELECT s.user_id,s.plan,s.started_at
  FROM raw.subscriptions s
  JOIN core.dim_user_plan_history d ON d.user_id=s.user_id AND d.is_current
  WHERE s.started_at >= :'interval_start'::timestamptz
    AND s.started_at < :'interval_end'::timestamptz
    AND s.plan <> d.plan
)
UPDATE core.dim_user_plan_history d
SET valid_to=c.started_at,is_current=false
FROM changed c
WHERE d.user_id=c.user_id AND d.is_current;

INSERT INTO core.dim_user_plan_history (user_id,plan,valid_from,valid_to,is_current)
SELECT s.user_id,s.plan,s.started_at,NULL,true
FROM raw.subscriptions s
WHERE s.started_at >= :'interval_start'::timestamptz
  AND s.started_at < :'interval_end'::timestamptz
  AND NOT EXISTS (
    SELECT 1 FROM core.dim_user_plan_history d
    WHERE d.user_id=s.user_id AND d.valid_from=s.started_at
  );
