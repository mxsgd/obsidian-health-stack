select
    date,
    lower(trim(workout)) as workout,
    workout_number,
    duration_min,  -- null = line could not be parsed, see workout_text
    distance_km,
    kcal,
    raw as workout_text,
    file
from {{ source('obsidian', 'workouts') }}
