-- One row per Health note. sleep_h is the sleep that ENDED that day (last night), like the manual value in Days.
-- A Polish-locale Shortcut writes "7,2" and may group thousands ("9 120"), hence the cleanup.
select
    date,
    try_cast(replace(sleep_h, ',', '.') as double) as sleep_h,
    try_cast(replace(resting_hr, ',', '.') as double) as resting_hr,
    try_cast(nullif(regexp_replace(steps, '[^0-9]', '', 'g'), '') as integer) as steps,  -- Shortcut rounds first
    file
from {{ source('obsidian', 'health') }}
