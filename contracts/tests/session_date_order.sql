select * from {{ source('synthetic_saas', 'sessions') }}
where session_ended_at < session_started_at

