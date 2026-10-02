-- One row per goals version. Valid on [valid_from, valid_to).
-- Empty versions are dropped and the first real one is stretched back, like the plan.
with filled as (
    select *
    from {{ ref('snap_goals') }}
    where coalesce(kcal_training, protein_training, kcal_rest, protein_rest) is not null
)

select
    case when dbt_valid_from = min(dbt_valid_from) over () then date '1900-01-01'
         else dbt_valid_from::date end as valid_from,
    coalesce(dbt_valid_to::date, date '9999-12-31') as valid_to,
    try_cast(kcal_training as integer) as kcal_training,
    try_cast(protein_training as integer) as protein_training,
    try_cast(kcal_rest as integer) as kcal_rest,
    try_cast(protein_rest as integer) as protein_rest
from filled
