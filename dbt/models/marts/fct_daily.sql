-- One row per calendar day from the first logged day to today. Grows a column per source as they arrive.
with checkins as (select * from {{ ref('stg_obsidian__checkins') }}),
sets as (select * from {{ ref('stg_obsidian__sets') }}),
plan as (select * from {{ ref('stg_obsidian__plan') }}),
goals as (select * from {{ ref('stg_obsidian__goals') }}),
food as (select * from {{ ref('stg_fatsecret__daily') }}),
health as (select * from {{ ref('stg_obsidian__health') }}),
workouts as (select * from {{ ref('stg_obsidian__workouts') }}),

spine as (
    select unnest(generate_series(min(date), current_date, interval 1 day))::date as date
    from (select date from checkins union all select date from sets union all select date from food
          union all select date from health)
),

watch_workouts as (
    select
        date,
        -- strength comes from the Obsidian gym log; the watch's strength sessions would count it twice.
        -- ponytail: name match, English or Polish Apple Health names; extend if another type slips through
        sum(duration_min) filter (where not regexp_matches(workout, 'strength|siłow')) as cardio_min,
        sum(distance_km) as cardio_km,
        sum(kcal) as workout_kcal  -- all sessions: burned is burned
    from workouts
    group by date
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
        food.kcal,
        food.protein_g,
        food.carbs_g,
        food.fat_g,
        checkins.energy,
        checkins.mood,
        checkins.gut,
        coalesce(health.sleep_h, checkins.sleep_h_manual) as sleep_h,  -- watch wins, manual fills the days before it
        health.resting_hr,
        health.steps,
        watch_workouts.cardio_min,
        watch_workouts.cardio_km,
        watch_workouts.workout_kcal
    from spine
    left join checkins using (date)
    left join health using (date)
    left join watch_workouts using (date)
    left join strength using (date)
    left join food using (date)
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
    kcal,
    protein_g,
    carbs_g,
    fat_g,
    case
        when kcal is null then 'not_logged'
        when kcal_target is null then 'no_target'
        -- ponytail: under half the target is assumed to be a half-logged day, not a fast; tune if you diet hard
        when kcal < 0.5 * kcal_target then 'incomplete'
        when kcal > 1.1 * kcal_target then 'over'
        when kcal < 0.9 * kcal_target then 'under'
        else 'on_target'
    end as food_status,
    protein_g >= protein_target as hit_protein,
    exercises,
    sets,
    volume_kg,
    energy,
    mood,
    gut,
    sleep_h,
    resting_hr,
    steps,
    cardio_min,
    cardio_km,
    workout_kcal,
    -- how the NEXT morning felt: the outcome for anything eaten or done today
    lead(energy) over (order by date) as next_energy,
    lead(mood) over (order by date) as next_mood,
    lead(gut) over (order by date) as next_gut
from days
