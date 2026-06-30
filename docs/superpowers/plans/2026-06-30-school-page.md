# School Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `school.html`, a new dashboard page tracking semesters, classes (with grades), and a unified assignments/exams list with due-date countdowns.

**Architecture:** A single static HTML file following this codebase's established page template (`template.html`): the shared dark glass-card design system in an inline `<style>` block, a single root localStorage key (`school_v1`) holding all data, vanilla JS with no build step, and `window.initCloudSync` for cross-device sync. The file is built up incrementally across 4 tasks — shell + semester switcher, then Classes, then Upcoming, then Overview — each task is a complete, independently-verifiable slice of the page.

**Tech Stack:** Plain HTML, CSS, vanilla JS (ES5-style, matching the rest of the codebase — `var`, no arrow functions, no template literals beyond what's already used elsewhere). No npm test runner exists in this repo.

## Global Constraints

- One root localStorage key for all page state: `school_v1`. Do not introduce additional top-level keys for this page.
- Cloud sync: `appKey: 'school'` via `window.initCloudSync` (confirmed unused — existing appKeys are `caffeine`, `finance`, `health`, `goals`, `template`).
- Visual style must match the existing design system exactly: reuse `--text-primary`/`--text-secondary`/`--text-tertiary`/`--success`/`--warning`/`--danger` custom properties, `.dash-title`, `.section-title`, `.gm-card`, `.gm-row`, `.gm-input`, `.gm-add`, `.gm-ghost`, `.stat-grid` classes verbatim from `template.html`.
- No GPA/credit-hour weighting — grades are plain percentages (0–100), average is a simple mean.
- Classes carry no in-page visual timetable — `days`/`startTime`/`endTime`/`room` are stored as plain data only (Phase 3 will turn this into calendar events; this page does not build that view).
- Assignments and exams share one list and one countdown/date-diff engine — no separate code paths beyond the type-specific checkbox-vs-countdown-chip rendering.
- "Today" for countdown/due-date comparisons is the user's local calendar date via plain `new Date()` — no special cutoff hour (unlike Health's 6 AM daily-reset for habit logs).
- Lightweight error handling only: required-field checks block submission of empty class names / task titles / missing due dates; no confirmation dialogs on delete.
- Deleting a class that a task references must not crash the page — the task's class-name display must fall back gracefully (handled by looking the class up at render time, not by mutating tasks on delete).

---

### Task 1: Page shell, data model, and semester switcher

**Files:**
- Create: `school.html`

**Interfaces:**
- Consumes: nothing (first task)
- Produces (for Tasks 2-4 to use verbatim):
  - `STORE_KEY` = `'school_v1'`
  - `load()` → `{ activeSemesterId: string|null, semesters: Array<{id, name, classes: [], tasks: []}> }`
  - `save(state)` → writes state to localStorage under `STORE_KEY`
  - `uid(prefix)` → returns a unique string id like `"sem_abc12xy"`
  - `activeSemester(state)` → returns the semester object matching `state.activeSemesterId`, or `null`
  - `render()` → top-level re-render function; Tasks 2-4 each add one line to its body
  - HTML structure ends with `</div><!-- /.page -->` right after the `.school-header-row` div — later tasks insert new `<div class="section">` blocks before this closing tag

- [ ] **Step 1: Create `school.html` with the full page shell**

Create `/Users/odenransom/Oden-Dashboard/school.html` with this exact content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<script src="lock.js"></script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#050506">
<title>School · Dashboard</title>

<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script src="sync.js" defer></script>
<script src="topbar.js" defer></script>

<style>
:root {
  --text-primary: #FAFAFA;
  --text-secondary: #B8B6B0;
  --text-tertiary: #76746E;
  --success: #6BE3A4;
  --warning: #F2C063;
  --danger:  #FF6B6B;
  --font: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0;
  background: #050506;
  color: var(--text-secondary);
  font-family: var(--font);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  -webkit-text-size-adjust: 100%;
}
body {
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
  padding: max(28px, env(safe-area-inset-top)) 20px 60px;
}
body::before {
  content: '';
  position: fixed; inset: 0;
  background:
    radial-gradient(circle at 82% 14%, rgba(224, 118, 88, 0.16), transparent 45%),
    radial-gradient(circle at 18% 90%, rgba(180, 180, 200, 0.06), transparent 50%);
  filter: blur(40px);
  pointer-events: none;
  z-index: -2;
  animation: drift 36s ease-in-out infinite alternate;
}
body::after {
  content: '';
  position: fixed; inset: 0;
  background-image: radial-gradient(rgba(255,255,255,0.014) 1px, transparent 1px);
  background-size: 3px 3px;
  pointer-events: none;
  z-index: -1;
}
@keyframes drift {
  0%   { transform: translate3d(0,0,0); }
  100% { transform: translate3d(-22px, 14px, 0); }
}

.page { max-width: 1100px; margin: 0 auto; }

