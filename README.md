# obsidian-health-stack

Food, sleep, training and mood, tracked from three messy sources and modeled with **dbt + DuckDB**.
Obsidian is both an input (morning ratings, gym log, plan, goals) and the place the dashboards live.

```
Redmi Watch 3 → Mi Fitness → Apple Health → iOS Shortcut ─► Health/*.md ─┐
Obsidian notes ──────────────────────────────────────────────────────────┤
FatSecret API ───────────────────────────────────────────────────────────┴─► extract/*.py ─► DuckDB raw_*
    ─► dbt staging ─► marts ─► Obsidian dashboards
       snapshots      tests
```

Status: Obsidian, FatSecret and watch (via the Shortcut below) done · dashboard export last.

## Run

```bash
cp .env.example .env    # point JOURNAL_DIR at your journal folder
uv sync
uv run run.py           # extract everything, then dbt build (snapshots, models, tests)
uv run python -m extract.test_obsidian   # parser checks
```

### Scheduled, with Airflow

```bash
docker compose up --build                                    # http://localhost:8080, DAG `health`
docker compose exec airflow airflow dags list-import-errors  # DAG parses?
docker compose exec airflow airflow dags test health         # one run, now
```

`dags/health.py` runs daily at 06:00: `extract_obsidian → extract_fatsecret → dbt_build`, the same functions as `run.py`.
FatSecret retries 3× (network); without a token it's skipped and dbt still builds. Extracts are sequential because DuckDB allows one writer.

## Model

| Layer | Model | Grain |
|---|---|---|
| snapshots | `snap_plan`, `snap_goals` | one row per version of the weekly split / nutrition targets |
| staging | `stg_obsidian__checkins` | day: energy, mood, gut (1–5) |
| | `stg_obsidian__sets` | strength set |
| | `stg_obsidian__plan` | plan version × weekday, valid `[from, to)` |
| | `stg_obsidian__goals` | goals version, valid `[from, to)` |
| | `stg_obsidian__health` | day: sleep, resting HR, steps (watch) |
| | `stg_obsidian__workouts` | watch workout: minutes, km, kcal |
| marts | `fct_daily` | calendar day: plan status, targets, training, cardio, sleep, ratings, next-morning ratings |
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
- **Strength comes from the gym log, cardio from the watch.** Watch strength sessions are left out of `cardio_min`
  so a gym day isn't counted twice; they still count toward `workout_kcal`.
- **Watch sleep wins over typed sleep**, and the typed `sleep_h` fills the days before the watch.

## Note formats

```markdown
Days/2026-10-02.md          ---  energy: 3, mood: 4, gut: 4  ---
Workouts/2026-10-02.md      - Bench press:: 60x8, 60x8, 62.5x6
                            - Pull-ups:: 10, 8, 7          (bodyweight: reps only)
Plan.md                     ---  monday: push, wednesday: pull, friday: legs  ---
Goals.md                    ---  kcal_training: 2800, protein_training: 160, kcal_rest: 2400, protein_rest: 140  ---
Health/2026-10-02.md        ---  sleep_h: 7.2, resting_hr: 54, steps: 9120  ---       (written by the Shortcut)
                            - Outdoor running:: 32 min, 5.1 km, 210 kcal   (min required; km, kcal optional)
```

## Watch data: the iOS Shortcut

Mi Fitness has no API, so the watch reaches the pipeline through Apple Health. A Shortcut on the iPhone writes
yesterday's data as a note into the vault, and from there it's just another Obsidian note.

1. **Mi Fitness:** Profile → third-party data sharing → Apple Health, allow sleep, heart rate, steps and workouts.
2. **Shortcuts → Automation → Time of Day**, daily at 05:30, *Run Immediately*. Actions:
   - `Yesterday` = *Adjust Date* (Current Date − 1 day); `Day` = *Format Date* `Yesterday` as `yyyy-MM-dd`.
     `From` = *Get Dates from* `Day` (yesterday 00:00); `To` = `From` + 1 day.
   - Every *Find Health Samples* below filters **Source is Mi Fitness** (the iPhone logs steps and sleep too,
     and raw samples are not de-duplicated like the Health app does) and **End Date is between `From` and `To`**.
   - **sleep_h:** Type *Sleep Analysis*, Value is not *In Bed* and not *Awake* → *Repeat with Each*:
     *Get Time Between Dates* (Start Date, End Date, minutes) → *Calculate Statistics* Sum → ÷ 60 → round to 1 decimal.
   - **resting_hr:** Type *Resting Heart Rate*, Limit 1 → value, rounded.
   - **steps:** Type *Steps* → *Calculate Statistics* Sum → round to ones.
   - **workouts:** Type *Workouts* → *Repeat with Each*: a line `- {type}:: {minutes} min, {distance} km, {energy} kcal`.
     Leave out distance or energy if your iOS doesn't offer them; only minutes is required.
   - *Text* with the note (frontmatter + workout lines) → *Save File* to
     `iCloud Drive/Obsidian/<vault>/Food Journal/Health/{Day}.md`, *Ask Where to Save* off, *Overwrite* on.
3. Check the first note by hand. Decimal commas (`7,2`) and grouped steps (`9 120`) are handled; anything else that
   doesn't parse becomes `null`, and a bad workout line raises a dbt warning.

A note covers everything that *ended* on that day, so `sleep_h` is the night before, same as the morning check-in.
If the watch hadn't synced by 05:30, run the Shortcut again by hand that day (it overwrites); the next pipeline run picks it up.

Personal data (`data/`) and credentials (`.env`) are gitignored and never committed.
