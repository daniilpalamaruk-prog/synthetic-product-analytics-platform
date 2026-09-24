select * from {{ source('synthetic_saas', 'users') }}
where campaign_id not like concat(acquisition_channel, '\_%') escape '\\'
