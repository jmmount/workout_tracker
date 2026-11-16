# workout_tracker
tracks workouts

A guided workout app that walks a session one step at a time — the way
Muse coached Strength B on Nov 15, 2026: one card per exercise, buttons
for sets/reps/weight, a "Show me" form image, and a Next button that
moves on. Completed lift sets are collected during the session and submitted
to the Health Log spreadsheet (the "Workouts" tab) in one go at the end.

Workouts: Strength A and Strength B from Jason's weekly plan, each with
jump-rope warm-up, the mobility sequence, and a balance step (balance
practice is in every workout, per Jason's Nov 15 request). Warm-up,
mobility and balance steps are guided but only lift sets are logged.

## Run

    python3 backend/server.py

Then open http://localhost:8767 — the frontend is prebuilt in
frontend/dist, so no Node is needed to run it. The server prints its
link and the launch command on startup.

## Develop

    cd frontend && npm install && npm run dev   # Vite dev server, /api proxied to 8767
    npm run build                               # refresh frontend/dist

Backend: Python stdlib only, port 8767 (WORKOUT_GUIDE_PORT or --port).
Data: backend/workouts.py. Sets and reps are editable on every card and
you can navigate back to previous exercises; entries are kept in the app
until the final submit.

## Connect the spreadsheet (one-time, on your machine)

The app writes to the Health Log from the machine it runs on, through a
small Apps Script web app attached to the spreadsheet itself — the same
pattern as the Investment Tracker. No Google credentials live in the app;
the script executes as you, and its URL is the only secret.

1. Open the Health Log spreadsheet -> Extensions -> Apps Script.
2. Paste in apps-script/HealthLog.gs (replacing any stub code), save.
3. Deploy -> New deployment -> Web app: execute as Me, access
   "Anyone with the link". Copy the web app URL.
4. In backend/, copy .env.example to .env and set
   SHEETS_ENDPOINT=<the web app URL>. Restart the server.

Code changes to HealthLog.gs later need Deploy -> Manage deployments ->
New version, same as the Investment Tracker script.
