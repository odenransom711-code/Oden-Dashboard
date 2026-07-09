# Fitness Simplified Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `gym.html`'s one-set-at-a-time logging (Gym+Day filter → exercise dropdown → weight/reps pill → tap "Log set" repeatedly) with a simpler flow: pick a day type (Upper/Lower/Cardio), add an exercise, log one entry per exercise per session (sets + reps + weight together).

**Architecture:** Five sequential tasks against the same file. Task 1 lands the new data model (CONFIG defaults, `state` shape, no more `gyms`). Tasks 2 and 3 build the new UI on top of that model (logging form, exercise modal) and are independent of each other. Task 4 adapts the coaching features (prescriptions, "last time," history) to the new per-session log shape — it depends on both Task 1 (exercises no longer have `repMin`/`repMax`/`step`) and Task 2 (logs now carry a `sets` field). Task 5 is an independent cleanup (removing the now-orphaned "Manage Gyms" section from Settings).

**Tech Stack:** Plain HTML/CSS/JS, matching `gym.html`'s existing conventions (`const`/arrow functions, `$()` id-lookup helper, template-string HTML building). No test framework exists in this repo. No real exercise/log data exists yet in this dashboard (confirmed with the user) — this is a clean replacement, not a migration.

## Global Constraints

- `state.logs[exerciseId]` entries change shape from `{weight, reps, date}` (one per set) to `{weight, sets, reps, date}` (one per exercise per session).
- `state.exercises[i]` drops `gym`, `repMin`, `repMax`, `step`, `startWeight` — keeps only `id`, `name`, `day`, `bw`.
- `CONFIG.days`/`state.days` default changes from Push/Pull/Legs to Upper/Lower/Cardio (ids: `upper`, `lower`, `cardio`). `CONFIG.splitRotation` updates to match: `["upper", "lower", "cardio", "rest"]`.
- The gym dimension (`CONFIG.gyms`, `state.gyms`, `state.filterGym`, every exercise's `gym` field, the "Gym" segmented filter, the "Manage Gyms" Settings section) is removed entirely — not deprecated, not hidden, deleted.
- Weight-increment suggestions use one fixed global step instead of a per-exercise `step`: `CONFIG.upgradeStepKg = 2.5`, `CONFIG.upgradeStepLb = 5`.
- The new prescription rule (`getRx()`): for weighted exercises, if the last 2+ consecutive sessions logged the same weight, suggest adding the global step next time; otherwise suggest repeating the same sets/reps/weight. For bodyweight exercises, if the last 2+ consecutive sessions hit the same rep count, suggest one more rep; otherwise suggest repeating.
- 1RM/best-set math (`estimate1RM()`), the sparkline, and the composition estimate need **no code changes** — they already read only `weight`/`reps`/`date` per log entry generically, which still exist unchanged in the new shape.
- Quick-tag, weight-tracking, and Today's/Past Workouts summaries need no logic changes — they don't depend on the fields being removed.

---

### Task 1: Data model — CONFIG, state normalization, exercise filtering

**Files:**
- Modify: `gym.html` (CONFIG block, `normalize()`, `getFiltered()`, `gymName()` removal)

**Interfaces:**
- Consumes: nothing (first task)
- Produces (for later tasks to rely on):
  - `CONFIG.days` = `[{id:"upper",name:"Upper"},{id:"lower",name:"Lower"},{id:"cardio",name:"Cardio"}]`
  - `CONFIG.splitRotation` = `["upper", "lower", "cardio", "rest"]`
  - `CONFIG.upgradeStepKg` = `2.5`, `CONFIG.upgradeStepLb` = `5`
  - `CONFIG.defaultExercises` entries shaped `{name, day, bw?}` (no `gym`/`repMin`/`repMax`/`step`/`startWeight`)
  - `state.exercises[i]` shaped `{id, name, day, bw}` (no `gym`)
  - `state.days`, `state.filterDay` (unchanged mechanism, new default data) — `state.gyms`/`state.filterGym` no longer exist
  - `getFiltered()` filters by `e.day === state.filterDay` only

- [ ] **Step 1: Replace the CONFIG block**

In `gym.html`, find this exact block (currently lines 20-93):

```javascript
const CONFIG = {
  appTitle: "Progressive Overload Coach",

  // Weight unit shown everywhere. "kg" or "lb".
  units: "kg",

  // Gyms you train at. Add as many as you want.
  // `id` must be a short unique slug (no spaces). `name` is what people see.
  gyms: [
    { id: "home",  name: "Home Gym" },
    { id: "comm",  name: "Commercial Gym" }
  ],

  // Training split. Most people use Push/Pull/Legs but you can rename
  // these to "Upper", "Lower", "Full Body", "Day A", anything.
  days: [
    { id: "push", name: "Push" },
    { id: "pull", name: "Pull" },
    { id: "legs", name: "Legs" }
  ],

  // Split rotation — the order your training days cycle through. Use day
  // ids from `days` above, plus "rest" for off-days. The pill at the top
  // of the app reads this + splitAnchor to compute "what day is today".
  splitRotation: ["push", "pull", "legs", "rest"],

  // Anchor: pair a real calendar date with which split day fell on it.
  // The rotation advances from this point. Set `date` to a recent day
  // when you knew what split you were on, and `splitId` to that day.
  // Edit this if your split drifts.
  splitAnchor: {
    date: "2026-05-12",
    splitId: "rest"
  },

  // Progression rule: hit this many reps on the top set → coach tells you
  // to add weight next session. Lower this to be more aggressive (e.g. 6),
  // raise it for more volume bias (e.g. 10).
  upgradeAtReps: 8,

  // Composition estimate (optional, for the weight chart).
  // Estimates how much of recent weight change is muscle vs fat by
  // cross-referencing the strength trend. Set yearsTraining to scale
  // expected muscle gain rate.
  composition: {
    enabled: true,
    yearsTraining: 1,        // 1 = beginner, 2 = intermediate, 3+ = advanced
    windowDays: 30           // window to compute weight + strength change
  },

  // Starter exercise list. Each one needs:
  //   name        — what shows in the dropdown
  //   gym         — one of the gym ids above, or "both"
  //   day         — one of the day ids above
  //   repMin      — bottom of your target rep range
  //   repMax      — top of your target rep range
  //   step        — how much weight you add when progressing (kg/lb)
  //   startWeight — starting weight (ignored when bw: true)
  //   bw          — true for bodyweight movements (logs reps only)
  //
  // First-run defaults. Once a user logs anything, they edit through
  // the in-app + / gear buttons; this block stays as the seed.
  defaultExercises: [
    { name: "Bench press",     gym: "comm", day: "push", repMin: 5, repMax: 8,  step: 2.5, startWeight: 60 },
    { name: "Overhead press",  gym: "comm", day: "push", repMin: 5, repMax: 8,  step: 2.5, startWeight: 35 },
    { name: "Tricep pushdown", gym: "comm", day: "push", repMin: 8, repMax: 12, step: 2.5, startWeight: 25 },
    { name: "Pull-ups",        gym: "both", day: "pull", repMin: 5, repMax: 10, step: 1,   startWeight: 0, bw: true },
    { name: "Barbell row",     gym: "comm", day: "pull", repMin: 6, repMax: 10, step: 2.5, startWeight: 50 },
    { name: "Bicep curl",      gym: "comm", day: "pull", repMin: 8, repMax: 12, step: 1.25,startWeight: 15 },
    { name: "Back squat",      gym: "comm", day: "legs", repMin: 5, repMax: 8,  step: 5,   startWeight: 80 },
    { name: "Romanian deadlift", gym: "comm", day: "legs", repMin: 6, repMax: 10, step: 5, startWeight: 60 },
    { name: "Leg press",       gym: "comm", day: "legs", repMin: 8, repMax: 12, step: 5,   startWeight: 100 }
  ]
};
```

Replace it with:

```javascript
const CONFIG = {
  appTitle: "Progressive Overload Coach",

  // Weight unit shown everywhere. "kg" or "lb".
  units: "kg",

  // Training split. Pick the day type when you log a session — rename
  // these in Settings if you want different categories.
  days: [
    { id: "upper",  name: "Upper" },
    { id: "lower",  name: "Lower" },
    { id: "cardio", name: "Cardio" }
  ],

  // Split rotation — the order your training days cycle through. Use day
  // ids from `days` above, plus "rest" for off-days. The pill at the top
  // of the app reads this + splitAnchor to compute "what day is today".
  splitRotation: ["upper", "lower", "cardio", "rest"],

  // Anchor: pair a real calendar date with which split day fell on it.
  // The rotation advances from this point. Set `date` to a recent day
  // when you knew what split you were on, and `splitId` to that day.
  // Edit this if your split drifts.
  splitAnchor: {
    date: "2026-05-12",
    splitId: "rest"
  },

  // Fixed weight increment the coach suggests when it recommends adding
  // weight (used instead of a per-exercise step now that logging is
  // simpler — kg used if units is "kg", lb used if units is "lb").
  upgradeStepKg: 2.5,
  upgradeStepLb: 5,

  // Composition estimate (optional, for the weight chart).
  // Estimates how much of recent weight change is muscle vs fat by
  // cross-referencing the strength trend. Set yearsTraining to scale
  // expected muscle gain rate.
  composition: {
    enabled: true,
    yearsTraining: 1,        // 1 = beginner, 2 = intermediate, 3+ = advanced
    windowDays: 30           // window to compute weight + strength change
  },

  // Starter exercise list. Each one needs:
  //   name — what shows in the dropdown
  //   day  — one of the day ids above
  //   bw   — true for bodyweight movements (logs reps only, no weight)
  //
  // First-run defaults. Once a user logs anything, they edit through
  // the in-app + / gear buttons; this block stays as the seed.
  defaultExercises: [
    { name: "Bench press",       day: "upper" },
    { name: "Overhead press",    day: "upper" },
    { name: "Pull-ups",          day: "upper", bw: true },
    { name: "Back squat",        day: "lower" },
    { name: "Romanian deadlift", day: "lower" },
    { name: "Leg press",         day: "lower" },
    { name: "Running",           day: "cardio", bw: true }
  ]
};
```

- [ ] **Step 2: Drop gym seeding from `normalize()`**

In `gym.html`, find this exact block:

```javascript
  function normalize(s) {
    s = s || {};
    s.units = s.units || CONFIG.units || 'kg';
    s.gyms  = (Array.isArray(s.gyms)  && s.gyms.length)  ? s.gyms  : CONFIG.gyms.slice();
    s.days  = (Array.isArray(s.days)  && s.days.length)  ? s.days  : CONFIG.days.slice();
    s.exercises = Array.isArray(s.exercises) ? s.exercises : buildDefaultExercises();
    s.logs = (s.logs && typeof s.logs === 'object') ? s.logs : {};
    s.filterGym = s.filterGym || s.gyms[0].id;
    s.filterDay = s.filterDay || s.days[0].id;
```

Replace it with:

```javascript
  function normalize(s) {
    s = s || {};
    s.units = s.units || CONFIG.units || 'kg';
    s.days  = (Array.isArray(s.days)  && s.days.length)  ? s.days  : CONFIG.days.slice();
    s.exercises = Array.isArray(s.exercises) ? s.exercises : buildDefaultExercises();
    s.logs = (s.logs && typeof s.logs === 'object') ? s.logs : {};
    s.filterDay = s.filterDay || s.days[0].id;
```

- [ ] **Step 3: Drop the gym dimension from `getFiltered()`**

In `gym.html`, find this exact block:

```javascript
  function getFiltered() {
    return state.exercises.filter(e =>
      (e.gym === state.filterGym || e.gym === 'both') && e.day === state.filterDay);
  }
```

Replace it with:

```javascript
  function getFiltered() {
    return state.exercises.filter(e => e.day === state.filterDay);
  }
```

- [ ] **Step 4: Remove the now-unused `gymName()` helper**

In `gym.html`, find this exact block:

```javascript
  function gymName(id) { const g = state.gyms.find(x => x.id === id); return g ? g.name : id; }
  function dayName(id) { const d = state.days.find(x => x.id === id); return d ? d.name : id; }
```

Replace it with:

```javascript
  function dayName(id) { const d = state.days.find(x => x.id === id); return d ? d.name : id; }
```

- [ ] **Step 5: Verify the file is well-formed**

Run:
```bash
node -e "
var fs = require('fs');
var s = fs.readFileSync('gym.html', 'utf8');
var re = /<script>([\s\S]*?)<\/script>/g;
var m, count = 0;
while ((m = re.exec(s))) { new Function(m[1]); count++; }
console.log('checked', count, 'inline script blocks OK');
"
```
Expected: prints a count with no syntax errors thrown. (This task alone will leave the page in a broken intermediate state if opened in a browser — the HTML still references `#gymSeg` which `renderFilters()` still populates until Task 2 lands. That's expected and fine; each task is reviewed on its own before the next lands, and the whole plan ships together at the end. The syntax check just confirms the JS itself parses.)

- [ ] **Step 6: Commit**

```bash
git add gym.html
git commit -m "$(cat <<'EOF'
Simplify Fitness data model: Upper/Lower/Cardio, drop gyms

Phase 1 of the simplified-logging rework: CONFIG defaults change to
Upper/Lower/Cardio day types, the gym dimension (gyms, filterGym,
per-exercise gym field) is removed entirely, and exercises drop their
progressive-overload configuration fields (repMin/repMax/step/
startWeight) — kept only where a later task still reads them, which
none do after this commit finishes landing across the full plan.
EOF
)"
```

---

### Task 2: New logging UI — day-type filter, session log form

**Files:**
- Modify: `gym.html` (CSS: new 3-column log grid; HTML: filter row, log form; JS: `renderFilters()`, `renderRepsRow()`, sets-pill wiring, `logBtn` handler, weight pre-fill)

**Interfaces:**
- Consumes from Task 1: `state.days`, `state.filterDay`, `getFiltered()`
- Produces (for Task 4 to rely on): logged entries shaped `{weight, sets, reps, date}` pushed to `state.logs[exerciseId]`; `#setsRow` element with the same `data-value` pill-picker pattern as `#repsRow`

- [ ] **Step 1: Add the 3-column log grid CSS**

In `gym.html`, find this exact block:

```css
.po-log-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px;
}
.po-log-grid.po-bw-mode { grid-template-columns: 1fr; }
```

Replace it with:

```css
.po-log-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px;
}
.po-log-grid.po-bw-mode { grid-template-columns: 1fr; }
.po-log-grid-3 {
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 14px;
}
.po-log-grid-3.po-bw-mode { grid-template-columns: 1fr 1fr; }
```

- [ ] **Step 2: Add the mobile override for the new grid**

In `gym.html`, find this exact line:

```css
  .po-log-grid { grid-template-columns: 1fr; gap: 14px; }
```

Replace it with:

```css
  .po-log-grid { grid-template-columns: 1fr; gap: 14px; }
  .po-log-grid-3 { grid-template-columns: 1fr; gap: 14px; }
```

- [ ] **Step 3: Replace the filter row HTML (drop the Gym row)**

In `gym.html`, find this exact block:

```html
  <div class="card">
    <!-- Filters -->
    <div class="po-filters">
      <div class="po-seg-row">
        <span class="po-seg-label">Gym</span>
        <div class="po-seg-control" id="gymSeg"></div>
      </div>
      <div class="po-seg-row">
        <span class="po-seg-label">Day</span>
        <div class="po-seg-control" id="daySeg"></div>
      </div>
    </div>
```

Replace it with:

```html
  <div class="card">
    <!-- Filters -->
    <div class="po-filters">
      <div class="po-seg-row">
        <span class="po-seg-label">Day type</span>
        <div class="po-seg-control" id="daySeg"></div>
      </div>
    </div>
```

- [ ] **Step 4: Replace the log form HTML (add a Sets field)**

In `gym.html`, find this exact block:

```html
    <!-- Log a set -->
    <div class="po-sub-section">
      <div class="po-sub-title">Log today's top set</div>
      <div class="po-bw-banner" id="bwBanner">Bodyweight — log reps only</div>
      <div class="po-last-set" id="lastSet">
        <span class="po-last-label">Last time</span>
        <span class="po-last-value" id="lastSetValue"></span>
        <span class="po-last-meta" id="lastSetMeta"></span>
      </div>
      <div class="po-log-grid" id="logGrid">
        <div class="po-field" id="weightField">
          <label id="weightLabel">Weight (kg)</label>
          <div class="po-weight-row">
            <button class="po-w-btn" id="weightDownBtn" type="button">−</button>
            <input type="number" id="weightInput" step="0.5" inputmode="decimal" placeholder="0">
            <button class="po-w-btn" id="weightUpBtn" type="button">+</button>
          </div>
        </div>
        <div class="po-field">
          <label>Reps</label>
          <div class="po-reps-row" id="repsRow" data-value="8">
            <button type="button" class="po-reps-pill" data-v="4">4</button>
            <button type="button" class="po-reps-pill" data-v="5">5</button>
            <button type="button" class="po-reps-pill" data-v="6">6</button>
            <button type="button" class="po-reps-pill" data-v="7">7</button>
            <button type="button" class="po-reps-pill active" data-v="8">8</button>
            <button type="button" class="po-reps-pill" data-v="9">9</button>
            <button type="button" class="po-reps-pill" data-v="10">10</button>
            <button type="button" class="po-reps-pill" data-v="11">11</button>
            <button type="button" class="po-reps-pill" data-v="12">12</button>
          </div>
        </div>
      </div>
      <button class="po-btn-primary" id="logBtn">Log set</button>
    </div>
```

Replace it with:

```html
    <!-- Log a session -->
    <div class="po-sub-section">
      <div class="po-sub-title">Log this session</div>
      <div class="po-bw-banner" id="bwBanner">Bodyweight — log reps only</div>
      <div class="po-last-set" id="lastSet">
        <span class="po-last-label">Last time</span>
        <span class="po-last-value" id="lastSetValue"></span>
        <span class="po-last-meta" id="lastSetMeta"></span>
      </div>
      <div class="po-log-grid-3" id="logGrid">
        <div class="po-field" id="weightField">
          <label id="weightLabel">Weight (kg)</label>
          <div class="po-weight-row">
            <button class="po-w-btn" id="weightDownBtn" type="button">−</button>
            <input type="number" id="weightInput" step="0.5" inputmode="decimal" placeholder="0">
            <button class="po-w-btn" id="weightUpBtn" type="button">+</button>
          </div>
        </div>
        <div class="po-field">
          <label>Sets</label>
          <div class="po-reps-row" id="setsRow" data-value="3">
            <button type="button" class="po-reps-pill" data-v="1">1</button>
            <button type="button" class="po-reps-pill" data-v="2">2</button>
            <button type="button" class="po-reps-pill active" data-v="3">3</button>
            <button type="button" class="po-reps-pill" data-v="4">4</button>
            <button type="button" class="po-reps-pill" data-v="5">5</button>
            <button type="button" class="po-reps-pill" data-v="6">6</button>
          </div>
        </div>
        <div class="po-field">
          <label>Reps</label>
          <div class="po-reps-row" id="repsRow" data-value="8">
            <button type="button" class="po-reps-pill" data-v="4">4</button>
            <button type="button" class="po-reps-pill" data-v="5">5</button>
            <button type="button" class="po-reps-pill" data-v="6">6</button>
            <button type="button" class="po-reps-pill" data-v="7">7</button>
            <button type="button" class="po-reps-pill active" data-v="8">8</button>
            <button type="button" class="po-reps-pill" data-v="9">9</button>
            <button type="button" class="po-reps-pill" data-v="10">10</button>
            <button type="button" class="po-reps-pill" data-v="11">11</button>
            <button type="button" class="po-reps-pill" data-v="12">12</button>
          </div>
        </div>
      </div>
      <button class="po-btn-primary" id="logBtn">Log session</button>
    </div>
```

- [ ] **Step 5: Drop the gym filter from `renderFilters()`**

In `gym.html`, find this exact block:

```javascript
  function renderFilters() {
    $('gymSeg').innerHTML = state.gyms.map(g =>
      '<button class="po-seg-btn ' + (g.id === state.filterGym ? 'active' : '') + '" data-gym="' + g.id + '">' + escape(g.name) + '</button>'
    ).join('');
    $('daySeg').innerHTML = state.days.map(d =>
      '<button class="po-seg-btn ' + (d.id === state.filterDay ? 'active' : '') + '" data-day="' + d.id + '">' + escape(d.name) + '</button>'
    ).join('');
    $('gymSeg').querySelectorAll('.po-seg-btn').forEach(b => {
      b.addEventListener('click', () => { state.filterGym = b.dataset.gym; state.currentEx = null; saveState(); renderAll(); });
    });
    $('daySeg').querySelectorAll('.po-seg-btn').forEach(b => {
      b.addEventListener('click', () => {
        state.filterDay = b.dataset.day;
        state.currentEx = null;
        // User has now manually picked a day — stop auto-overriding to today's split.
        state._userPickedDay = true;
        saveState(); renderAll();
      });
    });
  }
```

Replace it with:

```javascript
  function renderFilters() {
    $('daySeg').innerHTML = state.days.map(d =>
      '<button class="po-seg-btn ' + (d.id === state.filterDay ? 'active' : '') + '" data-day="' + d.id + '">' + escape(d.name) + '</button>'
    ).join('');
    $('daySeg').querySelectorAll('.po-seg-btn').forEach(b => {
      b.addEventListener('click', () => {
        state.filterDay = b.dataset.day;
        state.currentEx = null;
        // User has now manually picked a day — stop auto-overriding to today's split.
        state._userPickedDay = true;
        saveState(); renderAll();
      });
    });
  }
```

- [ ] **Step 6: Simplify `renderRepsRow()` to a fixed 1-20 range**

In `gym.html`, find this exact block:

```javascript
  // Build the rep buttons based on the current exercise's repMin/repMax.
  // Always spans repMin → repMax + 2 (a small buffer for over-performing
  // sets that trigger the upgrade signal), capped at 16 buttons total so
  // wide ranges don't break the mobile layout.
  function renderRepsRow() {
    const row = document.getElementById('repsRow');
    if (!row) return;
    const ex = getCurrentEx();
    let repMin, repMax;
    if (ex) {
      repMin = Math.max(1, parseInt(ex.repMin, 10) || 1);
      repMax = Math.max(repMin, parseInt(ex.repMax, 10) || repMin);
    } else {
      repMin = 4; repMax = 12;
    }
    const upper = Math.max(repMax + 2, repMin + 5);
    const end = Math.min(upper, repMin + 15);

    // Preserve the previously-selected rep if it still fits in the new
    // range; otherwise default to the target (repMax).
    const prev = parseInt(row.dataset.value, 10);
    const active = (prev >= repMin && prev <= end) ? prev : repMax;

    let html = '';
    for (let i = repMin; i <= end; i++) {
      html += '<button type="button" class="po-reps-pill' +
        (i === active ? ' active' : '') +
        '" data-v="' + i + '">' + i + '</button>';
    }
    row.innerHTML = html;
    row.dataset.value = String(active);
  }
```

Replace it with:

```javascript
  // Build the rep buttons across a fixed 1-20 range — no longer tied to
  // a per-exercise rep-range configuration (exercises don't carry one).
  function renderRepsRow() {
    const row = document.getElementById('repsRow');
    if (!row) return;
    const repMin = 1, end = 20;
    const prev = parseInt(row.dataset.value, 10);
    const active = (prev >= repMin && prev <= end) ? prev : 8;
    let html = '';
    for (let i = repMin; i <= end; i++) {
      html += '<button type="button" class="po-reps-pill' +
        (i === active ? ' active' : '') +
        '" data-v="' + i + '">' + i + '</button>';
    }
    row.innerHTML = html;
    row.dataset.value = String(active);
  }
```

- [ ] **Step 7: Wire the Sets pill row and update the Log button handler**

In `gym.html`, find this exact block:

```javascript
  $('logBtn').addEventListener('click', () => {
    const ex = getCurrentEx();
    if (!ex) return;
    const reps = parseInt($('repsRow').dataset.value, 10) || 0;
    if (reps <= 0) { alert('Pick a rep count.'); return; }
    const w = ex.bw ? 0 : (parseFloat($('weightInput').value) || 0);
    if (!ex.bw && w <= 0) { alert('Enter a weight.'); return; }
    const arr = state.logs[ex.id] || [];
    arr.push({ weight: w, reps: reps, date: new Date().toISOString() });
    state.logs[ex.id] = arr;
    saveState(); renderAll();
    // Strength changed → composition estimate may shift
    if (typeof wtRender === 'function') wtRender();
    // Tiny pulse on the button so the user feels the save
    const btn = $('logBtn');
    btn.style.transition = 'transform 0.15s';
    btn.style.transform = 'scale(0.96)';
    setTimeout(() => { btn.style.transform = ''; }, 160);
  });
```

Replace it with:

```javascript
  $('setsRow').addEventListener('click', (e) => {
    const p = e.target.closest('.po-reps-pill');
    if (!p) return;
    $('setsRow').querySelectorAll('.po-reps-pill').forEach(x => x.classList.remove('active'));
    p.classList.add('active');
    $('setsRow').dataset.value = p.dataset.v;
  });
  $('logBtn').addEventListener('click', () => {
    const ex = getCurrentEx();
    if (!ex) return;
    const sets = parseInt($('setsRow').dataset.value, 10) || 0;
    if (sets <= 0) { alert('Pick a set count.'); return; }
    const reps = parseInt($('repsRow').dataset.value, 10) || 0;
    if (reps <= 0) { alert('Pick a rep count.'); return; }
    const w = ex.bw ? 0 : (parseFloat($('weightInput').value) || 0);
    if (!ex.bw && w <= 0) { alert('Enter a weight.'); return; }
    const arr = state.logs[ex.id] || [];
    arr.push({ weight: w, sets: sets, reps: reps, date: new Date().toISOString() });
    state.logs[ex.id] = arr;
    saveState(); renderAll();
    // Strength changed → composition estimate may shift
    if (typeof wtRender === 'function') wtRender();
    // Tiny pulse on the button so the user feels the save
    const btn = $('logBtn');
    btn.style.transition = 'transform 0.15s';
    btn.style.transform = 'scale(0.96)';
    setTimeout(() => { btn.style.transform = ''; }, 160);
  });
```

- [ ] **Step 8: Fix the weight pre-fill (drop the removed `startWeight` fallback)**

In `gym.html`, find this exact block:

```javascript
    // Pre-fill weight input with last logged weight (or starting weight)
    const ex = getCurrentEx();
    if (ex && !ex.bw) {
      const logs = getLogs();
      const w = logs.length ? logs[logs.length - 1].weight : (ex.startWeight || 0);
      $('weightInput').value = w;
    }
```

Replace it with:

```javascript
    // Pre-fill weight input with last logged weight, if any
    const ex = getCurrentEx();
    if (ex && !ex.bw) {
      const logs = getLogs();
      const w = logs.length ? logs[logs.length - 1].weight : 0;
      $('weightInput').value = w;
    }
```

- [ ] **Step 9: Verify the file is well-formed**

Run:
```bash
node -e "
var fs = require('fs');
var s = fs.readFileSync('gym.html', 'utf8');
var re = /<script>([\s\S]*?)<\/script>/g;
var m, count = 0;
while ((m = re.exec(s))) { new Function(m[1]); count++; }
console.log('checked', count, 'inline script blocks OK');
"
```
Expected: prints a count with no syntax errors thrown.

Also run:
```bash
grep -c 'gymSeg\|filterGym\|state\.gyms' gym.html
```
Expected: `0` (Task 1 already removed the underlying data; this task removes every remaining HTML/JS reference to the gym filter UI)

- [ ] **Step 10: Manually verify in a browser**

Serve the directory (`python3 -m http.server 8123` from the repo root) and use Playwright MCP tools to navigate to `http://localhost:8123/gym.html` (or, if Playwright's Chromium binary is unavailable in this environment — a known issue seen throughout this project — fall back to curl-fetching the served HTML to confirm no `gymSeg`/`Gym` filter row exists and the log form has three fields (Weight, Sets, Reps), reporting `DONE_WITH_CONCERNS`).

Confirm: the Day type selector shows Upper/Lower/Cardio (or shows the default seed exercises' filtered view correctly); selecting a day type filters the exercise dropdown; picking sets/reps/weight and tapping "Log session" adds one entry to that exercise's log (verify via `localStorage.getItem('po_coach_v1')` in devtools/`browser_evaluate` showing a `{weight, sets, reps, date}` object, not a bare `{weight, reps, date}`).

- [ ] **Step 11: Commit**

```bash
git add gym.html
git commit -m "$(cat <<'EOF'
Add simplified session logging UI to Fitness page

Phase 2 of the simplified-logging rework: the Gym filter row is gone,
the log form now has Weight + Sets + Reps fields logging one combined
entry per exercise per session instead of tapping "Log set" per set.
EOF
)"
```

---

### Task 3: Simplified exercise add/edit modal

**Files:**
- Modify: `gym.html` (HTML: modal fields; JS: `renderModalSegs()`, `openExModal()`, remove `toggleBwFields()`, `exModalSave` handler, `modalGym` variable)

**Interfaces:**
- Consumes from Task 1: `state.days`, `state.filterDay`, `escape()`, `uid()`
- Produces: exercises pushed to `state.exercises` shaped `{id, name, day, bw}` (no `gym`/`repMin`/`repMax`/`step`/`startWeight`)

This task is independent of Task 2 — both depend only on Task 1, not on each other. Apply in either order.

- [ ] **Step 1: Simplify the Add/Edit Exercise modal HTML**

In `gym.html`, find this exact block:

```html
<!-- Add / Edit Exercise Modal -->
<div class="po-modal-bg" id="exModalBg">
  <div class="po-modal">
    <h3 id="exModalTitle">Add exercise</h3>
    <div class="po-field">
      <label style="font-size:11px;color:var(--text-3);font-weight:700;letter-spacing:0.04em;text-transform:uppercase">Name</label>
      <input type="text" id="exName" placeholder="e.g. Incline DB press">
    </div>
    <div class="po-field">
      <label style="font-size:11px;color:var(--text-3);font-weight:700;letter-spacing:0.04em;text-transform:uppercase">Gym</label>
      <div class="po-modal-seg" id="exGymSeg"></div>
    </div>
    <div class="po-field">
      <label style="font-size:11px;color:var(--text-3);font-weight:700;letter-spacing:0.04em;text-transform:uppercase">Day</label>
      <div class="po-modal-seg" id="exDaySeg"></div>
    </div>
    <label class="po-bw-toggle">
      <input type="checkbox" id="exBw">
      Bodyweight (track reps only, no weight)
    </label>
    <div class="po-field" id="exStartWeightField">
      <label style="font-size:11px;color:var(--text-3);font-weight:700;letter-spacing:0.04em;text-transform:uppercase">Starting weight</label>
      <input type="number" id="exStartWeight" step="0.5" placeholder="20" value="20">
    </div>
    <div class="po-log-grid" id="exNumFields">
      <div class="po-field">
        <label style="font-size:11px;color:var(--text-3);font-weight:700;letter-spacing:0.04em;text-transform:uppercase">Reps min</label>
        <input type="number" id="exRepMin" value="6">
      </div>
      <div class="po-field">
        <label style="font-size:11px;color:var(--text-3);font-weight:700;letter-spacing:0.04em;text-transform:uppercase">Reps max</label>
        <input type="number" id="exRepMax" value="8">
      </div>
    </div>
    <div class="po-field" id="exStepField">
      <label style="font-size:11px;color:var(--text-3);font-weight:700;letter-spacing:0.04em;text-transform:uppercase">Increment</label>
      <input type="number" id="exStep" step="0.5" value="2.5">
    </div>
    <div class="po-modal-actions">
      <button class="po-btn-secondary" id="exModalCancel">Cancel</button>
      <button class="po-btn-primary" id="exModalSave">Save</button>
    </div>
    <span class="po-delete-link" id="exDelete" style="display:none">Delete this exercise</span>
  </div>
</div>
```

Replace it with:

```html
<!-- Add / Edit Exercise Modal -->
<div class="po-modal-bg" id="exModalBg">
  <div class="po-modal">
    <h3 id="exModalTitle">Add exercise</h3>
    <div class="po-field">
      <label style="font-size:11px;color:var(--text-3);font-weight:700;letter-spacing:0.04em;text-transform:uppercase">Name</label>
      <input type="text" id="exName" placeholder="e.g. Incline DB press">
    </div>
    <div class="po-field">
      <label style="font-size:11px;color:var(--text-3);font-weight:700;letter-spacing:0.04em;text-transform:uppercase">Day type</label>
      <div class="po-modal-seg" id="exDaySeg"></div>
    </div>
    <label class="po-bw-toggle">
      <input type="checkbox" id="exBw">
      Bodyweight (track reps only, no weight)
    </label>
    <div class="po-modal-actions">
      <button class="po-btn-secondary" id="exModalCancel">Cancel</button>
      <button class="po-btn-primary" id="exModalSave">Save</button>
    </div>
    <span class="po-delete-link" id="exDelete" style="display:none">Delete this exercise</span>
  </div>
</div>
```

- [ ] **Step 2: Drop the `modalGym` variable**

In `gym.html`, find this exact line:

```javascript
  let modalGym = null, modalDay = null;
```

Replace it with:

```javascript
  let modalDay = null;
```

- [ ] **Step 3: Simplify `renderModalSegs()` to day-only**

In `gym.html`, find this exact block:

```javascript
  function renderModalSegs() {
    $('exGymSeg').innerHTML = state.gyms.map(g =>
      '<button data-gym="' + g.id + '" class="' + (modalGym === g.id ? 'active' : '') + '">' + escape(g.name) + '</button>'
    ).join('') + '<button data-gym="both" class="' + (modalGym === 'both' ? 'active' : '') + '">Both</button>';
    $('exDaySeg').innerHTML = state.days.map(d =>
      '<button data-day="' + d.id + '" class="' + (modalDay === d.id ? 'active' : '') + '">' + escape(d.name) + '</button>'
    ).join('');
    $('exGymSeg').querySelectorAll('button').forEach(b => {
      b.addEventListener('click', () => {
        modalGym = b.dataset.gym;
        $('exGymSeg').querySelectorAll('button').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
      });
    });
    $('exDaySeg').querySelectorAll('button').forEach(b => {
      b.addEventListener('click', () => {
        modalDay = b.dataset.day;
        $('exDaySeg').querySelectorAll('button').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
      });
    });
  }
```

Replace it with:

```javascript
  function renderModalSegs() {
    $('exDaySeg').innerHTML = state.days.map(d =>
      '<button data-day="' + d.id + '" class="' + (modalDay === d.id ? 'active' : '') + '">' + escape(d.name) + '</button>'
    ).join('');
    $('exDaySeg').querySelectorAll('button').forEach(b => {
      b.addEventListener('click', () => {
        modalDay = b.dataset.day;
        $('exDaySeg').querySelectorAll('button').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
      });
    });
  }
```

- [ ] **Step 4: Simplify `openExModal()`**

In `gym.html`, find this exact block:

```javascript
  function openExModal(mode, ex) {
    editingExId = mode === 'edit' ? ex.id : null;
    $('exModalTitle').textContent = mode === 'edit' ? 'Edit exercise' : 'Add exercise';
    $('exDelete').style.display = mode === 'edit' ? 'block' : 'none';
    if (mode === 'edit') {
      $('exName').value = ex.name;
      modalGym = ex.gym;
      modalDay = ex.day;
      $('exBw').checked = !!ex.bw;
      $('exStartWeight').value = ex.startWeight || 0;
      $('exRepMin').value = ex.repMin;
      $('exRepMax').value = ex.repMax;
      $('exStep').value = ex.step;
    } else {
      $('exName').value = '';
      modalGym = state.filterGym;
      modalDay = state.filterDay;
      $('exBw').checked = false;
      $('exStartWeight').value = 20;
      $('exRepMin').value = 6;
      $('exRepMax').value = 8;
      $('exStep').value = 2.5;
    }
    renderModalSegs();
    toggleBwFields();
    $('exModalBg').classList.add('show');
    setTimeout(() => $('exName').focus(), 60);
  }
```

Replace it with:

```javascript
  function openExModal(mode, ex) {
    editingExId = mode === 'edit' ? ex.id : null;
    $('exModalTitle').textContent = mode === 'edit' ? 'Edit exercise' : 'Add exercise';
    $('exDelete').style.display = mode === 'edit' ? 'block' : 'none';
    if (mode === 'edit') {
      $('exName').value = ex.name;
      modalDay = ex.day;
      $('exBw').checked = !!ex.bw;
    } else {
      $('exName').value = '';
      modalDay = state.filterDay;
      $('exBw').checked = false;
    }
    renderModalSegs();
    $('exModalBg').classList.add('show');
    setTimeout(() => $('exName').focus(), 60);
  }
```

- [ ] **Step 5: Remove `toggleBwFields()` and its listener**

In `gym.html`, find this exact block:

```javascript
  function toggleBwFields() {
    const isBw = $('exBw').checked;
    $('exStartWeightField').style.display = isBw ? 'none' : '';
    $('exStepField').style.display = isBw ? 'none' : '';
  }
  $('exBw').addEventListener('change', toggleBwFields);
  $('addExBtn').addEventListener('click', () => openExModal('add'));
```

Replace it with:

```javascript
  $('addExBtn').addEventListener('click', () => openExModal('add'));
```

- [ ] **Step 6: Simplify the `exModalSave` handler**

In `gym.html`, find this exact block:

```javascript
  $('exModalSave').addEventListener('click', () => {
    const name = $('exName').value.trim();
    if (!name) { alert('Name is required.'); return; }
    if (!modalGym) { alert('Pick a gym.'); return; }
    if (!modalDay) { alert('Pick a day.'); return; }
    const isBw = $('exBw').checked;
    const repMin = parseInt($('exRepMin').value, 10) || 6;
    const repMax = parseInt($('exRepMax').value, 10) || 8;
    const data = {
      name, gym: modalGym, day: modalDay,
      bw: isBw,
      startWeight: isBw ? 0 : (parseFloat($('exStartWeight').value) || 0),
      repMin, repMax,
      step: isBw ? 1 : (parseFloat($('exStep').value) || 2.5)
    };
    if (editingExId) {
      const ex = state.exercises.find(e => e.id === editingExId);
      if (ex) Object.assign(ex, data);
    } else {
      const ex = Object.assign({ id: uid() }, data);
      state.exercises.push(ex);
      state.currentEx = ex.id;
      state.filterGym = (modalGym === 'both') ? state.filterGym : modalGym;
      state.filterDay = modalDay;
    }
    saveState();
    $('exModalBg').classList.remove('show');
    renderAll();
  });
```

Replace it with:

```javascript
  $('exModalSave').addEventListener('click', () => {
    const name = $('exName').value.trim();
    if (!name) { alert('Name is required.'); return; }
    if (!modalDay) { alert('Pick a day type.'); return; }
    const isBw = $('exBw').checked;
    const data = { name, day: modalDay, bw: isBw };
    if (editingExId) {
      const ex = state.exercises.find(e => e.id === editingExId);
      if (ex) Object.assign(ex, data);
    } else {
      const ex = Object.assign({ id: uid() }, data);
      state.exercises.push(ex);
      state.currentEx = ex.id;
      state.filterDay = modalDay;
    }
    saveState();
    $('exModalBg').classList.remove('show');
    renderAll();
  });
```

- [ ] **Step 7: Verify the file is well-formed**

Run:
```bash
node -e "
var fs = require('fs');
var s = fs.readFileSync('gym.html', 'utf8');
var re = /<script>([\s\S]*?)<\/script>/g;
var m, count = 0;
while ((m = re.exec(s))) { new Function(m[1]); count++; }
console.log('checked', count, 'inline script blocks OK');
"
```
Expected: prints a count with no syntax errors thrown.

Also run:
```bash
grep -c 'exGymSeg\|exStartWeight\|exRepMin\|exRepMax\|exStep\b\|modalGym\|toggleBwFields' gym.html
```
Expected: `0`

- [ ] **Step 8: Manually verify in a browser**

Serve the directory and use Playwright MCP tools (or the curl/code-trace fallback from Task 2 Step 10 if Chromium is unavailable, reporting `DONE_WITH_CONCERNS`) to confirm: tapping "+" opens a modal with only Name, Day type, and a Bodyweight toggle; saving creates an exercise with no `gym`/`repMin`/`repMax`/`step`/`startWeight` fields (check via `localStorage.getItem('po_coach_v1')`); editing an existing exercise pre-fills its name/day/bodyweight state correctly.

- [ ] **Step 9: Commit**

```bash
git add gym.html
git commit -m "$(cat <<'EOF'
Simplify the Add/Edit Exercise modal on the Fitness page

Phase 3 of the simplified-logging rework: adding an exercise now only
needs a name, a day type, and a bodyweight toggle — the gym picker and
the repMin/repMax/step/startWeight progressive-overload configuration
fields are gone.
EOF
)"
```

---

### Task 4: Adapt prescriptions, "last time," and history to session-shaped logs

**Files:**
- Modify: `gym.html` (JS: `getRx()`, `renderRx()`, `renderLastSet()`, `renderHistory()`)

**Interfaces:**
- Consumes from Task 1: `CONFIG.upgradeStepKg`, `CONFIG.upgradeStepLb`, `unit()`
- Consumes from Task 2: log entries shaped `{weight, sets, reps, date}`
- Produces: nothing consumed elsewhere (last functional task; Task 5 is independent cleanup)

This task depends on both Task 1 and Task 2 having landed — `getRx()` currently destructures `ex.repMin`/`ex.repMax`/`ex.step` (removed in Task 1) and reads `last.weight`/`last.reps` from a log entry that doesn't yet have a `sets` field until Task 2 lands.

- [ ] **Step 1: Rewrite `getRx()` with the new session-based rule**

In `gym.html`, find this exact block:

```javascript
  function getRx(ex, logs) {
    if (!logs.length) return null;
    const last = logs[logs.length - 1];
    const { weight, reps } = last;
    const { repMin, repMax, step, bw } = ex;
    const upgradeAt = Math.min(CONFIG.upgradeAtReps || 8, repMax);
    let stuck = 0;
    for (let i = logs.length - 1; i >= 0; i--) {
      if (logs[i].weight === weight) stuck++; else break;
    }
    if (bw) {
      if (reps >= upgradeAt) return { type: 'up', weight: 0, reps: reps + 1, tag: 'Push for more', reason: reps + ' reps — strong. Push for ' + (reps + 1) + ' next time.', bw: true };
      if (reps >= repMin) return { type: 'hold', weight: 0, reps: reps + 1, tag: 'Add a rep', reason: reps + ' reps. Push for ' + (reps + 1) + ' next session.', bw: true };
      return { type: 'hold', weight: 0, reps: repMin, tag: 'Repeat', reason: reps + ' reps fell short. Repeat until you hit ' + repMin + '+.', bw: true };
    }
    if (stuck >= 3 && reps < repMin) {
      const dl = roundToStep(weight * 0.9, step);
      return { type: 'down', weight: dl, reps: repMax, tag: 'Deload', reason: 'Stuck at ' + weight + unit() + ' for ' + stuck + ' sessions. Drop 10%, reset, build back cleaner.' };
    }
    if (reps >= upgradeAt) return { type: 'up', weight: weight + step, reps: repMin, tag: 'Add weight', reason: 'You hit ' + reps + ' reps — time to add ' + step + unit() + '. Expect ' + repMin + '-' + (repMin + 1) + ' next session.' };
    if (reps >= repMin && reps < upgradeAt) return { type: 'hold', weight: weight, reps: reps + 1, tag: 'Add a rep', reason: reps + ' reps in target. Stay at ' + weight + unit() + ', push for ' + (reps + 1) + '.' };
    return { type: 'hold', weight: weight, reps: repMin, tag: 'Repeat', reason: reps + ' reps short of ' + repMin + '-' + upgradeAt + '. Repeat ' + weight + unit() + ' until you hit ' + repMin + '+ clean.' };
  }
```

Replace it with:

```javascript
  function getRx(ex, logs) {
    if (!logs.length) return null;
    const last = logs[logs.length - 1];
    const { weight, sets, reps } = last;
    if (ex.bw) {
      let stuck = 0;
      for (let i = logs.length - 1; i >= 0; i--) {
        if (logs[i].reps === reps) stuck++; else break;
      }
      if (stuck >= 2) return { type: 'up', weight: 0, sets: sets, reps: reps + 1, tag: 'Add a rep', reason: 'You hit ' + reps + ' reps for ' + stuck + ' sessions in a row — push for ' + (reps + 1) + ' next time.', bw: true };
      return { type: 'hold', weight: 0, sets: sets, reps: reps, tag: 'Repeat', reason: 'Repeat ' + sets + ' × ' + reps + ' next session.', bw: true };
    }
    let stuck = 0;
    for (let i = logs.length - 1; i >= 0; i--) {
      if (logs[i].weight === weight) stuck++; else break;
    }
    const step = unit() === 'lb' ? (CONFIG.upgradeStepLb || 5) : (CONFIG.upgradeStepKg || 2.5);
    if (stuck >= 2) {
      const nextWeight = weight + step;
      return { type: 'up', weight: nextWeight, sets: sets, reps: reps, tag: 'Add weight', reason: 'You held ' + weight + unit() + ' for ' + stuck + ' sessions — try ' + nextWeight + unit() + ' next time.' };
    }
    return { type: 'hold', weight: weight, sets: sets, reps: reps, tag: 'Repeat', reason: 'Repeat ' + sets + ' × ' + reps + ' @ ' + weight + unit() + ' next session.' };
  }
```

- [ ] **Step 2: Rewrite `renderRx()` for the new prescription shape and the "no logs yet" state**

In `gym.html`, find this exact block:

```javascript
  function renderRx() {
    const wrap = $('rxWrap');
    const ex = getCurrentEx();
    if (!ex) { wrap.innerHTML = '<div class="po-rx-empty">Pick a gym and day above.</div>'; return; }
    const logs = getLogs();
    const rx = getRx(ex, logs);
    if (!rx) {
      const sw = ex.startWeight, sr = ex.repMin;
      const head = ex.bw
        ? '<span class="po-accent">' + sr + '</span> reps'
        : '<span class="po-accent">' + (sw || 0) + unit() + '</span> × ' + sr + ' reps';
      const reason = ex.bw
        ? 'Aim for ' + ex.repMin + '-' + ex.repMax + ' clean reps. Once you hit ' + ex.repMax + '+, push for more.'
        : 'Hit ' + ex.repMin + '-' + ex.repMax + ' reps. Once logged, the coach will start prescribing.';
      wrap.innerHTML = '<div class="po-rx-card"><div class="po-rx-label">' + escape(ex.name) + ' · starting point</div><div class="po-rx-headline">' + head + '</div><span class="po-rx-tag hold">Start here</span><p class="po-rx-reason">' + reason + '</p></div>';
      return;
    }
    const head = rx.bw
      ? '<span class="po-accent">' + rx.reps + '</span> reps'
      : '<span class="po-accent">' + rx.weight + unit() + '</span> × ' + rx.reps + ' reps';
    wrap.innerHTML = '<div class="po-rx-card po-rx-' + rx.type + '"><div class="po-rx-label">' + escape(ex.name) + '</div><div class="po-rx-headline">' + head + '</div><span class="po-rx-tag ' + rx.type + '">' + rx.tag + '</span><p class="po-rx-reason">' + rx.reason + '</p></div>';
  }
```

Replace it with:

```javascript
  function renderRx() {
    const wrap = $('rxWrap');
    const ex = getCurrentEx();
    if (!ex) { wrap.innerHTML = '<div class="po-rx-empty">Pick a day type above.</div>'; return; }
    const logs = getLogs();
    const rx = getRx(ex, logs);
    if (!rx) {
      wrap.innerHTML = '<div class="po-rx-card"><div class="po-rx-label">' + escape(ex.name) + ' · new exercise</div><div class="po-rx-headline">No sessions yet</div><span class="po-rx-tag hold">Start here</span><p class="po-rx-reason">Log your first session below to start tracking.</p></div>';
      return;
    }
    const head = rx.bw
      ? '<span class="po-accent">' + rx.sets + '</span> × ' + rx.reps + ' reps'
      : '<span class="po-accent">' + rx.weight + unit() + '</span> × ' + rx.sets + ' × ' + rx.reps;
    wrap.innerHTML = '<div class="po-rx-card po-rx-' + rx.type + '"><div class="po-rx-label">' + escape(ex.name) + '</div><div class="po-rx-headline">' + head + '</div><span class="po-rx-tag ' + rx.type + '">' + rx.tag + '</span><p class="po-rx-reason">' + rx.reason + '</p></div>';
  }
```

- [ ] **Step 3: Update `renderLastSet()` to show sets**

In `gym.html`, find this exact block:

```javascript
  function renderLastSet() {
    const wrap = $('lastSet');
    const v = $('lastSetValue');
    const m = $('lastSetMeta');
    const ex = getCurrentEx();
    const logs = ex ? getLogs() : [];
    if (!ex || !logs.length) { wrap.classList.remove('show'); return; }
    const last = logs[logs.length - 1];
    const setStr = ex.bw ? (last.reps + ' reps') : (last.weight + unit() + ' × ' + last.reps);
    const d = new Date(last.date);
    const da = Math.floor((Date.now() - d.getTime()) / 86400000);
    const ago = da === 0 ? 'today' : da === 1 ? 'yesterday' : da + ' days ago';
    v.textContent = setStr;
    m.textContent = ago;
    wrap.classList.add('show');
  }
```

Replace it with:

```javascript
  function renderLastSet() {
    const wrap = $('lastSet');
    const v = $('lastSetValue');
    const m = $('lastSetMeta');
    const ex = getCurrentEx();
    const logs = ex ? getLogs() : [];
    if (!ex || !logs.length) { wrap.classList.remove('show'); return; }
    const last = logs[logs.length - 1];
    const setStr = ex.bw ? (last.sets + ' × ' + last.reps + ' reps') : (last.sets + ' × ' + last.reps + ' @ ' + last.weight + unit());
    const d = new Date(last.date);
    const da = Math.floor((Date.now() - d.getTime()) / 86400000);
    const ago = da === 0 ? 'today' : da === 1 ? 'yesterday' : da + ' days ago';
    v.textContent = setStr;
    m.textContent = ago;
    wrap.classList.add('show');
  }
```

- [ ] **Step 4: Update `renderHistory()` to show sets per session**

In `gym.html`, find this exact block:

```javascript
  function renderHistory() {
    const wrap = $('historyCard');
    const ex = getCurrentEx();
    const logs = ex ? getLogs().slice().reverse() : [];
    if (!logs.length) {
      wrap.innerHTML = '<div class="po-empty">No logs yet.</div>';
      return;
    }
    wrap.innerHTML = logs.slice(0, 12).map((l, i) => {
      const d = new Date(l.date);
      const dStr = (d.getMonth() + 1) + '/' + d.getDate();
      const setStr = ex.bw ? (l.reps + ' reps') : (l.weight + unit() + ' × ' + l.reps);
      const realIdx = logs.length - 1 - i; // since we reversed
      return '<div class="po-hist-row">'
        + '<div class="po-hist-date">' + dStr + '</div>'
        + '<div class="po-hist-set">' + setStr + '</div>'
        + '<button class="po-hist-del" data-idx="' + realIdx + '" aria-label="Delete">×</button>'
        + '</div>';
    }).join('');
    wrap.querySelectorAll('.po-hist-del').forEach(b => {
      b.addEventListener('click', () => {
        if (!confirm('Delete this log?')) return;
        const realIdx = parseInt(b.dataset.idx, 10);
        const arr = state.logs[state.currentEx] || [];
        // realIdx is index in REVERSED list; map back to original
        const origIdx = arr.length - 1 - realIdx;
        arr.splice(origIdx, 1);
        if (!arr.length) delete state.logs[state.currentEx];
        else state.logs[state.currentEx] = arr;
        saveState(); renderAll();
      });
    });
  }
```

Replace it with:

```javascript
  function renderHistory() {
    const wrap = $('historyCard');
    const ex = getCurrentEx();
    const logs = ex ? getLogs().slice().reverse() : [];
    if (!logs.length) {
      wrap.innerHTML = '<div class="po-empty">No logs yet.</div>';
      return;
    }
    wrap.innerHTML = logs.slice(0, 12).map((l, i) => {
      const d = new Date(l.date);
      const dStr = (d.getMonth() + 1) + '/' + d.getDate();
      const setStr = ex.bw ? (l.sets + ' × ' + l.reps + ' reps') : (l.sets + ' × ' + l.reps + ' @ ' + l.weight + unit());
      const realIdx = logs.length - 1 - i; // since we reversed
      return '<div class="po-hist-row">'
        + '<div class="po-hist-date">' + dStr + '</div>'
        + '<div class="po-hist-set">' + setStr + '</div>'
        + '<button class="po-hist-del" data-idx="' + realIdx + '" aria-label="Delete">×</button>'
        + '</div>';
    }).join('');
    wrap.querySelectorAll('.po-hist-del').forEach(b => {
      b.addEventListener('click', () => {
        if (!confirm('Delete this log?')) return;
        const realIdx = parseInt(b.dataset.idx, 10);
        const arr = state.logs[state.currentEx] || [];
        // realIdx is index in REVERSED list; map back to original
        const origIdx = arr.length - 1 - realIdx;
        arr.splice(origIdx, 1);
        if (!arr.length) delete state.logs[state.currentEx];
        else state.logs[state.currentEx] = arr;
        saveState(); renderAll();
      });
    });
  }
```

- [ ] **Step 5: Verify the file is well-formed**

Run:
```bash
node -e "
var fs = require('fs');
var s = fs.readFileSync('gym.html', 'utf8');
var re = /<script>([\s\S]*?)<\/script>/g;
var m, count = 0;
while ((m = re.exec(s))) { new Function(m[1]); count++; }
console.log('checked', count, 'inline script blocks OK');
"
```
Expected: prints a count with no syntax errors thrown.

Also run:
```bash
grep -c 'ex\.repMin\|ex\.repMax\|ex\.step\b\|ex\.startWeight\|CONFIG\.upgradeAtReps' gym.html
```
Expected: `0` (no remaining reference to the removed per-exercise fields or the removed global rep-threshold config)

- [ ] **Step 6: Manually verify in a browser**

Serve the directory and use Playwright MCP tools (or the curl/code-trace fallback from Task 2 Step 10 if Chromium is unavailable, reporting `DONE_WITH_CONCERNS`) to confirm:
- With no logs yet for an exercise, "Next session" shows "No sessions yet" / "Start here."
- Log a session (e.g. 3 sets × 8 reps @ 100kg), confirm "Last time" shows "3 × 8 @ 100kg," History shows the same, and 1RM/best-set/sparkline populate (unchanged math, now fed by session data — this is the concrete check that those genuinely-unmodified functions still work correctly against the new log shape).
- Log a second session at the same weight, confirm "Next session" now suggests adding the configured step (2.5kg default) next time.
- Log a session with a different weight, confirm "Next session" suggests repeating instead.
- For a bodyweight exercise, confirm the equivalent same-rep-count-twice-in-a-row → "Add a rep" behavior.

- [ ] **Step 7: Commit**

```bash
git add gym.html
git commit -m "$(cat <<'EOF'
Adapt Fitness prescriptions and history to session-shaped logs

Phase 4 of the simplified-logging rework: getRx() now suggests
progression based on repeating the same weight/reps for 2+ sessions
in a row (using one fixed global weight step) instead of the removed
per-exercise rep-range/step configuration. "Last time" and History
now show sets × reps @ weight per session. 1RM, best-set, and the
sparkline needed no changes — they already read weight/reps generically.
EOF
)"
```

---

### Task 5: Remove "Manage Gyms" from Settings

**Files:**
- Modify: `gym.html` (HTML: Settings modal; JS: `renderSettings()`, `setAddGym` handler)

**Interfaces:**
- Consumes: nothing beyond what already exists (independent cleanup task)
- Produces: nothing consumed elsewhere (final task in this plan)

This task is independent of Tasks 2-4 — it only touches the Settings modal's now-orphaned gym-management UI, which has had no live data behind it since Task 1 removed `state.gyms`. It can be applied at any point after Task 1.

- [ ] **Step 1: Remove the "Gyms" section from the Settings modal HTML**

In `gym.html`, find this exact block:

```html
    <div class="po-set-section">
      <h4>Gyms</h4>
      <div class="po-set-list" id="setGyms"></div>
      <button class="po-add-row-btn" id="setAddGym">+ Add gym</button>
    </div>

    <div class="po-set-section">
      <h4>Days</h4>
```

Replace it with:

```html
    <div class="po-set-section">
      <h4>Days</h4>
```

- [ ] **Step 2: Remove gym handling from `renderSettings()`**

In `gym.html`, find this exact block:

```javascript
  function renderSettings() {
    $('setUnitsSeg').querySelectorAll('button').forEach(b => {
      b.classList.toggle('active', b.dataset.u === state.units);
    });
    $('setGyms').innerHTML = state.gyms.map((g, i) =>
      '<div class="po-set-row" data-i="' + i + '">'
      + '<input type="text" value="' + escape(g.name) + '" data-field="name" placeholder="Gym name">'
      + '<button class="po-mini-btn" data-action="del" aria-label="Delete">×</button>'
      + '</div>'
    ).join('');
    $('setDays').innerHTML = state.days.map((d, i) =>
      '<div class="po-set-row" data-i="' + i + '">'
      + '<input type="text" value="' + escape(d.name) + '" data-field="name" placeholder="Day name">'
      + '<button class="po-mini-btn" data-action="del" aria-label="Delete">×</button>'
      + '</div>'
    ).join('');
    $('setGyms').querySelectorAll('.po-set-row').forEach(row => {
      const i = parseInt(row.dataset.i, 10);
      row.querySelector('input').addEventListener('input', e => {
        state.gyms[i].name = e.target.value;
        saveState();
      });
      row.querySelector('[data-action="del"]').addEventListener('click', () => {
        if (state.gyms.length <= 1) { alert('You need at least one gym.'); return; }
        if (!confirm('Remove "' + state.gyms[i].name + '"? Exercises tagged to this gym will become invisible until you reassign them.')) return;
        state.gyms.splice(i, 1);
        if (!state.gyms.find(g => g.id === state.filterGym)) state.filterGym = state.gyms[0].id;
        saveState(); renderSettings(); renderAll();
      });
    });
    $('setDays').querySelectorAll('.po-set-row').forEach(row => {
```

Replace it with:

```javascript
  function renderSettings() {
    $('setUnitsSeg').querySelectorAll('button').forEach(b => {
      b.classList.toggle('active', b.dataset.u === state.units);
    });
    $('setDays').innerHTML = state.days.map((d, i) =>
      '<div class="po-set-row" data-i="' + i + '">'
      + '<input type="text" value="' + escape(d.name) + '" data-field="name" placeholder="Day name">'
      + '<button class="po-mini-btn" data-action="del" aria-label="Delete">×</button>'
      + '</div>'
    ).join('');
    $('setDays').querySelectorAll('.po-set-row').forEach(row => {
```

- [ ] **Step 3: Remove the `setAddGym` click handler**

In `gym.html`, find this exact block:

```javascript
  $('setAddGym').addEventListener('click', () => {
    const name = (prompt('New gym name:') || '').trim();
    if (!name) return;
    const id = 'g_' + Date.now();
    state.gyms.push({ id, name });
    saveState(); renderSettings(); renderAll();
  });
  $('setAddDay').addEventListener('click', () => {
```

Replace it with:

```javascript
  $('setAddDay').addEventListener('click', () => {
```

- [ ] **Step 4: Verify the file is well-formed**

Run:
```bash
node -e "
var fs = require('fs');
var s = fs.readFileSync('gym.html', 'utf8');
var re = /<script>([\s\S]*?)<\/script>/g;
var m, count = 0;
while ((m = re.exec(s))) { new Function(m[1]); count++; }
console.log('checked', count, 'inline script blocks OK');
"
```
Expected: prints a count with no syntax errors thrown.

Also run:
```bash
grep -c 'setGyms\|setAddGym' gym.html
```
Expected: `0`

- [ ] **Step 5: Manually verify in a browser**

Serve the directory and use Playwright MCP tools (or the curl/code-trace fallback from Task 2 Step 10 if Chromium is unavailable, reporting `DONE_WITH_CONCERNS`) to confirm: opening Settings shows a "Days" section (rename/add/delete day types) with no "Gyms" section above it, and the Days section still works exactly as before (rename a day type, confirm it updates the day-type filter/exercise-modal picker).

- [ ] **Step 6: Commit**

```bash
git add gym.html
git commit -m "$(cat <<'EOF'
Remove orphaned "Manage Gyms" section from Fitness Settings

Phase 5 (final) of the simplified-logging rework: cleans up the
Settings modal now that the gym dimension has been fully removed from
the page (data model in phase 1, UI in phases 2-3). Completes the
Fitness simplified-logging rework.
EOF
)"
```
