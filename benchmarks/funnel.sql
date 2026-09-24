SELECT event_date, device_type, app_version,
       uniqExactIf(user_id, event_name='signup') signups,
       uniqExactIf(user_id, event_name='checkout_started') checkouts,
       uniqExactIf(user_id, event_name='payment_success') payers
FROM synthetic_saas.events
WHERE event_date BETWEEN {start:Date} AND {end:Date}
GROUP BY event_date, device_type, app_version ORDER BY event_date;

