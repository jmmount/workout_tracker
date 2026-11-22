"""SQLite store for workout definitions (backend/workouts.db).

The app serves workouts from this database, not from code. The seed
definitions in workouts.py are inserted only when a workout id is not
already present — append-only, so edits made in the database (e.g. in
DBeaver) are never overwritten, and adding a workout later means adding
its definition to workouts.py and restarting: it appends itself.
"""
import sqlite3
from pathlib import Path

from workouts import WORKOUTS

DB_PATH = Path(__file__).parent / "workouts.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS workouts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    subtitle TEXT,
    sort INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS steps (
    workout_id TEXT NOT NULL REFERENCES workouts(id),
    pos INTEGER NOT NULL,
    name TEXT NOT NULL,
    kind TEXT,
    target TEXT,
    cue TEXT,
    image TEXT,
    sets INTEGER,
    reps INTEGER,
    per_side INTEGER NOT NULL DEFAULT 0,
    metric TEXT,
    default_weight REAL,
    exercise_id TEXT,
    cue_override TEXT,
    PRIMARY KEY (workout_id, pos)
);
CREATE TABLE IF NOT EXISTS exercises (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    kind TEXT,
    cue TEXT,
    image TEXT
);
"""


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _slug(name):
    out, dash = [], False
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
            dash = False
        elif not dash and out:
            out.append("-")
            dash = True
    return "".join(out).strip("-")


def _normalize_exercises(conn):
    """One exercises row per distinct step name; steps link to it.

    Canonical cue = the most common cue for the name (ties: the shorter
    one). A step whose cue differs keeps its own in cue_override, so
    per-workout cue variants survive. Idempotent; existing exercises
    rows are never overwritten.
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(steps)")}
    for col in ("exercise_id", "cue_override"):
        if col not in cols:
            conn.execute(f"ALTER TABLE steps ADD COLUMN {col} TEXT")
    names = [r[0] for r in conn.execute(
        "SELECT DISTINCT name FROM steps ORDER BY name")]
    for name in names:
        rows = conn.execute(
            "SELECT kind, cue, image FROM steps WHERE name = ?",
            (name,)).fetchall()
        cues = [r[1] for r in rows if r[1]]
        canonical = None
        if cues:
            canonical = min(set(cues),
                            key=lambda c: (-cues.count(c), len(c)))
        kind = next((r[0] for r in rows if r[0]), None)
        image = next((r[2] for r in rows if r[2]), None)
        conn.execute(
            "INSERT OR IGNORE INTO exercises (id, name, kind, cue, image)"
            " VALUES (?, ?, ?, ?, ?)",
            (_slug(name), name, kind, canonical, image))
        conn.execute(
            "UPDATE steps SET exercise_id = ? WHERE name = ?",
            (_slug(name), name))
        if canonical is not None:
            conn.execute(
                "UPDATE steps SET cue_override = cue WHERE name = ?"
                " AND cue IS NOT NULL AND cue != ?"
                " AND cue_override IS NULL", (name, canonical))


def ensure_db():
    """Create the tables if needed and append any missing seed workouts."""
    with _connect() as conn:
        conn.executescript(SCHEMA)
        have = {r["id"] for r in conn.execute("SELECT id FROM workouts")}
        for sort, w in enumerate(WORKOUTS):
            if w["id"] in have:
                continue
            conn.execute(
                "INSERT INTO workouts (id, name, subtitle, sort)"
                " VALUES (?, ?, ?, ?)",
                (w["id"], w["name"], w.get("subtitle"), sort))
            for pos, s in enumerate(w["steps"]):
                conn.execute(
                    "INSERT INTO steps (workout_id, pos, name, kind, target,"
                    " cue, image, sets, reps, per_side, metric,"
                    " default_weight)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (w["id"], pos, s["name"], s.get("kind"),
                     s.get("target"), s.get("cue"), s.get("image"),
                     s.get("sets"), s.get("reps"),
                     1 if s.get("per_side") else 0, s.get("metric"),
                     s.get("default_weight")))
        _normalize_exercises(conn)
        conn.commit()


def get_workouts():
    """All workouts with their steps, in the JSON shape the frontend uses."""
    ensure_db()
    with _connect() as conn:
        out = []
        for w in conn.execute(
                "SELECT * FROM workouts ORDER BY sort, id"):
            steps = []
            for s in conn.execute(
                    "SELECT s.*, e.name AS ex_name, e.kind AS ex_kind,"
                    " e.image AS ex_image,"
                    " COALESCE(s.cue_override, e.cue) AS ex_cue"
                    " FROM steps s"
                    " LEFT JOIN exercises e ON e.id = s.exercise_id"
                    " WHERE s.workout_id = ?"
                    " ORDER BY s.pos", (w["id"],)):
                step = {"name": s["ex_name"] or s["name"],
                        "kind": s["kind"] if s["kind"] is not None
                        else s["ex_kind"],
                        "cue": s["ex_cue"] if s["ex_cue"] is not None
                        else s["cue"],
                        "image": s["ex_image"] or s["image"]}
                for key in ("target", "sets", "reps", "metric"):
                    if s[key] is not None:
                        step[key] = s[key]
                if s["per_side"]:
                    step["per_side"] = True
                if s["default_weight"] is not None:
                    step["default_weight"] = s["default_weight"]
                steps.append(step)
            out.append({"id": w["id"], "name": w["name"],
                        "subtitle": w["subtitle"], "steps": steps})
        return out
