-- One row per (plan version, weekday). Valid on [valid_from, valid_to).
-- Empty versions (Plan.md not filled in yet) are dropped, and the first real version is
-- stretched back to cover days logged before it.
with filled as (
    select *
    from {{ ref('snap_plan') }}
    where coalesce(monday, tuesday, wednesday, thursday, friday, saturday, sunday) is not null
),

versions as (
    select
        *,
        case when dbt_valid_from = min(dbt_valid_from) over () then date '1900-01-01'
             else dbt_valid_from::date end as valid_from,
        coalesce(dbt_valid_to::date, date '9999-12-31') as valid_to
    from filled
),

unpivoted as (
    unpivot versions
    on monday, tuesday, wednesday, thursday, friday, saturday, sunday
    into name weekday value session
)

select
    valid_from,
    valid_to,
    weekday,
    lower(trim(session)) as session,
    lower(trim(session)) not in ('rest', 'off', '-') as is_training
from unpivoted
