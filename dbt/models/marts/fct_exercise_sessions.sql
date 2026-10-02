-- One row per exercise per day, with progression vs the previous session of the same exercise.
with sessions as (
    select
        date,
        exercise,
        count(*) as sets,
        sum(reps) as total_reps,
        sum(weight_kg * reps) as volume_kg,
        max(weight_kg) as top_weight_kg,
        max(weight_kg * (1 + reps / 30.0)) as est_1rm_kg  -- Epley formula
    from {{ ref('stg_obsidian__sets') }}
    where reps is not null
    group by date, exercise
)

select
    *,
    est_1rm_kg - lag(est_1rm_kg) over (partition by exercise order by date) as est_1rm_change_kg,
    total_reps - lag(total_reps) over (partition by exercise order by date) as total_reps_change
from sessions
