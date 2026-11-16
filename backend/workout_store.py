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
    PRIMARY KEY (workout_id, pos)
);
"""


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
                    "SELECT * FROM steps WHERE workout_id = ?"
                    " ORDER BY pos", (w["id"],)):
                step = {"name": s["name"], "kind": s["kind"],
                        "cue": s["cue"], "image": s["image"]}
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
