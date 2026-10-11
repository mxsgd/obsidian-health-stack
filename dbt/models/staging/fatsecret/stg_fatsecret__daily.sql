select
    date,
    try_cast(calories as double) as kcal,
    try_cast(protein as double) as protein_g,
    try_cast(carbohydrate as double) as carbs_g,
    try_cast(fat as double) as fat_g
from {{ source('fatsecret', 'daily') }}
