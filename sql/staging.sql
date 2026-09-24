-- Staging: typed projections from contract-valid clean source tables.
CREATE VIEW IF NOT EXISTS synthetic_saas.stg_events AS SELECT * FROM synthetic_saas.events;
CREATE VIEW IF NOT EXISTS synthetic_saas.stg_users AS SELECT * FROM synthetic_saas.users;
CREATE VIEW IF NOT EXISTS synthetic_saas.stg_payments AS
SELECT *, amount_local - refund_amount_local AS net_amount_local,
          amount_usd - refund_amount_usd AS net_amount_usd
FROM synthetic_saas.payments;
CREATE VIEW IF NOT EXISTS synthetic_saas.stg_subscriptions AS
SELECT *, coalesce(ended_at, toDateTime64('2299-12-31 00:00:00', 3, 'UTC')) AS effective_ended_at
FROM synthetic_saas.subscriptions;

CREATE VIEW IF NOT EXISTS synthetic_saas.stg_marketing_spend AS
SELECT *, spend_local AS acquisition_spend_local, spend_usd AS acquisition_spend_usd
FROM synthetic_saas.marketing_spend;