.dash-title {
  margin: 0 0 14px;
  font-size: 28px; font-weight: 700;
  letter-spacing: -0.025em;
  background: linear-gradient(180deg, #FFFFFF 0%, #C7C4BC 120%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
}
@media (max-width: 480px) { .dash-title { font-size: 22px; } }

.section { margin-top: 8px; }
.section-title {
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--text-tertiary);
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 12px;
}
.section-title::before {
  content: ''; width: 18px; height: 1px;
  background: var(--text-tertiary); opacity: 0.6;
}
.section-title::after {
  content: ''; flex: 1; height: 1px;
  background: linear-gradient(90deg, rgba(255,255,255,0.08), transparent);
}

.gm-card {
  position: relative;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 14px;
  backdrop-filter: blur(24px) saturate(1.2);
  -webkit-backdrop-filter: blur(24px) saturate(1.2);
  box-shadow: 0 12px 40px rgba(0,0,0,0.45);
  overflow: hidden;
}
.gm-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  flex-wrap: wrap; gap: 12px; margin-bottom: 14px;
}
.gm-header-left { display: flex; flex-direction: column; }
.gm-eyebrow {
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--text-tertiary); margin-bottom: 6px;
}
.gm-progress-row { display: flex; align-items: baseline; gap: 6px; }
.gm-progress-num {
  font-size: 42px; font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.045em; color: var(--text-primary); line-height: 1;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}
.stat {
  background: rgba(255,255,255,0.035);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px; padding: 14px;
}
.stat-num {
  font-size: 26px; font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em; color: var(--text-primary); line-height: 1;
}
.stat-label {
  margin-top: 6px;
  font-size: 10.5px; font-weight: 600;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--text-tertiary);
}

.empty-state {
  text-align: center; font-size: 12px; font-style: italic;
  color: var(--text-tertiary); padding: 14px 0;
}
.gm-row {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; margin-bottom: 6px;
  background: rgba(255,255,255,0.035);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  transition: background 0.2s, opacity 0.3s;
}
.gm-row:hover { background: rgba(255,255,255,0.06); }
.gm-row.gm-row-done { opacity: 0.45; background: rgba(107,227,164,0.04); }
.gm-row.gm-row-done .task-title { text-decoration: line-through; text-decoration-color: rgba(255,255,255,0.4); }
.gm-check {
  appearance: none; -webkit-appearance: none;
  width: 22px; height: 22px; flex-shrink: 0; margin: 0;
  border: 1.5px solid rgba(255,255,255,0.18);
  background: rgba(0,0,0,0.28); border-radius: 7px;
  position: relative; cursor: pointer;
  transition: background 0.2s, border-color 0.2s, box-shadow 0.25s;
}
.gm-check:checked {
  background: var(--success); border-color: var(--success);
  box-shadow: 0 0 12px rgba(107,227,164,0.40);
}
.gm-check:checked::after {
  content: ''; position: absolute; left: 6px; top: 2px;
  width: 6px; height: 11px;
  border: solid #0A0A0B; border-width: 0 2.5px 2.5px 0;
  transform: rotate(45deg);
}
.goal-delete {
  border: 0; background: transparent; color: var(--text-tertiary);
  font-size: 18px; cursor: pointer; padding: 0 4px;
  opacity: 0.5; transition: opacity 0.2s, color 0.2s;
}
.gm-row:hover .goal-delete { opacity: 1; }
.goal-delete:hover { color: var(--danger); }

