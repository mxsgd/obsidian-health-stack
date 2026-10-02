"""Parser checks. Run: uv run python -m extract.test_obsidian"""
from extract.obsidian import FIELD, frontmatter, parse_sets

assert parse_sets("60x8, 62.5 x 6, 10") == [(60.0, 8, "60x8"), (62.5, 6, "62.5 x 6"), (None, 10, "10")]
assert parse_sets("80kg x 5") == [(80.0, 5, "80kg x 5")]
assert parse_sets("3x8@60") == [(None, None, "3x8@60")], "unknown format must surface, not guess"
assert parse_sets(" , ") == []

note = "---\nsession: push\nmood: 3\n---\n- Bench press:: 60x8, 60x8\n* Pull-ups:: 10\nnot a field: x\n"
assert frontmatter(note) == {"session": "push", "mood": 3}
assert frontmatter("no frontmatter") == {}
assert FIELD.findall(note) == [("Bench press", "60x8, 60x8"), ("Pull-ups", "10")]
print("extract checks pass")
