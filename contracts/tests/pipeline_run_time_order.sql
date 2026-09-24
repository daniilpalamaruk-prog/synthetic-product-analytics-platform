select * from {{ source('synthetic_saas', 'pipeline_runs') }}
where completed_at < started_at or source_watermark > completed_at
