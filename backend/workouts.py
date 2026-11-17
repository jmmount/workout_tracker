"""Workout definitions for the guided workout app.

Strength A, Strength B and Mobility A from Jason's weekly plan.
These definitions seed the SQLite store (backend/workouts.db, via
workout_store.py); the app serves workouts from the database.
Default weights and
rep schemes reflect his Week 1 actuals (Nov 2026). Mobility and warm-up
steps are guided but not logged; lift sets are logged to the Health Log.
Balance practice is in every workout (Jason's request, Nov 15 2026).
"""

MOBILITY = [
    {"name": "Cat-camel", "target": "8 slow reps", "kind": "mobility",
     "cue": "Hands and knees. Round your back up, then let it sag gently. Move only as far as feels good.",
     "image": "https://hitmymacros.com/wp-content/uploads/2021/11/Cat_Camel-back-1024x678.jpg"},
    {"name": "Bird-dog", "target": "6 per side", "kind": "mobility",
     "cue": "Opposite arm and leg reach out, hips level, pause, return. Slow beats long.",
     "image": "https://www.chicagoathleticclubs.com/hs-fs/hubfs/Bird%20Dog.png?width=1536&height=1024&name=Bird%20Dog.png"},
    {"name": "Dead bug", "target": "8 reps", "kind": "mobility",
     "cue": "Low back pressed into the floor the whole time. Opposite arm and leg lower slowly.",
     "image": "https://traineatrepeat.com/exercise-images/dead-bug.webp"},
    {"name": "Standing hamstring stretch", "target": "30 s per side", "kind": "mobility",
     "cue": "Heel on a low step, toes up, hinge from the hips with a flat back until you feel the pull.",
     "image": "https://traineatrepeat.com/exercise-images/standing-hamstring-stretch.webp"},
    {"name": "Half-kneeling hip-flexor stretch", "target": "30 s per side", "kind": "mobility",
     "cue": "Half-kneeling, tuck the pelvis slightly, shift forward until the front of the hip opens up.",
     "image": "https://media.flexor.app/media/exercises/images/kneeling-psoas.webp"},
    {"name": "Figure-4 stretch", "target": "30 s per side", "kind": "mobility",
     "cue": "On your back, ankle over opposite knee, draw the leg in until the hip and glute let go.",
     "image": "https://westretch.ca/images/blog/Supine-Figure-Four-Stretch.webp"},
    {"name": "Child's pose", "target": "60 s", "kind": "mobility",
     "cue": "Sit back toward your heels, arms long, breathe into your back.",
     "image": "https://cdn.prod.website-files.com/670a59845f0989763e175227/670a59845f0989763e1761aa_All-about-Childs-Pose-p-1080.jpg"},
]

WARMUP = {"name": "Jump rope", "target": "5 minutes", "kind": "warmup",
          "cue": "Easy rhythm, land soft. This is a warm-up, not a workout.",
          "image": "https://fitnessvolt.com/wp-content/uploads/2020/11/jump-rope.jpg.webp"}

BALANCE = {"name": "Single-leg balance stand", "target": "2 x 30 s per side", "kind": "balance",
           "sets": 2, "reps": 30, "per_side": True, "metric": "time",
           "cue": "Stand on one leg, eyes on one spot, support within reach. Wobbling is the practice working.",
           "image": "https://www.nuffieldhealth.com/local/f2/ef/43ebcdbd4ca4bfbd97211c55fd2f/single-leg-deadlift.jpg"}

_MOB = {m["name"]: m for m in MOBILITY}


def _mob(name, sets, reps, metric, per_side=False):
    """A mobility step with set rows, so a standalone mobility session
    can be checked off and logged like any other workout."""
    base = _MOB[name]
    step = {"name": name, "kind": "mobility", "cue": base["cue"],
            "image": base["image"], "sets": sets, "reps": reps,
            "metric": metric}
    if per_side:
        step["per_side"] = True
    return step


MOBILITY_A_STEPS = [
    _mob("Cat-camel", 2, 8, "bodyweight"),
    _mob("Bird-dog", 2, 6, "bodyweight", per_side=True),
    _mob("Dead bug", 2, 8, "bodyweight", per_side=True),
    _mob("Standing hamstring stretch", 2, 30, "time", per_side=True),
    _mob("Half-kneeling hip-flexor stretch", 2, 30, "time", per_side=True),
    _mob("Figure-4 stretch", 2, 30, "time", per_side=True),
    BALANCE,
    _mob("Child's pose", 2, 60, "time"),
]

