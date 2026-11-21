#!/usr/bin/env python3
"""Workout Guide — local backend.

Serves the guided-workout frontend on one port and logs completed lift
sets to the local health.db (the primary store since the Nov 21, 2026
step-2 cutover). Each submit is also exported to the Health Log
spreadsheet afterwards, best-effort — an export failure never fails
the submit.

Run:  python3 backend/server.py [--port 8767]
"""
import json
import os
import subprocess
import sys
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from workout_store import get_workouts  # noqa: E402
import health_store  # noqa: E402

DIST = Path(__file__).parent.parent / "frontend" / "dist"


def load_env():
    """Read KEY=VALUE lines from backend/.env (local config, never committed)."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
# Apps Script web app URL for the Health Log (see apps-script/HealthLog.gs).
# When set, the app writes to the spreadsheet from THIS machine over HTTPS,
# executing as the sheet's owner — no Google credentials stored in the app.
SHEETS_ENDPOINT = os.environ.get("SHEETS_ENDPOINT", "")
SPREADSHEET_ID = "1tauxBlfcQW-KCiq8o7vtZFX7wEc08x5sSMJJMELFbUQ"
RANGE = "Workouts!A:O"
CLI = "/opt/hatch/bin/hatch_gws_cli"
COLUMNS = ["date", "workout_session_id", "workout_id", "workout_name",
           "scheduled_date", "location", "start_time", "duration_min",
           "exercise", "set_number", "reps", "metric_type", "weight_lb",
           "time_sec", "notes"]


def append_rows(rows, dry_run=False):
    payload = {"values": rows}
    if dry_run:
        return payload
    if SHEETS_ENDPOINT:
        req = urllib.request.Request(
            SHEETS_ENDPOINT,
            data=json.dumps({"rows": rows}).encode(),
            headers={"Content-Type": "text/plain"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    if not os.path.exists(CLI):
        raise RuntimeError(
            "No spreadsheet connection on this machine yet: set "
            "SHEETS_ENDPOINT in backend/.env (see README) and restart.")
    result = subprocess.run(
        [CLI, "sheets", "spreadsheets", "values", "append",
         "--params", json.dumps({"spreadsheetId": SPREADSHEET_ID,
                                 "range": RANGE,
                                 "valueInputOption": "USER_ENTERED"}),
         "--json", json.dumps(payload)],
        capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def log_session(body):
    """Log every completed exercise's sets, once.

    Body: {date, workout_id, workout_name, location, start_time,
           exercises: [{exercise, sets: [{exercise?, set_number, reps,
           metric_type, weight_lb, time_sec}]}], dry_run?}

    The rows are written to the local health.db FIRST — that write is
    the committed success, and its failure raises. The same rows are
    then exported to the Health Log spreadsheet, best-effort: an
    export failure is logged to stderr and reported, never raised.
    (dry_run skips only the export; it is a test path, unused by the
    frontend.)

    Returns (export_result, exported, export_error).
    """
    date = body["date"]
    session = f"{date}-{body['workout_id']}"
    rows = []
    for ex in body["exercises"]:
        for s in ex["sets"]:
            row = {
                "date": date, "workout_session_id": session,
                "workout_id": body["workout_id"],
                "workout_name": body["workout_name"],
                "scheduled_date": date,
                "location": body.get("location", "YMCA"),
                "start_time": body.get("start_time", ""),
                "duration_min": "",
                "exercise": s.get("exercise", ex["exercise"]),
                "set_number": s["set_number"],
                "reps": s.get("reps", ""),
                "metric_type": s.get("metric_type", "weight"),
                "weight_lb": s.get("weight_lb", ""),
                "time_sec": s.get("time_sec", ""),
                "notes": s.get("notes", "Logged from Workout Guide app."),
            }
            rows.append([row[c] for c in COLUMNS])
    health_store.log_rows(rows)  # primary write; a failure here raises
    result, exported, export_error = None, False, None
    try:
        result = append_rows(rows, dry_run=bool(body.get("dry_run")))
        exported = True
    except Exception as e:  # export is best-effort; the DB row stands
        export_error = str(e)
        print(f"sheet export failed for session {session}: {e}",
              file=sys.stderr, flush=True)
    return result, exported, export_error


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DIST), **kw)

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/workouts":
            return self._json(200, health_store.suggested_overlay(get_workouts()))
        if not Path(DIST, self.path.lstrip("/")).exists() and "." not in Path(self.path).name:
            self.path = "/index.html"
        super().do_GET()

    def _log_food(self, body):
        """POST /api/log/food: {date, meal, item, kcal} -> one food row."""
        if not isinstance(body, dict):
            raise ValueError("body must be a JSON object")
        missing = [k for k in ("date", "meal", "item", "kcal")
                   if body.get(k) in (None, "")]
        if missing:
            raise ValueError(f"missing field(s): {', '.join(missing)}")
        kcal = body["kcal"]
        if isinstance(kcal, bool) or not isinstance(kcal, (int, float)):
            raise ValueError("kcal must be a number")
        return health_store.log_food_rows(
            [[body["date"], body["meal"], body["item"], kcal]])

    def _log_workout(self, body):
        """POST /api/log/workout: {rows: [{...COLUMNS fields...}]}."""
        if not isinstance(body, dict) or not isinstance(body.get("rows"), list) \
                or not body["rows"]:
            raise ValueError("body must be {rows: [row, ...]}")
        rows = []
        for i, r in enumerate(body["rows"]):
            if not isinstance(r, dict):
                raise ValueError(f"rows[{i}] must be an object")
            missing = [c for c in COLUMNS if c not in r]
            if missing:
                raise ValueError(
                    f"rows[{i}] missing field(s): {', '.join(missing)}")
            rows.append([r[c] for c in COLUMNS])
        return health_store.log_rows(rows)

    def do_POST(self):
        try:
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
        except (TypeError, ValueError):
            return self._json(400, {"ok": False, "error": "invalid JSON body"})
        try:
            if self.path == "/api/log-session":
                result, exported, export_error = log_session(body)
                n = sum(len(e["sets"]) for e in body["exercises"])
                resp = {"ok": True, "rows": n, "result": result,
                        "exported": exported}
                if export_error:
                    resp["export_error"] = export_error
                return self._json(200, resp)
            if self.path == "/api/log/food":
                return self._json(200, {"ok": True,
                                        "inserted": self._log_food(body)})
            if self.path == "/api/log/workout":
                return self._json(200, {"ok": True,
                                        "inserted": self._log_workout(body)})
            return self._json(404, {"ok": False, "error": "unknown_path"})
        except ValueError as e:
            self._json(400, {"ok": False, "error": str(e)})
        except Exception as e:  # surface the real error to the app
            self._json(500, {"ok": False, "error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("WORKOUT_GUIDE_PORT", "8767"))
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    print(f"Workout Guide: http://localhost:{port}", flush=True)
    print(f"Started with: python3 {' '.join(sys.argv)}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
