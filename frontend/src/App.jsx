import { useEffect, useState } from 'react';

const today = () => {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};
const nowTime = () =>
  new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
// A step with set rows is a loggable step (lifts, balance, and the
// set-based mobility steps in standalone mobility workouts).
const isLiftStep = (s) => s && !!s.sets;

// Build the set rows for a step at a given set count.
function buildRows(step, setCount) {
  const rows = [];
  for (let i = 1; i <= setCount; i++) {
    if (step.per_side) {
      for (const side of ['L', 'R']) {
        rows.push({ key: `${i}-${side}`, label: `Set ${i} · ${side === 'L' ? 'Left' : 'Right'}`,
                    exercise: `${step.name} (${side})`, set_number: i,
                    value: step.reps, weight: step.default_weight ?? '' });
      }
    } else {
      rows.push({ key: `${i}`, label: `Set ${i}`, exercise: step.name,
                  set_number: i, value: step.reps, weight: step.default_weight ?? '' });
    }
  }
  return rows;
}

export default function App() {
  const [workouts, setWorkouts] = useState([]);
  const [workout, setWorkout] = useState(null);
  const [stepIdx, setStepIdx] = useState(0);
  const [data, setData] = useState({}); // stepIdx -> {setCount, rows, done}
  const [showImg, setShowImg] = useState(false);
  const [location, setLocation] = useState('YMCA');
  const [startTime, setStartTime] = useState('');
  const [finished, setFinished] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(null); // {rows} on success
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    fetch('/api/workouts').then((r) => r.json()).then(setWorkouts);
  }, []);

  const step = workout?.steps[stepIdx];
  const cur = data[stepIdx];

  function ensureStep(idx, w) {
    if (data[idx]) return;
    const s = w.steps[idx];
    setData((d) => ({ ...d, [idx]: {
      setCount: s.sets || 0,
      rows: s.sets ? buildRows(s, s.sets) : [],
      done: {},
    } }));
  }

  function start(w) {
    setWorkout(w); setStepIdx(0); setData({}); setFinished(false);
    setSubmitted(null); setSubmitError(''); setStartTime(nowTime());
    const s = w.steps[0];
    setData({ 0: { setCount: s.sets || 0, rows: s.sets ? buildRows(s, s.sets) : [], done: {} } });
    setShowImg(false);
  }

  function go(idx) {
    ensureStep(idx, workout);
    setStepIdx(idx);
    setShowImg(false);
  }

  function patchCur(patch) {
    setData((d) => ({ ...d, [stepIdx]: { ...d[stepIdx], ...patch } }));
  }

  function changeSetCount(delta) {
    const n = Math.max(1, cur.setCount + delta);
    const fresh = buildRows(step, n);
    const merged = fresh.map((r) => {
      const old = cur.rows.find((x) => x.key === r.key);
      return old ? { ...r, value: old.value, weight: old.weight } : r;
    });
    patchCur({ setCount: n, rows: merged });
  }

  function setRow(key, field, value) {
    patchCur({ rows: cur.rows.map((r) => (r.key === key ? { ...r, [field]: value } : r)) });
  }

  // Completed exercises across the whole session, for the end summary/submit.
  function completedExercises() {
    if (!workout) return [];
    const out = [];
    workout.steps.forEach((s, i) => {
      if (!isLiftStep(s) || !data[i]) return;
      const doneRows = data[i].rows.filter((r) => data[i].done[r.key]);
      if (doneRows.length) out.push({ step: s, rows: doneRows });
    });
    return out;
  }

  async function submit() {
    const exercises = completedExercises().map(({ step: s, rows }) => ({
      exercise: s.name,
      sets: rows.map((r) => ({
        exercise: r.exercise, set_number: r.set_number,
        reps: s.metric === 'time' ? '' : r.value,
        time_sec: s.metric === 'time' ? r.value : '',
        weight_lb: s.metric === 'weight' ? r.weight : '',
        metric_type: s.metric === 'time' ? 'time' : 'weight',
      })),
    }));
    setSubmitting(true); setSubmitError('');
    try {
      const res = await fetch('/api/log-session', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: today(), workout_id: workout.id,
          workout_name: workout.name, location, start_time: startTime, exercises }),
      });
      const j = await res.json();
      if (!j.ok) throw new Error(j.error || 'submit failed');
      setSubmitted({ rows: j.rows });
    } catch (e) {
      setSubmitError(String(e.message || e));
    }
    setSubmitting(false);
  }

  if (!workout) {
    return (
      <div className="wrap">
        <h1>Workout Guide</h1>
        <p className="sub">Pick today's workout. One step at a time, like the gym session. Nothing is sent to the Health Log until you submit at the end.</p>
        <label className="loc">Location
          <input value={location} onChange={(e) => setLocation(e.target.value)} />
        </label>
        {workouts.map((w) => (
          <button key={w.id} className="pick" onClick={() => start(w)}>
            <span className="pick-name">{w.name}</span>
            <span className="pick-sub">{w.subtitle} · {w.steps.length} steps</span>
          </button>
        ))}
      </div>
    );
  }

  if (finished) {
    const doneList = completedExercises();
    return (
      <div className="wrap">
        <h1>{workout.name} — review & submit</h1>
        {doneList.length ? (
          <ul className="logged">
            {doneList.map(({ step: s, rows }, i) => (
              <li key={i}><strong>{s.name}</strong> — {rows.map((r) =>
                s.metric === 'time' ? `${r.value}s` : `${r.value}${s.metric === 'weight' ? ` × ${r.weight} lb` : ''}`
              ).join(', ')}</li>
            ))}
          </ul>
        ) : <p className="sub">No sets were marked done, so there's nothing to submit.</p>}

        {submitted ? (
          <p className="ok">Submitted — {submitted.rows} sets are in the Health Log.</p>
        ) : (
          <>
            {submitError && <p className="err">Submit failed: {submitError}. Your entries are still here — try again.</p>}
            {doneList.length > 0 && (
              <button className="next" disabled={submitting} onClick={submit}>
                {submitting ? 'Submitting…' : 'Submit to Health Log'}
              </button>
            )}
          </>
        )}
        <div className="navrow">
          <button className="navbtn" onClick={() => { setFinished(false); go(workout.steps.length - 1); }}>← Back to last exercise</button>
          <button className="navbtn" onClick={() => setWorkout(null)}>Workouts</button>
        </div>
      </div>
    );
  }

  const lift = isLiftStep(step);
  return (
    <div className="wrap">
      <div className="top">
        <span>{workout.name}</span>
        <span>Step {stepIdx + 1} of {workout.steps.length}</span>
      </div>
      <div className="bar"><div style={{ width: `${((stepIdx + 1) / workout.steps.length) * 100}%` }} /></div>

      <div className="card">
        <h2>{step.name}</h2>
        <p className="target">{step.target || `${cur?.setCount ?? step.sets} sets × ${step.reps}${step.metric === 'time' ? ' s' : ' reps'}${step.per_side ? ' per side' : ''}${step.default_weight ? ` · ${step.default_weight} lb` : ''}`}</p>
        <p className="cue">{step.cue}</p>

        {showImg && <img className="form" src={step.image} alt={`${step.name} form`} />}
        <button className="showme" onClick={() => setShowImg(!showImg)}>
          {showImg ? 'Hide image' : 'Show me'}
        </button>

        {lift && cur && (
          <>
            <div className="setsedit">
              <span>Sets</span>
              <span className="stepper">
                <button onClick={() => changeSetCount(-1)}>−</button>
                <span className="val">{cur.setCount}</span>
                <button onClick={() => changeSetCount(1)}>+</button>
              </span>
            </div>
            {cur.rows.map((r) => (
              <div key={r.key} className={`setrow ${cur.done[r.key] ? 'isdone' : ''}`}>
                <span className="setlabel">{r.label}</span>
                <span className="stepper">
                  <button onClick={() => setRow(r.key, 'value', Math.max(0, r.value - 1))}>−</button>
                  <span className="val">{r.value}{step.metric === 'time' ? 's' : ''}</span>
                  <button onClick={() => setRow(r.key, 'value', r.value + 1)}>+</button>
                </span>
                {step.metric === 'weight' && (
                  <span className="stepper">
                    <button onClick={() => setRow(r.key, 'weight', Math.max(0, r.weight - 5))}>−</button>
                    <span className="val">{r.weight} lb</span>
                    <button onClick={() => setRow(r.key, 'weight', r.weight + 5)}>+</button>
                  </span>
                )}
                <button className="check" onClick={() => patchCur({ done: { ...cur.done, [r.key]: !cur.done[r.key] } })}>✓</button>
              </div>
            ))}
          </>
        )}

        <div className="navrow">
          <button className="navbtn" disabled={stepIdx === 0} onClick={() => go(stepIdx - 1)}>← Previous</button>
          {stepIdx + 1 < workout.steps.length ? (
            <button className="navbtn primary" onClick={() => go(stepIdx + 1)}>Next →</button>
          ) : (
            <button className="navbtn primary" onClick={() => setFinished(true)}>Finish →</button>
          )}
        </div>
      </div>
    </div>
  );
}