WORKOUTS = [
    {
        "id": "STR-A", "name": "Strength A", "subtitle": "Bench-led upper body",
        "steps": [WARMUP, *MOBILITY, BALANCE,
            {"name": "Bench press", "kind": "lift", "sets": 4, "reps": 6,
             "metric": "weight", "default_weight": 135,
             "cue": "Feet planted, shoulder blades pinched, bar to mid-chest, press up and slightly back.",
             "image": "https://i0.wp.com/www.muscleandfitness.com/wp-content/uploads/2017/11/barbell-bench-press-12800.jpg?w=1200&h=675&crop=1&quality=86&strip=all"},
            {"name": "Pull-ups", "kind": "lift", "sets": 4, "reps": 3,
             "metric": "bodyweight", "default_weight": None,
             "cue": "Full hang to chin over the bar. Add weight only when every set is clean.",
             "image": "https://iascfitness.org/wp-content/uploads/2023/07/concept-power-strength-healthy-lifestyle-sport-powerful-attractive-muscular-man-gym.jpg"},
            {"name": "Dumbbell row", "kind": "lift", "sets": 3, "reps": 10,
             "metric": "weight", "default_weight": 25,
             "cue": "Flat back, row to the hip, not the chest. No twisting.",
             "image": "https://www.sfd.pl/SFD/articles/content/2019/11/20/2019-11-205af7f7861d954102b98f8c7c365dbef4.jpg"},
            {"name": "Overhead press", "kind": "lift", "sets": 3, "reps": 8,
             "metric": "weight", "default_weight": 17.5,
             "cue": "Seated dumbbells. Ribs down, press straight up, don't lean back.",
             "image": "https://cdn.fitsociety.io/training/my_exercises/4ea140ad-8482-46d6-9827-c28f09702bf9_seated_dumbbell_shoulder_press-3.jpg"},
            {"name": "Dead bug", "kind": "lift", "sets": 3, "reps": 8,
             "per_side": True, "metric": "bodyweight", "default_weight": None,
             "cue": "Low back pressed into the floor the whole time — that pressure IS the ab work. Opposite arm and leg lower slowly; if your back arches, shorten the reach.",
             "image": "https://traineatrepeat.com/exercise-images/dead-bug.webp"},
            {"name": "Side plank", "kind": "lift", "sets": 2, "reps": 30,
             "per_side": True, "metric": "time", "default_weight": None,
             "cue": "Forearm down, body in one straight line, hips stacked. A plank turned sideways — bracing only, no bending or twisting.",
             "image": "https://media1.popsugar-assets.com/files/thumbor/Si7M1kTlwTOEokXzjw0WGOGvXig/fit-in/1024x1024/filters:format_auto-!!-:strip_icc-!!-/2023/01/31/730/n/1922729/tmp_mKt4pR_b820ef43be2c0d52_Side-Plank.jpg"},
            {"name": "Plank", "kind": "lift", "sets": 2, "reps": 45,
             "metric": "time", "default_weight": None,
             "cue": "One long line, ribs down, glutes on. Stop the set if your low back sags.",
             "image": "https://sp-ao.shortpixel.ai/client/to_webp,q_glossy,ret_img,w_800,h_450/https://yoga-lava.com/yogafull/wp-content/uploads/2023/08/B-53-002.jpeg"},
        ],
    },
    {
        "id": "STR-B", "name": "Strength B", "subtitle": "Deadlift-led legs and hinge",
        "steps": [WARMUP, *MOBILITY, BALANCE,
            {"name": "Trap-bar deadlift", "kind": "lift", "sets": 3, "reps": 5,
             "metric": "weight", "default_weight": 95,
             "cue": "High handles. Push the floor away, stand tall. Stop if pain radiates below the knee.",
             "image": "https://www.mensjournal.com/.image/NDI6MDAwMDAwMDAxMDIyOTkx/trap-bar-deadlift.png?profile=w828&x=50&y=50"},
            {"name": "Goblet squat", "kind": "lift", "sets": 3, "reps": 8,
             "metric": "weight", "default_weight": 35,
             "cue": "Kettlebell by the horns at your chest. Sit between your heels; depth stops before your pelvis tucks.",
             "image": "https://images.ctfassets.net/3s5io6mnxfqz/6XRq0TMYZsXUjElqZw081U/9010fe0758bc115d4476f35b0a000df8/MasterClassSEO_Goblet_Squat_HERO.jpg?w=1920"},
            {"name": "Pull-ups", "kind": "lift", "sets": 4, "reps": 3,
             "metric": "bodyweight", "default_weight": None,
             "cue": "Full hang to chin over the bar, every rep.",
             "image": "https://iascfitness.org/wp-content/uploads/2023/07/concept-power-strength-healthy-lifestyle-sport-powerful-attractive-muscular-man-gym.jpg"},
            {"name": "Incline dumbbell bench", "kind": "lift", "sets": 4, "reps": 6,
             "metric": "weight", "default_weight": 40,
             "cue": "Bench at 30-45 degrees. Dumbbells to chest level, press up and together.",
             "image": "https://www.sfd.pl/SFD/articles/main/2018/6/17/big4042ab17d30b480c849a25695d0d9870.webp"},
            {"name": "Single-leg RDL", "kind": "lift", "sets": 2, "reps": 10,
             "per_side": True, "metric": "weight", "default_weight": 15,
             "cue": "Dumbbell in the opposite hand, free hand on a rack for balance. Flat back earns the range.",
             "image": "https://www.nuffieldhealth.com/local/f2/ef/43ebcdbd4ca4bfbd97211c55fd2f/single-leg-deadlift.jpg"},
            {"name": "Pallof press", "kind": "lift", "sets": 2, "reps": 12,
             "per_side": True, "metric": "weight", "default_weight": 30,
             "cue": "Cable at chest height, side-on. Press straight out, exhale, don't let it rotate you.",
             "image": "https://www.fitnessandpower.com/wp-content/uploads/2022/06/pallof-press-768x421.jpg"},
        ],
    },
    {
        "id": "MOB-A", "name": "Mobility A",
        "subtitle": "Standalone mobility: back, hips, hamstrings",
        "steps": MOBILITY_A_STEPS,
    },
]
