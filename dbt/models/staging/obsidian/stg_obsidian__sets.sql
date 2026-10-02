select
    date,
    lower(trim(exercise)) as exercise,
    set_number,
    weight_kg,  -- null = bodyweight
    reps,       -- null = set text could not be parsed, see raw
    raw as set_text,
    file
from {{ source('obsidian', 'sets') }}
