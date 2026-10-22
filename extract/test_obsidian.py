"""Parser checks. Run: uv run python -m extract.test_obsidian"""
from extract.obsidian import FIELD, frontmatter, parse_sets, parse_workout

assert parse_sets("60x8, 62.5 x 6, 10") == [(60.0, 8, "60x8"), (62.5, 6, "62.5 x 6"), (None, 10, "10")]
assert parse_sets("80kg x 5") == [(80.0, 5, "80kg x 5")]
assert parse_sets("3x8@60") == [(None, None, "3x8@60")], "unknown format must surface, not guess"
assert parse_sets(" , ") == []

note = "---\nsession: push\nmood: 3\n---\n- Bench press:: 60x8, 60x8\n* Pull-ups:: 10\nnot a field: x\n"
assert frontmatter(note) == {"session": "push", "mood": 3}
assert frontmatter("no frontmatter") == {}
assert FIELD.findall(note) == [("Bench press", "60x8, 60x8"), ("Pull-ups", "10")]
assert parse_workout("32 min, 5.1 km, 210 kcal") == {"duration_min": 32.0, "distance_km": 5.1, "kcal": 210.0}
assert parse_workout("45,5 min, 5,1 km") == {"duration_min": 45.5, "distance_km": 5.1, "kcal": None}, "decimal comma"
assert parse_workout("40 MIN") == {"duration_min": 40.0, "distance_km": None, "kcal": None}
assert parse_workout("32 min, 5 laps") == dict.fromkeys(["duration_min", "distance_km", "kcal"]), "unknown part must surface"
print("extract checks pass")
