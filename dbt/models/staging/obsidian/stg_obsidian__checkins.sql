select
    date,
    try_cast(energy as double) as energy,
    try_cast(mood as double) as mood,
    try_cast(gut as double) as gut,
    try_cast(sleep_h as double) as sleep_h_manual,  -- legacy; replaced by watch data
    file
from {{ source('obsidian', 'checkins') }}
