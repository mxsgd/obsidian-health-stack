-- Plan adherence per ISO week (Monday start). Today counts only once it's done.
select
    date_trunc('week', date)::date as week_start,
    count(*) filter (where is_planned_training and plan_status != 'planned') as planned_sessions,
    count(*) filter (where plan_status = 'done') as done_sessions,
    count(*) filter (where plan_status = 'skipped') as skipped_sessions,
    count(*) filter (where plan_status = 'extra') as extra_sessions,
    round(done_sessions / nullif(planned_sessions, 0), 2) as adherence,
    sum(volume_kg) as volume_kg
from {{ ref('fct_daily') }}
group by 1
