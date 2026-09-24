select e.*
from {{ source('synthetic_saas', 'events') }} e
join {{ source('synthetic_saas', 'users') }} u using (user_id)
where e.event_name not in ('ad_impression', 'ad_click')
  and e.event_time < u.registration_at

