"""Local SQLite store for workout RESULTS (backend/health.db).

Mirrors the Health Log spreadsheet's two tabs:
- workout_rows: the 15 Workouts columns, same names and order.
- food:         the 4 Food columns (date, meal, item, estimated_kcal).

The spreadsheet stays canonical for now (Nov 16, 2026): server.py still
submits every session to the sheet first and dual-writes the same rows
here second. See REFACTOR_NOTES.md for the cutover decision.
"""
import math
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "health.db"

WORKOUT_COLUMNS = ["date", "workout_session_id", "workout_id", "workout_name",
                   "scheduled_date", "location", "start_time", "duration_min",
                   "exercise", "set_number", "reps", "metric_type",
                   "weight_lb", "time_sec", "notes"]
FOOD_COLUMNS = ["date", "meal", "item", "estimated_kcal"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS workout_rows (
    date TEXT, workout_session_id TEXT, workout_id TEXT, workout_name TEXT,
    scheduled_date TEXT, location TEXT, start_time TEXT, duration_min REAL,
    exercise TEXT, set_number INTEGER, reps INTEGER, metric_type TEXT,
    weight_lb REAL, time_sec REAL, notes TEXT);
CREATE TABLE IF NOT EXISTS food (
    date TEXT, meal TEXT, item TEXT, estimated_kcal INTEGER);
"""


def _num(v, cast=float):
    try:
        return cast(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _workout_tuple(row):
    r = (list(row) + [""] * 15)[:15]
    return (r[0], r[1], r[2], r[3], r[4], r[5], r[6], _num(r[7]),
            r[8], _num(r[9], int), _num(r[10], int), r[11],
            _num(r[12]), _num(r[13]), r[14])


def _food_tuple(row):
    r = (list(row) + [""] * 4)[:4]
    return (r[0], r[1], r[2], _num(r[3], int))


def _connect():
    return sqlite3.connect(DB_PATH)


def ensure_db():
    with _connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def log_rows(rows):
    """Insert session rows (lists in WORKOUT_COLUMNS order). Returns count."""
    ensure_db()
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO workout_rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [_workout_tuple(r) for r in rows])
        conn.commit()
    return len(rows)


def log_food_rows(rows):
    """Insert food rows (lists in FOOD_COLUMNS order). Returns count."""
    ensure_db()
    with _connect() as conn:
        conn.executemany("INSERT INTO food VALUES (?,?,?,?)",
                         [_food_tuple(r) for r in rows])
        conn.commit()
    return len(rows)


def clear_tables():
    """Empty both tables (the importer clear-and-reloads from the sheet)."""
    ensure_db()
    with _connect() as conn:
        conn.execute("DELETE FROM workout_rows")
        conn.execute("DELETE FROM food")
        conn.commit()


def counts():
    ensure_db()
    with _connect() as conn:
        w = conn.execute("SELECT COUNT(*) FROM workout_rows").fetchone()[0]
        f = conn.execute("SELECT COUNT(*) FROM food").fetchone()[0]
    return w, f


import re

_ALIASES = {"Pull-up": "Pull-ups"}


def _base_name(exercise):
    """'Pallof press (L)' -> 'Pallof press'; grip/variant names fold to
    the app's step names via _ALIASES."""
    base = re.sub(r"\s*\([^)]*\)\s*$", "", exercise or "").strip()
    return _ALIASES.get(base, base)


def last_performance():
    """Most recent logged performance per exercise (base name), from
    the latest session that logged it: {"date", "weight", "time",
    "reps"} with max values across that session's sets."""
    ensure_db()
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT date, workout_session_id, exercise, reps, weight_lb,"
            " time_sec FROM workout_rows ORDER BY date DESC, rowid DESC"
        ).fetchall()
    latest = {}
    for r in rows:
        base = _base_name(r["exercise"])
        if base not in latest:
            latest[base] = {"session": r["workout_session_id"],
                            "date": r["date"], "weight": None,
                            "time": None, "reps": None}
        entry = latest[base]
        if r["workout_session_id"] != entry["session"]:
            continue
        for key, col in (("weight", "weight_lb"), ("time", "time_sec"),
                         ("reps", "reps")):
            v = r[col]
            if v is not None and (entry[key] is None or v > entry[key]):
                entry[key] = v
    return latest


def suggested_overlay(workouts):
    """Reset each step's defaults from the last completed performance
    (Jason's rule, Nov 16 2026): weight +5 lb under 100 lb, +10 lb at
    100 lb and up; time +5 s; bodyweight reps = last time's best set.
    Suggested weights always round UP to the next multiple of 5 lb
    (Jason's rule, Nov 17 2026: 17.5 -> 20, so 22.5 -> 25).
    Steps with no logged history keep their definition defaults. The
    log is the Health Log's data (sheet imported + dual-written), so
    every Submit moves the next session's defaults."""
    try:
        last = last_performance()
    except Exception:
        return workouts
    for w in workouts:
        for s in w["steps"]:
            if not s.get("sets"):
                continue
            perf = last.get(s["name"])
            if not perf:
                continue
            if s.get("metric") == "weight" and perf["weight"]:
                raw = perf["weight"] + (
                    10 if perf["weight"] >= 100 else 5)
                s["default_weight"] = math.ceil(raw / 5) * 5
            elif s.get("metric") == "time" and perf["time"]:
                s["reps"] = int(perf["time"]) + 5
            elif s.get("metric") == "bodyweight" and perf["reps"]:
                s["reps"] = int(perf["reps"])
    return workouts
