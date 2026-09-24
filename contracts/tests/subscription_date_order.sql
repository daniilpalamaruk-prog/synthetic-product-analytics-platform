select * from {{ source('synthetic_saas', 'subscriptions') }}
where ended_at is not null and ended_at < started_at

