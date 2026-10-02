-- One row per calendar day from the first logged day to today. Grows a column per source as they arrive.
with checkins as (select * from {{ ref('stg_obsidian__checkins') }}),
sets as (select * from {{ ref('stg_obsidian__sets') }}),
plan as (select * from {{ ref('stg_obsidian__plan') }}),
goals as (select * from {{ ref('stg_obsidian__goals') }}),

spine as (
    select unnest(generate_series(min(date), current_date, interval 1 day))::date as date
    from (select date from checkins union all select date from sets)
),

strength as (
    select
        date,
        count(distinct exercise) as exercises,
        count(reps) as sets,  -- unparsed sets are flagged by a test, not counted
        sum(weight_kg * reps) as volume_kg
    from sets
    group by date
),

days as (
    select
        spine.date,
        lower(dayname(spine.date)) as weekday,
        plan.session as planned_session,
        coalesce(plan.is_training, false) as is_planned_training,
        strength.date is not null as did_strength,
        strength.exercises,
        strength.sets,
        strength.volume_kg,
        goals.kcal_training,
        goals.protein_training,
        goals.kcal_rest,
        goals.protein_rest,
        checkins.energy,
        checkins.mood,
        checkins.gut,
        checkins.sleep_h_manual
    from spine
    left join checkins using (date)
    left join strength using (date)
    left join plan
        on plan.weekday = lower(dayname(spine.date))
        and spine.date >= plan.valid_from and spine.date < plan.valid_to
    left join goals
        on spine.date >= goals.valid_from and spine.date < goals.valid_to
)

select
    date,
    weekday,
    planned_session,
    is_planned_training,
    case
        when is_planned_training and did_strength then 'done'
        when is_planned_training and date = current_date then 'planned'
        when is_planned_training then 'skipped'
        when did_strength then 'extra'
        else 'rest'
    end as plan_status,
    -- targets follow the PLAN, not what happened: you decide what to eat before the gym
    case when is_planned_training then kcal_training else kcal_rest end as kcal_target,
    case when is_planned_training then protein_training else protein_rest end as protein_target,
    exercises,
    sets,
    volume_kg,
    energy,
    mood,
    gut,
    sleep_h_manual,
    -- how the NEXT morning felt: the outcome for anything eaten or done today
    lead(energy) over (order by date) as next_energy,
    lead(mood) over (order by date) as next_mood,
    lead(gut) over (order by date) as next_gut
from days
