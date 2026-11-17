# Refactor notes

## Local health.db — workout & food results mirror (Mon Nov 16, 2026)

Workout *definitions* moved to SQLite earlier today (backend/workouts.db,
via workout_store.py). This change does the same for workout *results*:

- **backend/health.db** (SQLite, created by backend/health_store.py)
  mirrors the Health Log spreadsheet exactly:
  - `workout_rows` — the 15 Workouts columns, same names and order
    (date, workout_session_id, workout_id, workout_name, scheduled_date,
    location, start_time, duration_min, exercise, set_number, reps,
    metric_type, weight_lb, time_sec, notes).
  - `food` — the 4 Food columns (date, meal, item, estimated_kcal).
  Like workouts.db, it is gitignored: the file lives on the machine, the
  code and schema live in GitHub.
- **Full history loaded** by backend/import_health_log.py, which reads
  both sheet tabs read-only and clear-and-reloads the local tables
  (idempotent — re-running never duplicates; it would wipe any
  local-only rows, which by design there are none of yet). At import
  time: 45 workout rows, 57 food rows.
- **Dual-write:** server.py's log_session() still submits every session
  to the spreadsheet first, exactly as before, then also inserts the
  same rows into health.db. If the local write fails, the sheet submit
  is unaffected — the response JSON carries a `health_db_warning`
  field instead. (Note: a `dry_run` submit still skips the sheet but
  does write locally; dry_run is a test path only, the frontend never
  sends it.)
- **Food is not dual-written** — nothing in this app writes food; food
  logging still happens straight to the sheet, and the importer is how
  food reaches health.db.

**Cutover decision for Jason:** the spreadsheet stays canonical. The
local health.db is a mirror until he approves switching — switching
would mean the app writes sessions only to health.db (and reads history
from it), with the sheet becoming an export/backup rather than the
live store. Nothing reads from health.db yet.

## Suggested defaults from last performance (added Nov 16, evening)

At Jason's request, exercise defaults are no longer static. When the
app serves a workout, `health_store.suggested_overlay()` resets each
step's default from the last completed performance in the log (the
Health Log's data: sheet imported into health.db + dual-written on
every submit — so each Submit moves the next session's defaults):

- weight: last weight + 5 lb (under 100 lb) or + 10 lb (100 lb and up)
- time: last time + 5 s
- bodyweight: last session's best-set reps (no increment)

Steps with no logged history keep their definition defaults (e.g.
single-leg RDL keeps 15 lb until a weight is actually logged for it).
Sheet exercise names are folded to app step names by stripping
trailing "(...)" variants, with a small alias map ("Pull-up" ->
"Pull-ups"). Verified live Nov 16: bench 135 -> 145, trap-bar
deadlift 95 -> 100, plank 45 s -> 50 s.
