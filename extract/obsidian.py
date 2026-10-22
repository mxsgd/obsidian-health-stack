"""Obsidian journal -> raw_obsidian.* tables.

Reads (all paths relative to JOURNAL_DIR):
  Days/YYYY-MM-DD.md       frontmatter energy, mood, gut (1-5), legacy sleep_h
  Workouts/YYYY-MM-DD*.md  lines like "- Bench press:: 60x8, 60x8, 62.5x6" or "- Pull-ups:: 10, 8, 7"
  Health/YYYY-MM-DD.md     written by an iOS Shortcut from Apple Health (Mi Fitness): frontmatter sleep_h,
                           resting_hr, steps; lines like "- Outdoor running:: 32 min, 5.1 km, 210 kcal"
  Plan.md                  frontmatter monday..sunday: session name, empty or "rest"
  Goals.md                 frontmatter kcal/protein targets for training and rest days

Values are loaded as text and typed in dbt staging, so a typo becomes a failing test, not a crash.
"""
import re
from pathlib import Path

import yaml

from extract.load import replace

DATED = re.compile(r"^\d{4}-\d{2}-\d{2}")
FIELD = re.compile(r"^\s*[-*]\s*([^:\n]+?)::[ \t]*(.*)$", re.M)
SET = re.compile(r"^(?:(\d+(?:\.\d+)?)\s*(?:kg)?\s*x\s*)?(\d+)$", re.I)
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
GOALS = ["kcal_training", "protein_training", "kcal_rest", "protein_rest"]
HEALTH = ["sleep_h", "resting_hr", "steps"]
# "5,1 km" too: a Polish-locale iPhone writes decimal commas, so parts are split on ", " only
WORKOUT_PART = re.compile(r"^(\d+(?:[.,]\d+)?)\s*(min|km|kcal)$", re.I)
WORKOUT_UNITS = {"min": "duration_min", "km": "distance_km", "kcal": "kcal"}


def frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    return (yaml.safe_load(text[3:end]) or {}) if end != -1 else {}


def text_or_none(v) -> str | None:
    return None if v is None or str(v).strip() == "" else str(v).strip()


def parse_sets(value: str) -> list[tuple[float | None, int | None, str]]:
    """'60x8, 62.5 x 6, 10' -> [(60.0, 8, '60x8'), (62.5, 6, '62.5 x 6'), (None, 10, '10')].
    An unparseable set keeps its raw text with reps=None so a dbt test can flag it."""
    out = []
    for raw in filter(None, (s.strip() for s in value.split(","))):
        m = SET.match(raw)
        out.append((float(m[1]) if m and m[1] else None, int(m[2]) if m else None, raw))
    return out


def parse_workout(value: str) -> dict[str, float | None]:
    """'32 min, 5,1 km, 210 kcal' -> {'duration_min': 32.0, 'distance_km': 5.1, 'kcal': 210.0}.
    One unparseable part nulls the whole line (raw text is kept) so a dbt test can flag it."""
    out = dict.fromkeys(WORKOUT_UNITS.values())
    for part in filter(None, (s.strip() for s in re.split(r",\s+", value))):
        m = WORKOUT_PART.match(part)
        if not m:
            return dict.fromkeys(WORKOUT_UNITS.values())
        out[WORKOUT_UNITS[m[2].lower()]] = float(m[1].replace(",", "."))
    return out


def dated_notes(folder: Path):
    for f in sorted(folder.glob("*.md")) if folder.exists() else []:
        if DATED.match(f.stem):
            yield f.stem[:10], f, f.read_text(encoding="utf-8")


def one_row(path: Path, keys: list[str], row_id: str) -> dict:
    fm = frontmatter(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {"id": row_id, **{k: text_or_none(fm.get(k)) for k in keys}}


def run(con, journal: Path):
    checkins = []
    for date, f, text in dated_notes(journal / "Days"):
        fm = frontmatter(text)
        checkins.append({"date": date, "file": f.name, **{k: text_or_none(fm.get(k)) for k in ("energy", "mood", "gut", "sleep_h")}})

    sets = []
    for date, f, text in dated_notes(journal / "Workouts"):
        for exercise, value in FIELD.findall(text):
            for n, (weight, reps, raw) in enumerate(parse_sets(value), 1):
                sets.append({"date": date, "file": f.name, "exercise": exercise.strip(), "set_number": n,
                             "weight_kg": weight, "reps": reps, "raw": raw})

    health, workouts = [], []
    for date, f, text in dated_notes(journal / "Health"):
        fm = frontmatter(text)
        health.append({"date": date, "file": f.name, **{k: text_or_none(fm.get(k)) for k in HEALTH}})
        for n, (workout, value) in enumerate(FIELD.findall(text), 1):
            workouts.append({"date": date, "file": f.name, "workout": workout.strip(), "workout_number": n,
                             **parse_workout(value), "raw": value.strip()})

    replace(con, "raw_obsidian", "checkins",
            {"date": "date", "file": "varchar", "energy": "varchar", "mood": "varchar", "gut": "varchar", "sleep_h": "varchar"},
            checkins)
    replace(con, "raw_obsidian", "sets",
            {"date": "date", "file": "varchar", "exercise": "varchar", "set_number": "integer",
             "weight_kg": "double", "reps": "integer", "raw": "varchar"},
            sets)
    replace(con, "raw_obsidian", "health", {"date": "date", "file": "varchar", **{k: "varchar" for k in HEALTH}}, health)
    replace(con, "raw_obsidian", "workouts",
            {"date": "date", "file": "varchar", "workout": "varchar", "workout_number": "integer",
             "duration_min": "double", "distance_km": "double", "kcal": "double", "raw": "varchar"},
            workouts)
    replace(con, "raw_obsidian", "plan", {"id": "varchar", **{d: "varchar" for d in WEEKDAYS}},
            [one_row(journal / "Plan.md", WEEKDAYS, "plan")])
    replace(con, "raw_obsidian", "goals", {"id": "varchar", **{g: "varchar" for g in GOALS}},
            [one_row(journal / "Goals.md", GOALS, "goals")])