.gm-input-wrap {
  display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
  margin-top: 14px; padding-top: 14px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.gm-input {
  flex: 1; min-width: 120px;
  padding: 11px 14px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px; background: rgba(0,0,0,0.28);
  color: var(--text-primary);
  font-family: inherit; font-size: 14px; outline: none;
  transition: border-color 0.2s, background 0.2s;
}
.gm-input::placeholder { color: var(--text-tertiary); }
.gm-input:focus { border-color: rgba(255,255,255,0.28); background: rgba(0,0,0,0.36); }

.gm-add {
  padding: 11px 20px; border: 0; border-radius: 12px;
  background: linear-gradient(180deg, #FFFFFF 0%, #E8E5DD 100%);
  color: #0A0A0B; font-family: inherit; font-size: 13px; font-weight: 700;
  cursor: pointer;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.9),
    0 2px 8px rgba(0,0,0,0.35),
    0 8px 22px rgba(0,0,0,0.25);
  transition: transform 0.1s, filter 0.15s;
}
.gm-add:hover { filter: brightness(1.06); transform: translateY(-1px); }
.gm-add:active { transform: translateY(0); }

.gm-ghost {
  padding: 11px 18px;
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 12px; background: rgba(255,255,255,0.04);
  color: var(--text-primary);
  font-family: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.gm-ghost:hover { background: rgba(255,255,255,0.07); border-color: rgba(255,255,255,0.18); }

.school-header-row {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  margin-bottom: 20px;
}
.sem-select {
  padding: 10px 14px; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px; background: rgba(0,0,0,0.28);
  color: var(--text-primary); font-family: inherit; font-size: 13px;
  outline: none; cursor: pointer;
}
.sem-add-input {
  width: 140px; padding: 10px 14px;
  border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
  background: rgba(0,0,0,0.28); color: var(--text-primary);
  font-family: inherit; font-size: 13px; outline: none;
}
.sem-add-input::placeholder { color: var(--text-tertiary); }

@media (max-width: 480px) {
  body { padding: max(20px, env(safe-area-inset-top)) 14px 50px; }
  .gm-card { padding: 16px; }
  .gm-progress-num { font-size: 36px; }
}
</style>
</head>
<body>
<div class="page">

  <h1 class="dash-title">School</h1>

  <div class="school-header-row">
    <select class="sem-select" id="semSelect"></select>
    <input class="sem-add-input" id="semAddInput" type="text" placeholder="New semester…" autocomplete="off">
    <button class="gm-ghost" id="semAddBtn" type="button">+ Add semester</button>
  </div>

</div><!-- /.page -->

<script>
(function () {
  'use strict';

  var STORE_KEY = 'school_v1';

  function load() {
    try {
      var v = JSON.parse(localStorage.getItem(STORE_KEY));
      if (v && Array.isArray(v.semesters)) return v;
    } catch (e) {}
    return { activeSemesterId: null, semesters: [] };
  }
  function save(state) { localStorage.setItem(STORE_KEY, JSON.stringify(state)); }
  function uid(prefix) { return prefix + '_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
  function activeSemester(state) {
    return state.semesters.filter(function (s) { return s.id === state.activeSemesterId; })[0] || null;
  }

  function renderSemesterSelect() {
    var state = load();
    var sel = document.getElementById('semSelect');
    sel.innerHTML = '';
    if (state.semesters.length === 0) {
      var opt = document.createElement('option');
      opt.textContent = 'No semesters yet';
      opt.value = '';
      sel.appendChild(opt);
      sel.disabled = true;
      return;
    }
    sel.disabled = false;
    state.semesters.forEach(function (s) {
      var opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = s.name;
      if (s.id === state.activeSemesterId) opt.selected = true;
      sel.appendChild(opt);
    });
  }

  function render() {
    renderSemesterSelect();
  }

  document.getElementById('semSelect').addEventListener('change', function (e) {
    var state = load();
    state.activeSemesterId = e.target.value;
    save(state);
    render();
  });

  document.getElementById('semAddBtn').addEventListener('click', function () {
    var input = document.getElementById('semAddInput');
    var name = input.value.trim();
    if (!name) return;
    var state = load();
    var sem = { id: uid('sem'), name: name, classes: [], tasks: [] };
    state.semesters.push(sem);
    state.activeSemesterId = sem.id;
    save(state);
    input.value = '';
    render();
  });
  document.getElementById('semAddInput').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') document.getElementById('semAddBtn').click();
  });

  render();

  if (window.initCloudSync) {
    window.initCloudSync({
      appKey: 'school',
      syncedKeys: [STORE_KEY],
      onApplied: render
    });
  }
})();
</script>
</body>
</html>
```

- [ ] **Step 2: Verify the file is well-formed HTML**

Run: `python3 -c "import re; s=open('school.html').read(); print('script tags:', s.count('<script')); print('matched:', s.count('<script') == s.count('</script>'))"`
Expected: `matched: True`

- [ ] **Step 3: Manually verify in a browser**

Run: `python3 -m http.server 8123` from the repo root (background it or use a separate terminal), then use the Playwright MCP tools (`mcp__plugin_playwright_playwright__browser_navigate` to `http://localhost:8123/school.html`, `browser_snapshot` to inspect, `browser_type`/`browser_click`/`browser_select_option` to interact, `browser_evaluate` to read `localStorage.getItem('school_v1')`) to confirm:
- The page loads with title "School" and a (disabled, "No semesters yet") semester dropdown
- Typing a name into the "New semester…" input and clicking "+ Add semester" creates a semester, the dropdown now shows it selected and enabled
- Reloading the page (`browser_navigate` to the same URL again) preserves the semester (confirms localStorage persistence)
- Adding a second semester and switching the dropdown between the two updates `activeSemesterId` correctly (verify via `browser_evaluate` reading `JSON.parse(localStorage.getItem('school_v1')).activeSemesterId`)

**If Playwright's browser binary is unavailable in this environment** (a known issue here — Chromium not installed at the expected path), fall back to: `curl`-fetching the served HTML to confirm structural correctness (the `<select id="semSelect">`, input, and button elements are present with correct ids), and manually trace through the `semAddBtn` click handler and `render()` logic by reading the code to confirm correctness. Report this fallback clearly in your report and use status `DONE_WITH_CONCERNS` noting interactive behavior could not be directly observed.

- [ ] **Step 4: Commit**

```bash
git add school.html
git commit -m "$(cat <<'EOF'
Add School page shell with semester switcher

Phase 2 of the dashboard redesign: data model (school_v1), semester
add/switch, cloud sync wiring. Classes/Upcoming/Overview sections
follow in subsequent tasks.
EOF
)"
```

---

### Task 2: Classes section

**Files:**
- Modify: `school.html` (HTML: insert a new `<div class="section">` for Classes right before `</div><!-- /.page -->`; CSS: add class-card and day-toggle rules; JS: add render/event logic for Classes)

**Interfaces:**
- Consumes from Task 1: `STORE_KEY`, `load()`, `save(state)`, `uid(prefix)`, `activeSemester(state)`, the existing `render()` function (this task adds one line to its body)
- Produces (for Tasks 3-4 to use verbatim):
  - `escapeHtml(s)` → HTML-escapes a string for safe innerHTML interpolation
  - Each semester's `classes` array holds objects shaped `{ id, name, instructor, days: string[], startTime, endTime, room, grade: number|null }`
  - `renderClasses()` → re-renders the `#classesList` container from the active semester's `classes`

- [ ] **Step 1: Add Classes-specific CSS**

In `school.html`, find this block (the end of the `<style>` section, just before the closing `</style>`):

```css
.sem-add-input::placeholder { color: var(--text-tertiary); }

@media (max-width: 480px) {
  body { padding: max(20px, env(safe-area-inset-top)) 14px 50px; }
  .gm-card { padding: 16px; }
  .gm-progress-num { font-size: 36px; }
}
</style>
```

Replace it with:

```css
.sem-add-input::placeholder { color: var(--text-tertiary); }

.class-card {
  background: rgba(255,255,255,0.035);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px; padding: 14px; margin-bottom: 10px;
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
}
.class-card-info { min-width: 0; }
.class-name { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.class-meta { font-size: 12px; color: var(--text-tertiary); margin-top: 4px; }
.class-card-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.class-grade-input {
  width: 64px; padding: 8px 10px; text-align: center;
  border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
  background: rgba(0,0,0,0.28); color: var(--text-primary);
  font-family: inherit; font-size: 14px; outline: none;
}
.class-grade-input::placeholder { color: var(--text-tertiary); }

.day-toggle-row { display: flex; gap: 6px; flex-wrap: wrap; }
.day-toggle {
  padding: 8px 10px; border: 1px solid rgba(255,255,255,0.10);
  border-radius: 9px; background: rgba(255,255,255,0.04);
  color: var(--text-tertiary); font-family: inherit;
  font-size: 12px; font-weight: 600; cursor: pointer;
}
.day-toggle.on { background: rgba(255,255,255,0.12); color: var(--text-primary); border-color: rgba(255,255,255,0.22); }

@media (max-width: 480px) {
  body { padding: max(20px, env(safe-area-inset-top)) 14px 50px; }
  .gm-card { padding: 16px; }
  .gm-progress-num { font-size: 36px; }
  .class-card { flex-direction: column; }
}
</style>
```

- [ ] **Step 2: Add the Classes section HTML**

In `school.html`, find:

```html
  </div>

</div><!-- /.page -->
```

(this is the end of the `.school-header-row` div, immediately followed by the closing `.page` div). Replace it with:

```html
  </div>

  <div class="section">
    <div class="section-title">Classes</div>
    <div class="gm-card">
      <div id="classesList"></div>

      <div class="gm-input-wrap">
        <input class="gm-input" id="classNameInput" type="text" placeholder="Class name…" autocomplete="off" style="min-width:160px">
        <input class="gm-input" id="classInstructorInput" type="text" placeholder="Instructor (optional)" autocomplete="off" style="max-width:160px">
        <div class="day-toggle-row" id="classDayToggleRow">
          <button type="button" class="day-toggle" data-day="Mon">Mon</button>
          <button type="button" class="day-toggle" data-day="Tue">Tue</button>
          <button type="button" class="day-toggle" data-day="Wed">Wed</button>
          <button type="button" class="day-toggle" data-day="Thu">Thu</button>
          <button type="button" class="day-toggle" data-day="Fri">Fri</button>
          <button type="button" class="day-toggle" data-day="Sat">Sat</button>
          <button type="button" class="day-toggle" data-day="Sun">Sun</button>
        </div>
        <input class="gm-input" id="classStartInput" type="time" style="max-width:110px">
        <input class="gm-input" id="classEndInput" type="time" style="max-width:110px">
        <input class="gm-input" id="classRoomInput" type="text" placeholder="Room (optional)" autocomplete="off" style="max-width:140px">
        <button class="gm-add" id="classAddBtn" type="button">+ Add class</button>
      </div>
    </div>
  </div>

</div><!-- /.page -->
```

- [ ] **Step 3: Add Classes JS logic**

In `school.html`, find:

```js
  function render() {
    renderSemesterSelect();
  }
```

Replace it with:

```js
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
    });
  }

  function formatTime12(t) {
    if (!t) return '';
    var parts = t.split(':');
    var h = parseInt(parts[0], 10);
    var m = parts[1];
    var ap = h >= 12 ? 'PM' : 'AM';
    var h12 = h % 12; if (h12 === 0) h12 = 12;
    return h12 + ':' + m + ' ' + ap;
  }

  function classMetaLine(cls) {
    var bits = [];
    if (cls.instructor) bits.push(cls.instructor);
    if (cls.days && cls.days.length) bits.push(cls.days.join('/'));
    if (cls.startTime && cls.endTime) bits.push(formatTime12(cls.startTime) + '–' + formatTime12(cls.endTime));
    if (cls.room) bits.push(cls.room);
    return bits.join(' · ');
  }

  function renderClassCardHtml(cls) {
    var meta = classMetaLine(cls);
    return '' +
      '<div class="class-card" data-id="' + cls.id + '">' +
        '<div class="class-card-info">' +
          '<div class="class-name">' + escapeHtml(cls.name) + '</div>' +
          (meta ? '<div class="class-meta">' + escapeHtml(meta) + '</div>' : '') +
        '</div>' +
        '<div class="class-card-right">' +
          '<input class="class-grade-input" type="number" min="0" max="100" step="1" placeholder="—" value="' + (cls.grade == null ? '' : cls.grade) + '" data-grade-id="' + cls.id + '">' +
          '<button type="button" class="goal-delete" data-delete-id="' + cls.id + '">×</button>' +
        '</div>' +
      '</div>';
  }

  function renderClasses() {
    var state = load();
    var sem = activeSemester(state);
    var list = document.getElementById('classesList');
    if (!sem) { list.innerHTML = '<div class="empty-state">Add a semester to get started.</div>'; return; }
    if (sem.classes.length === 0) { list.innerHTML = '<div class="empty-state">No classes yet — add one below.</div>'; return; }
    list.innerHTML = sem.classes.map(renderClassCardHtml).join('');
  }

  document.getElementById('classesList').addEventListener('click', function (e) {
    var btn = e.target.closest('[data-delete-id]');
    if (!btn) return;
    var state = load();
    var sem = activeSemester(state);
    if (!sem) return;
    var id = btn.getAttribute('data-delete-id');
    sem.classes = sem.classes.filter(function (c) { return c.id !== id; });
    save(state);
    render();
  });
  document.getElementById('classesList').addEventListener('change', function (e) {
    var input = e.target.closest('[data-grade-id]');
    if (!input) return;
    var state = load();
    var sem = activeSemester(state);
    if (!sem) return;
    var cls = sem.classes.filter(function (c) { return c.id === input.getAttribute('data-grade-id'); })[0];
    if (!cls) return;
    var v = input.value === '' ? null : Math.max(0, Math.min(100, parseFloat(input.value)));
    cls.grade = (v == null || isNaN(v)) ? null : v;
    save(state);
    render();
  });

  var selectedDays = [];
  document.getElementById('classDayToggleRow').addEventListener('click', function (e) {
    var btn = e.target.closest('.day-toggle');
    if (!btn) return;
    var day = btn.getAttribute('data-day');
    var idx = selectedDays.indexOf(day);
    if (idx === -1) selectedDays.push(day); else selectedDays.splice(idx, 1);
    btn.classList.toggle('on');
  });

  function addClass() {
    var nameEl = document.getElementById('classNameInput');
    var name = nameEl.value.trim();
    if (!name) return;
    var state = load();
    var sem = activeSemester(state);
    if (!sem) return;
    sem.classes.push({
      id: uid('cls'),
      name: name,
      instructor: document.getElementById('classInstructorInput').value.trim(),
      days: selectedDays.slice(),
      startTime: document.getElementById('classStartInput').value,
      endTime: document.getElementById('classEndInput').value,
      room: document.getElementById('classRoomInput').value.trim(),
      grade: null
    });
    save(state);
    nameEl.value = '';
    document.getElementById('classInstructorInput').value = '';
    document.getElementById('classStartInput').value = '';
    document.getElementById('classEndInput').value = '';
    document.getElementById('classRoomInput').value = '';
    selectedDays.length = 0;
    var toggles = document.querySelectorAll('#classDayToggleRow .day-toggle');
    for (var i = 0; i < toggles.length; i++) toggles[i].classList.remove('on');
    render();
  }
  document.getElementById('classAddBtn').addEventListener('click', addClass);
  document.getElementById('classNameInput').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') addClass();
  });

  function render() {
    renderSemesterSelect();
    renderClasses();
  }
```

- [ ] **Step 4: Verify the file is well-formed**

Run: `node -e "new Function(require('fs').readFileSync('school.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1])" && echo "JS syntax OK"`
Expected: `JS syntax OK` (this parses the inline script as a function body, which throws a SyntaxError on malformed JS without executing browser-only calls like `document.getElementById`, since `new Function` only compiles, it doesn't run, the body until invoked — and we never invoke it).

- [ ] **Step 5: Manually verify in a browser**

Serve the directory (`python3 -m http.server 8123`) and use Playwright MCP tools (or the curl/code-trace fallback from Task 1 Step 3 if Chromium is unavailable) to confirm:
- With an active semester selected, filling in the class form (name required; try with and without optional fields) and clicking "+ Add class" adds a card showing the name and a correctly formatted meta line (e.g. "Dr. Lee · Mon/Wed/Fri · 9:00 AM–9:50 AM · Building 4, Rm 210")
- Typing a grade into a class's grade input and blurring/tabbing away (a `change` event) persists it — reload the page and confirm the grade value is still there
- Clicking a class's delete (×) button removes it immediately, and the removal persists after reload
- Day-toggle buttons visually toggle `.on` and reset after a successful add
- With no semester selected (or zero semesters), the Classes list shows the "Add a semester to get started." empty state and the add-class button does nothing when clicked

- [ ] **Step 6: Commit**

```bash
git add school.html
git commit -m "$(cat <<'EOF'
Add Classes section to School page

Phase 2 task 2: class cards with inline grade entry, add-class form
with day-of-week toggles, delete.
EOF
)"
```

---

### Task 3: Upcoming (assignments + exams) section

**Files:**
- Modify: `school.html` (HTML: insert a new `<div class="section">` for Upcoming right before `</div><!-- /.page -->`; CSS: add task badge/chip rules; JS: add render/event logic for Upcoming)

**Interfaces:**
- Consumes from Tasks 1-2: `STORE_KEY`, `load()`, `save(state)`, `uid(prefix)`, `activeSemester(state)`, `escapeHtml(s)`, the existing `render()` function (this task adds two lines to its body)
- Produces (for Task 4 to use verbatim):
  - `todayStr()` → returns today's local date as `"YYYY-MM-DD"`
  - Each semester's `tasks` array holds objects shaped `{ id, title, type: 'assignment'|'exam', classId: string|null, dueDate: 'YYYY-MM-DD', done: boolean }`
  - `renderUpcoming()` → re-renders the `#upcomingList` container, sorted by `dueDate` ascending

- [ ] **Step 1: Add Upcoming-specific CSS**

In `school.html`, find:

```css
.day-toggle.on { background: rgba(255,255,255,0.12); color: var(--text-primary); border-color: rgba(255,255,255,0.22); }

@media (max-width: 480px) {
```

Replace it with:

```css
.day-toggle.on { background: rgba(255,255,255,0.12); color: var(--text-primary); border-color: rgba(255,255,255,0.22); }

.task-badge {
  font-size: 9.5px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  padding: 4px 8px; border-radius: 999px; flex-shrink: 0;
}
.task-badge.assignment { background: rgba(125,211,252,0.12); color: #7DD3FC; }
.task-badge.exam { background: rgba(255,107,107,0.12); color: var(--danger); }
.task-body { flex: 1; min-width: 0; }
.task-title { font-size: 14px; color: var(--text-primary); }
.task-class { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
.task-chip {
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  padding: 5px 9px; border-radius: 8px; flex-shrink: 0;
  background: rgba(255,255,255,0.05); color: var(--text-tertiary);
}
.task-chip.overdue { background: rgba(255,107,107,0.12); color: var(--danger); }
.task-chip.today { background: rgba(242,192,99,0.12); color: var(--warning); }

@media (max-width: 480px) {
```

- [ ] **Step 2: Add the Upcoming section HTML**

In `school.html`, find (the end of the Classes section, immediately followed by the closing `.page` div):

```html
  </div>

</div><!-- /.page -->
```

Replace it with:

```html
  </div>

  <div class="section">
    <div class="section-title">Upcoming</div>
    <div class="gm-card">
      <div id="upcomingList"></div>

      <div class="gm-input-wrap">
        <input class="gm-input" id="taskTitleInput" type="text" placeholder="Title…" autocomplete="off" style="min-width:160px">
        <select class="gm-input" id="taskTypeSelect" style="max-width:130px">
          <option value="assignment">Assignment</option>
          <option value="exam">Exam</option>
        </select>
        <select class="gm-input" id="taskClassSelect" style="max-width:160px">
          <option value="">No class</option>
        </select>
        <input class="gm-input" id="taskDueInput" type="date" style="max-width:160px">
        <button class="gm-add" id="taskAddBtn" type="button">+ Add</button>
      </div>
    </div>
  </div>

</div><!-- /.page -->
```

(Note: this `find` block now matches the end of the Classes section added in Task 2, not the header row — Task 2 already moved the `</div>\n\n</div><!-- /.page -->` marker to the end of the file, so this step's `find` text is the Classes section's closing tags.)

- [ ] **Step 3: Add Upcoming JS logic**

In `school.html`, find:

```js
  function render() {
    renderSemesterSelect();
    renderClasses();
  }
```

Replace it with:

```js
  function todayStr() {
    var d = new Date();
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }
  function daysUntil(dateStr) {
    var today = new Date(todayStr() + 'T00:00:00');
    var due = new Date(dateStr + 'T00:00:00');
    return Math.round((due - today) / 86400000);
  }
  function countdownChip(dateStr) {
    var n = daysUntil(dateStr);
    if (n < 0) return { text: 'Overdue', cls: 'overdue' };
    if (n === 0) return { text: 'Today', cls: 'today' };
    if (n === 1) return { text: 'in 1 day', cls: '' };
    return { text: 'in ' + n + ' days', cls: '' };
  }

  function renderTaskRowHtml(task, sem) {
    var cls = task.classId ? sem.classes.filter(function (c) { return c.id === task.classId; })[0] : null;
    var chip = countdownChip(task.dueDate);
    var rowDoneClass = (task.type === 'assignment' && task.done) ? ' gm-row-done' : '';
    var checkboxHtml = task.type === 'assignment'
      ? '<input type="checkbox" class="gm-check" data-done-id="' + task.id + '"' + (task.done ? ' checked' : '') + '>'
      : '';
    return '' +
      '<div class="gm-row' + rowDoneClass + '" data-id="' + task.id + '">' +
        checkboxHtml +
        '<span class="task-badge ' + task.type + '">' + (task.type === 'exam' ? 'Exam' : 'Assignment') + '</span>' +
        '<div class="task-body">' +
          '<div class="task-title">' + escapeHtml(task.title) + '</div>' +
          (cls ? '<div class="task-class">' + escapeHtml(cls.name) + '</div>' : '') +
        '</div>' +
        '<span class="task-chip ' + chip.cls + '">' + chip.text + '</span>' +
        '<button type="button" class="goal-delete" data-delete-id="' + task.id + '">×</button>' +
      '</div>';
  }

  function renderUpcoming() {
    var state = load();
    var sem = activeSemester(state);
    var list = document.getElementById('upcomingList');
    if (!sem) { list.innerHTML = '<div class="empty-state">Add a semester to get started.</div>'; return; }
    if (sem.tasks.length === 0) { list.innerHTML = '<div class="empty-state">Nothing upcoming — add one below.</div>'; return; }
    var sorted = sem.tasks.slice().sort(function (a, b) { return a.dueDate < b.dueDate ? -1 : a.dueDate > b.dueDate ? 1 : 0; });
    list.innerHTML = sorted.map(function (t) { return renderTaskRowHtml(t, sem); }).join('');
  }

  function renderTaskClassOptions() {
    var state = load();
    var sem = activeSemester(state);
    var sel = document.getElementById('taskClassSelect');
    var current = sel.value;
    sel.innerHTML = '<option value="">No class</option>';
    if (sem) {
      sem.classes.forEach(function (c) {
        var opt = document.createElement('option');
        opt.value = c.id; opt.textContent = c.name;
        sel.appendChild(opt);
      });
    }
    var stillValid = false;
    for (var i = 0; i < sel.options.length; i++) { if (sel.options[i].value === current) stillValid = true; }
    sel.value = stillValid ? current : '';
  }

  document.getElementById('upcomingList').addEventListener('click', function (e) {
    var btn = e.target.closest('[data-delete-id]');
    if (!btn) return;
    var state = load();
    var sem = activeSemester(state);
    if (!sem) return;
    var id = btn.getAttribute('data-delete-id');
    sem.tasks = sem.tasks.filter(function (t) { return t.id !== id; });
    save(state);
    render();
  });
  document.getElementById('upcomingList').addEventListener('change', function (e) {
    var cb = e.target.closest('[data-done-id]');
    if (!cb) return;
    var state = load();
    var sem = activeSemester(state);
    if (!sem) return;
    var task = sem.tasks.filter(function (t) { return t.id === cb.getAttribute('data-done-id'); })[0];
    if (!task) return;
    task.done = cb.checked;
    save(state);
    render();
  });

  function addTask() {
    var titleEl = document.getElementById('taskTitleInput');
    var dueEl = document.getElementById('taskDueInput');
    var title = titleEl.value.trim();
    var due = dueEl.value;
    if (!title || !due) return;
    var state = load();
    var sem = activeSemester(state);
    if (!sem) return;
    sem.tasks.push({
      id: uid('task'),
      title: title,
      type: document.getElementById('taskTypeSelect').value,
      classId: document.getElementById('taskClassSelect').value || null,
      dueDate: due,
      done: false
    });
    save(state);
    titleEl.value = '';
    dueEl.value = '';
    render();
  }
  document.getElementById('taskAddBtn').addEventListener('click', addTask);
  document.getElementById('taskTitleInput').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') addTask();
  });

  function render() {
    renderSemesterSelect();
    renderClasses();
    renderTaskClassOptions();
    renderUpcoming();
  }
```

- [ ] **Step 4: Verify the file is well-formed**

Run: `node -e "new Function(require('fs').readFileSync('school.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1])" && echo "JS syntax OK"`
Expected: `JS syntax OK`

- [ ] **Step 5: Manually verify in a browser**

Serve the directory and use Playwright MCP tools (or the fallback from Task 1 Step 3) to confirm:
- Adding an assignment with a due date a few days in the future shows an "in N days" chip and a checkbox; checking it applies strikethrough styling (`.gm-row-done`) and persists after reload
- Adding an exam with today's date shows a "Today" chip with the `.today` styling and no checkbox
- Adding a task with a due date in the past shows "Overdue" with `.overdue` styling
- Adding a task linked to an existing class shows the class name under the title; deleting that class (in the Classes section) and reloading shows the task row with no class name (no crash, no broken reference)
- The Upcoming list is sorted soonest-due-date-first regardless of the order items were added in
- Deleting a task removes it and the removal persists after reload

- [ ] **Step 6: Commit**

```bash
git add school.html
git commit -m "$(cat <<'EOF'
Add Upcoming section to School page

Phase 2 task 3: unified assignments+exams list sorted by due date,
shared countdown engine, checkbox for assignments / countdown chip
for exams, graceful fallback when a linked class is deleted.
EOF
)"
```

---

### Task 4: Overview section

**Files:**
- Modify: `school.html` (HTML: insert a new `<div class="section">` for Overview between the semester switcher and the Classes section; JS: add `renderOverview()` and one line to `render()`)

**Interfaces:**
- Consumes from Tasks 1-3: `load()`, `activeSemester(state)`, `todayStr()`, the existing `render()` function (this task adds one line to its body)
- Produces: nothing consumed by other tasks (this is the last task in the plan)

- [ ] **Step 1: Add the Overview section HTML**

In `school.html`, find:

```html
  </div>

  <div class="section">
    <div class="section-title">Classes</div>
```

Replace it with:

```html
  </div>

  <div class="section">
    <div class="section-title">Overview</div>
    <div class="gm-card">
      <div class="gm-header">
        <div class="gm-header-left">
          <div class="gm-eyebrow">Average Grade</div>
          <div class="gm-progress-row">
            <span class="gm-progress-num" id="ovAvgGrade">—</span>
          </div>
        </div>
      </div>
      <div class="stat-grid">
        <div class="stat"><div class="stat-num" id="ovClassCount">0</div><div class="stat-label">Classes</div></div>
        <div class="stat"><div class="stat-num" id="ovUpcomingCount">0</div><div class="stat-label">Upcoming</div></div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Classes</div>
```

- [ ] **Step 2: Add Overview JS logic**

In `school.html`, find:

```js
  function render() {
    renderSemesterSelect();
    renderClasses();
    renderTaskClassOptions();
    renderUpcoming();
  }
```

Replace it with:

```js
  function renderOverview() {
    var state = load();
    var sem = activeSemester(state);
    var avgEl = document.getElementById('ovAvgGrade');
    var classCountEl = document.getElementById('ovClassCount');
    var upcomingCountEl = document.getElementById('ovUpcomingCount');
    if (!sem) {
      avgEl.textContent = '—';
      classCountEl.textContent = '0';
      upcomingCountEl.textContent = '0';
      return;
    }
    var graded = sem.classes.filter(function (c) { return c.grade != null; });
    if (graded.length === 0) {
      avgEl.textContent = '—';
    } else {
      var sum = graded.reduce(function (acc, c) { return acc + c.grade; }, 0);
      avgEl.textContent = (Math.round((sum / graded.length) * 10) / 10) + '%';
    }
    classCountEl.textContent = String(sem.classes.length);
    var today = todayStr();
    var upcoming = sem.tasks.filter(function (t) { return t.dueDate >= today; });
    upcomingCountEl.textContent = String(upcoming.length);
  }

  function render() {
    renderSemesterSelect();
    renderClasses();
    renderTaskClassOptions();
    renderUpcoming();
    renderOverview();
  }
```

- [ ] **Step 3: Verify the file is well-formed**

Run: `node -e "new Function(require('fs').readFileSync('school.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1])" && echo "JS syntax OK"`
Expected: `JS syntax OK`

- [ ] **Step 4: Manually verify in a browser**

Serve the directory and use Playwright MCP tools (or the fallback from Task 1 Step 3) to confirm:
- With no semester selected, Overview shows "—" for average grade and "0" for both stats
- Adding classes with grades (e.g. 91 and 85) shows the correctly rounded average (88%) in Overview
- Adding a class with no grade entered doesn't pull the average toward 0 (it's excluded from the average, not treated as 0)
- The class count stat matches the number of classes in the active semester
- The upcoming count stat matches the number of tasks with `dueDate >= today` (including today, excluding past-due items)
- Switching semesters updates all three Overview numbers to that semester's own data

- [ ] **Step 5: Commit**

```bash
git add school.html
git commit -m "$(cat <<'EOF'
Add Overview section to School page

Phase 2 task 4 (final): average grade, class count, and upcoming
count, computed from the active semester's Classes and Upcoming data.
This completes the School page for phase 2 of the dashboard redesign.
EOF
)"
```
