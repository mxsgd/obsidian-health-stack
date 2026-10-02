# obsidian-health-stack

Food, sleep, training and mood, tracked from three messy sources and modeled with **dbt + DuckDB**.
Obsidian is both an input (morning ratings, gym log, plan, goals) and the place the dashboards live.

```
Obsidian notes ───┐
FatSecret API ────┼─► extract/*.py ─► DuckDB raw_* ─► dbt staging ─► marts ─► Obsidian dashboards
Watch → Apple Health (iOS Shortcut) ┘                 snapshots    tests
```

Status: Obsidian source done · FatSecret next · sleep/cardio after · dashboard export last.

## Run

```bash
cp .env.example .env    # point JOURNAL_DIR at your journal folder
uv sync
uv run run.py           # extract everything, then dbt build (snapshots, models, tests)
uv run python -m extract.test_obsidian   # parser checks
```

## Model

| Layer | Model | Grain |
|---|---|---|
| snapshots | `snap_plan`, `snap_goals` | one row per version of the weekly split / nutrition targets |
| staging | `stg_obsidian__checkins` | day: energy, mood, gut (1–5) |
| | `stg_obsidian__sets` | strength set |
| | `stg_obsidian__plan` | plan version × weekday, valid `[from, to)` |
| | `stg_obsidian__goals` | goals version, valid `[from, to)` |
| marts | `fct_daily` | calendar day: plan status, targets, training, ratings, next-morning ratings |
| | `fct_exercise_sessions` | exercise × day: volume, top set, estimated 1RM and its change |
| | `fct_weekly_training` | ISO week: planned vs done sessions, adherence |

Design notes:

- **Plan and goals are SCD2 snapshots.** Change your split in December and October is still judged by October's plan.
  Empty versions are ignored and the first real version is stretched back over earlier days.
- **Training day = planned, not performed.** You decide what to eat before you know if you'll make the gym,
  so targets follow the plan and a missed session shows up as `skipped`, not as a missed food goal.
- **Raw values land as text** and are typed in staging, so a typo in a note becomes a failing test instead of a crash.
  Unparseable sets (`3x8@60`) are kept with `reps = null` and raise a warning.
- **Next-day outcomes** (`next_energy`, …) use `lead()` over a full date spine, so gaps in logging never pair a day with the wrong morning.

## Note formats

```markdown
Days/2026-10-02.md          ---  energy: 3, mood: 4, gut: 4  ---
Workouts/2026-10-02.md      - Bench press:: 60x8, 60x8, 62.5x6
                            - Pull-ups:: 10, 8, 7          (bodyweight: reps only)
Plan.md                     ---  monday: push, wednesday: pull, friday: legs  ---
Goals.md                    ---  kcal_training: 2800, protein_training: 160, kcal_rest: 2400, protein_rest: 140  ---
```

Personal data (`data/`) and credentials (`.env`) are gitignored and never committed.
