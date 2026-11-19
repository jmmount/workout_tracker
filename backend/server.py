#!/usr/bin/env python3
"""Workout Guide — local backend.

Serves the guided-workout frontend on one port and logs completed lift
sets to the Health Log spreadsheet (same append path as
~/workspace/health/code/populate_workout.py).

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
    """Append every completed exercise's sets to the Health Log, once.

    Body: {date, workout_id, workout_name, location, start_time,
           exercises: [{exercise, sets: [{exercise?, set_number, reps,
           metric_type, weight_lb, time_sec}]}], dry_run?}

    Returns (sheet_result, warning). The same rows are also dual-written
    to the local health.db; a local failure never breaks the sheet
    submit — it comes back as the warning string instead.
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
    result = append_rows(rows, dry_run=bool(body.get("dry_run")))
    warning = None
    try:
        health_store.log_rows(rows)
    except Exception as e:  # local mirror must never break the sheet submit
        warning = f"health.db dual-write failed: {e}"
    return result, warning


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

    def do_POST(self):
        if self.path != "/api/log-session":
            return self._json(404, {"ok": False, "error": "unknown_path"})
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            result, warning = log_session(body)
            n = sum(len(e["sets"]) for e in body["exercises"])
            resp = {"ok": True, "rows": n, "result": result}
            if warning:
                resp["health_db_warning"] = warning
            self._json(200, resp)
        except Exception as e:  # surface the real error to the app
            self._json(500, {"ok": False, "error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("WORKOUT_GUIDE_PORT", "8767"))
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    print(f"Workout Guide: http://localhost:{port}", flush=True)
    print(f"Started with: python3 {' '.join(sys.argv)}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
