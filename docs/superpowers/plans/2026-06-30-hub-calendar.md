# Hub Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Calendar block to the hub (`index.html`) — a month grid with expand-in-place day selection, manual event entry, and an "Upcoming" agenda list of the next 5 events.

**Architecture:** Pure HTML/CSS/JS addition to `index.html`, in its own self-contained `<script>` IIFE (separate from the page's existing settings/WHOOP script, to avoid any naming collisions) with its own localStorage key (`calendar_v1`) and cloud-sync registration. Built up incrementally across 3 tasks: month grid + navigation, then day selection + event add/delete, then the agenda list.

**Tech Stack:** Plain HTML/CSS, vanilla JS (`var`, no arrow functions beyond what's already used elsewhere in this file — note `index.html`'s existing script already uses `const`/arrow functions in places, e.g. its WHOOP logic, so either style is acceptable in this file; this plan uses `var`/`function` throughout the new calendar script for internal consistency within the new code, matching the convention used in `school.html` and `health.html`'s newer additions). No test framework exists in this repo.

## Global Constraints

- One new localStorage key: `calendar_v1`, holding `{ events: [{id, date: 'YYYY-MM-DD', title, time}] }`. `time` is optional (empty string when unset).
- Cloud sync: `appKey: 'calendar'` via `window.initCloudSync`, **registered inside `document.addEventListener('DOMContentLoaded', ...)`**, not a bare `if (window.initCloudSync)` check at script-execution time — phase 2 (School page) surfaced a real bug where the bare-check pattern silently never fires because the inline script runs before the deferred `sync.js` loads. Confirmed available: `appKey` values already in use elsewhere are `caffeine`, `finance`, `health`, `goals`, `template`, `school` — `calendar` is free.
- No event categories — events are title + date + optional time only, no type/color.
- Manual entry only — no auto-pulling classes from School or workouts from Fitness in this phase.
- The Calendar section sits between the hub header row (`.hub-head`) and the bento tile grid (`.bento`) in `index.html`.
- `index.html` does not currently define `.section`/`.section-title` (that convention exists in `template.html`/`school.html`/`health.html` but was never carried into `index.html`). This plan adds those two rules to `index.html` as part of Task 1, copied verbatim from the established pattern, to use a consistent section heading for "Calendar." `index.html` also does not define `--success`/`--warning`/`--danger` or `.gm-card` — the new calendar CSS uses fresh `.cal-*` class names styled to match `index.html`'s own existing visual language (the `.tile` card look: `rgba(255,255,255,0.04)` background, `blur(24px) saturate(1.2)`, `var(--text-primary)`/`var(--text-secondary)`/`var(--text-tertiary)`, which do already exist in `index.html`'s `:root`), not copy-pasted from `template.html`'s separate `.gm-card` system.
- Lightweight error handling only: adding an event requires a non-empty title (date is implicit from the selected day, so never missing); no confirmation dialogs on delete.

---

### Task 1: Calendar section shell, data model, month grid, navigation

**Files:**
- Modify: `index.html:198-199` (end of `<style>` block — insert new CSS before `</style>`)
- Modify: `index.html:213-215` (insert new HTML section between `.hub-head`'s close and `.bento`'s open)
- Modify: `index.html:541-542` (insert new `<script>` block between the existing script's close and `</body>`)

**Interfaces:**
- Consumes: nothing (first task)
- Produces (for Tasks 2-3 to use verbatim):
  - `CAL_KEY` = `'calendar_v1'`
  - `CAL_MONTHS` — array of full month names, index 0 = January
  - `calLoad()` → `{ events: Array<{id, date, title, time}> }`
  - `calSave(state)` → persists to localStorage
  - `calUid()` → unique string id like `"evt_abc12xy"`
  - `calToday()` → `{ y, m, d }` (m is 0-indexed, matching `Date.getMonth()`)
  - `calPad2(n)` → zero-pads a number to 2 digits as a string
  - `calDateStr(y, m, day)` → `"YYYY-MM-DD"` string (m is 0-indexed)
  - `viewYear`, `viewMonth` — module-level mutable state for which month the grid currently shows (not persisted)
  - `calBuildWeeks(y, m)` → array of 7-element arrays (each element is a day number 1-31, or `null` for a leading/trailing filler cell)
  - `calRenderGrid()` → re-renders `#calGrid` and `#calMonthLabel`; Tasks 2-3 each modify this function's body
  - HTML: `#calPrevBtn`, `#calNextBtn`, `#calMonthLabel`, `#calGrid` ids exist and are wired

- [ ] **Step 1: Add Calendar CSS**

In `index.html`, find this block (currently lines 197-199):

```css
.whoop-btn { width: 100%; margin-top: 14px; padding: 11px; border: 1px solid rgba(255,255,255,0.12); border-radius: 11px; background: transparent; color: var(--text-secondary); font-family: inherit; font-size: 12px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; cursor: pointer; transition: background 0.15s, color 0.15s; }
.whoop-btn:hover { background: rgba(255,255,255,0.05); color: var(--text-primary); }
</style>
```

Replace it with:

```css
.whoop-btn { width: 100%; margin-top: 14px; padding: 11px; border: 1px solid rgba(255,255,255,0.12); border-radius: 11px; background: transparent; color: var(--text-secondary); font-family: inherit; font-size: 12px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; cursor: pointer; transition: background 0.15s, color 0.15s; }
.whoop-btn:hover { background: rgba(255,255,255,0.05); color: var(--text-primary); }

/* ===== Calendar ===== */
.section { margin-top: 8px; margin-bottom: 22px; }
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
.cal-card {
  position: relative;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 18px;
  padding: 20px;
  margin-bottom: 14px;
  backdrop-filter: blur(24px) saturate(1.2);
  -webkit-backdrop-filter: blur(24px) saturate(1.2);
  box-shadow: 0 12px 40px rgba(0,0,0,0.45);
}
.cal-nav {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 14px;
}
.cal-nav-label {
  font-size: 16px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.01em;
}
.cal-nav-btn {
  width: 32px; height: 32px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 9px; border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.04); color: var(--text-secondary);
  cursor: pointer; font-size: 16px; transition: background 0.15s, color 0.15s;
}
.cal-nav-btn:hover { background: rgba(255,255,255,0.08); color: var(--text-primary); }
.cal-weekday-row {
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px;
  margin-bottom: 6px;
}
.cal-weekday {
  text-align: center; font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-tertiary);
  padding: 4px 0;
}
.cal-week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 4px; }
.cal-day {
  position: relative;
  height: 44px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 10px; border: 1px solid transparent;
  cursor: pointer; transition: background 0.15s, border-color 0.15s;
}
.cal-day:hover { background: rgba(255,255,255,0.05); }
.cal-day-empty { cursor: default; }
.cal-day-empty:hover { background: transparent; }
.cal-day-num { font-size: 13px; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.cal-day-today { border-color: rgba(107,227,164,0.5); }
.cal-day-today .cal-day-num { color: var(--text-primary); font-weight: 700; }
.cal-day-dot {
  position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%);
  width: 4px; height: 4px; border-radius: 50%; background: #6BE3A4;
}
@media (max-width: 480px) {
  .cal-card { padding: 16px; }
  .cal-day { height: 38px; }
}
</style>
```

- [ ] **Step 2: Add the Calendar section HTML**

In `index.html`, find this block (currently lines 212-215):

```html
    </button>
  </div>

  <div class="bento">
```

Replace it with:

```html
    </button>
  </div>

  <div class="section">
    <div class="section-title">Calendar</div>
    <div class="cal-card">
      <div class="cal-nav">
        <button class="cal-nav-btn" id="calPrevBtn" type="button" aria-label="Previous month">‹</button>
        <span class="cal-nav-label" id="calMonthLabel"></span>
        <button class="cal-nav-btn" id="calNextBtn" type="button" aria-label="Next month">›</button>
      </div>
      <div class="cal-weekday-row">
        <div class="cal-weekday">Sun</div>
        <div class="cal-weekday">Mon</div>
        <div class="cal-weekday">Tue</div>
        <div class="cal-weekday">Wed</div>
        <div class="cal-weekday">Thu</div>
        <div class="cal-weekday">Fri</div>
        <div class="cal-weekday">Sat</div>
      </div>
      <div id="calGrid"></div>
    </div>
  </div>

  <div class="bento">
```

- [ ] **Step 3: Add the Calendar JS as a new, separate script block**

In `index.html`, find this block (currently lines 540-542, the very end of the file):

```js
})();
</script>
</body>
</html>
```

Replace it with:

```js
})();
</script>

<script>
(function () {
  'use strict';

  var CAL_KEY = 'calendar_v1';
  var CAL_MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

  function calLoad() {
    try {
      var v = JSON.parse(localStorage.getItem(CAL_KEY));
      if (v && Array.isArray(v.events)) return v;
    } catch (e) {}
    return { events: [] };
  }
  function calSave(state) { localStorage.setItem(CAL_KEY, JSON.stringify(state)); }
  function calUid() { return 'evt_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }

  function calToday() {
    var d = new Date();
    return { y: d.getFullYear(), m: d.getMonth(), d: d.getDate() };
  }
  function calPad2(n) { return n < 10 ? '0' + n : String(n); }
  function calDateStr(y, m, day) { return y + '-' + calPad2(m + 1) + '-' + calPad2(day); }

  var today0 = calToday();
  var viewYear = today0.y;
  var viewMonth = today0.m;

  function calBuildWeeks(y, m) {
    var firstDow = new Date(y, m, 1).getDay();
    var daysInMonth = new Date(y, m + 1, 0).getDate();
    var cells = [];
    for (var i = 0; i < firstDow; i++) cells.push(null);
    for (var day = 1; day <= daysInMonth; day++) cells.push(day);
    while (cells.length % 7 !== 0) cells.push(null);
    var weeks = [];
    for (var i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
    return weeks;
  }

  function calRenderGrid() {
    var state = calLoad();
    var weeks = calBuildWeeks(viewYear, viewMonth);
    var today = calToday();
    var html = '';
    weeks.forEach(function (week) {
      html += '<div class="cal-week">';
      week.forEach(function (day) {
        if (day == null) { html += '<div class="cal-day cal-day-empty"></div>'; return; }
        var dateStr = calDateStr(viewYear, viewMonth, day);
        var isToday = today.y === viewYear && today.m === viewMonth && today.d === day;
        var hasEvents = state.events.some(function (e) { return e.date === dateStr; });
        html += '<div class="cal-day' + (isToday ? ' cal-day-today' : '') + '" data-date="' + dateStr + '">' +
                  '<span class="cal-day-num">' + day + '</span>' +
                  (hasEvents ? '<span class="cal-day-dot"></span>' : '') +
                '</div>';
      });
      html += '</div>';
    });
    document.getElementById('calGrid').innerHTML = html;
    document.getElementById('calMonthLabel').textContent = CAL_MONTHS[viewMonth] + ' ' + viewYear;
  }

  document.getElementById('calPrevBtn').addEventListener('click', function () {
    viewMonth--;
    if (viewMonth < 0) { viewMonth = 11; viewYear--; }
    calRenderGrid();
  });
  document.getElementById('calNextBtn').addEventListener('click', function () {
    viewMonth++;
    if (viewMonth > 11) { viewMonth = 0; viewYear++; }
    calRenderGrid();
  });

  calRenderGrid();

  document.addEventListener('DOMContentLoaded', function () {
    if (typeof initCloudSync !== 'function') return;
    initCloudSync({
      appKey: 'calendar',
      syncedKeys: [CAL_KEY],
      onApplied: calRenderGrid
    });
  });
})();
</script>
</body>
</html>
```

- [ ] **Step 4: Verify the file is well-formed**

Run:
```bash
node -e "
var fs = require('fs');
var s = fs.readFileSync('index.html', 'utf8');
var re = /<script>([\s\S]*?)<\/script>/g;
var m, count = 0;
while ((m = re.exec(s))) { new Function(m[1]); count++; }
console.log('checked', count, 'inline script blocks OK');
"
```
Expected: `checked 2 inline script blocks OK` (the pre-existing settings/WHOOP script, plus the new calendar script — both must compile with no syntax errors).

- [ ] **Step 5: Manually verify in a browser**

Serve the directory (`python3 -m http.server 8123` from the repo root) and use Playwright MCP tools to navigate to `http://localhost:8123/index.html` (or, if Playwright's Chromium binary is unavailable in this environment — a known issue seen throughout this project — fall back to: curl-fetching the page to confirm the `#calPrevBtn`/`#calNextBtn`/`#calMonthLabel`/`#calGrid` elements exist, and manually tracing `calBuildWeeks` by hand for the current real month to confirm the day count and leading-blank-cell count are correct; report this fallback clearly and use `DONE_WITH_CONCERNS` if used).

Expected, if visual verification is possible: a "Calendar" section appears between the header and the tile grid, showing the current month's name and year, a 7-column weekday header (Sun-Sat), and a grid of day cells with today's date visually highlighted (bordered). Clicking the `‹`/`›` buttons changes the displayed month. Reload the page and confirm it always reopens to the real current month (view state is not persisted).

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "$(cat <<'EOF'
Add Calendar month grid and navigation to hub

Phase 3b task 1: calendar_v1 data model, month grid rendering with
today highlighting and event-dot indicators, prev/next month nav,
cloud sync registered inside DOMContentLoaded (avoiding the init-
timing bug found during the School page build).
EOF
)"
```

---

### Task 2: Day selection, expand-in-place event list, add/delete events

**Files:**
- Modify: `index.html` (CSS: add selection/detail-strip/event-row rules; JS: modify `calRenderGrid()`, add new functions and event listeners)

**Interfaces:**
- Consumes from Task 1: `CAL_KEY`, `CAL_MONTHS`, `calLoad()`, `calSave(state)`, `calUid()`, `calToday()`, `calDateStr(y, m, day)`, `viewYear`, `viewMonth`, `calBuildWeeks(y, m)`, the existing `calRenderGrid()` (this task modifies its body)
- Produces (for Task 3 to use verbatim):
  - `selectedDate` — module-level mutable state, `'YYYY-MM-DD'` or `null`
  - `calEscapeHtml(s)` → HTML-escapes a string for safe innerHTML interpolation
  - Each event object is shaped `{ id, date: 'YYYY-MM-DD', title, time }` (`time` may be `''`)
  - `.cal-event-row`, `.cal-event-title`, `.cal-event-time` CSS classes, reusable for Task 3's agenda rows

- [ ] **Step 1: Add selection/detail-strip CSS**

In `index.html`, find this block (the end of the Calendar CSS added in Task 1):

```css
.cal-day-dot {
  position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%);
  width: 4px; height: 4px; border-radius: 50%; background: #6BE3A4;
}
@media (max-width: 480px) {
  .cal-card { padding: 16px; }
  .cal-day { height: 38px; }
}
```

Replace it with:

```css
.cal-day-dot {
  position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%);
  width: 4px; height: 4px; border-radius: 50%; background: #6BE3A4;
}
.cal-day-selected { border-color: rgba(107,227,164,0.8); background: rgba(107,227,164,0.08); }
.cal-day-detail {
  background: rgba(255,255,255,0.035);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 14px;
  margin: -2px 0 8px;
}
.cal-detail-heading { font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 10px; }
.cal-detail-empty { font-size: 12px; font-style: italic; color: var(--text-tertiary); padding: 6px 0; }
.cal-event-list { margin-bottom: 10px; }
.cal-event-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; margin-bottom: 4px;
  background: rgba(255,255,255,0.04); border-radius: 9px;
}
.cal-event-title { flex: 1; font-size: 13px; color: var(--text-primary); }
.cal-event-time { font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary); }
.cal-event-delete { border: 0; background: transparent; color: var(--text-tertiary); font-size: 16px; cursor: pointer; padding: 0 2px; }
.cal-event-delete:hover { color: #FF6B6B; }
.cal-event-add-row { display: flex; gap: 8px; flex-wrap: wrap; }
.cal-event-input {
  flex: 1; min-width: 100px; padding: 9px 12px;
  border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
  background: rgba(0,0,0,0.28); color: var(--text-primary);
  font-family: inherit; font-size: 13px; outline: none;
}
.cal-event-input::placeholder { color: var(--text-tertiary); }
.cal-event-time-input {
  padding: 9px 10px; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
  background: rgba(0,0,0,0.28); color: var(--text-primary);
  font-family: inherit; font-size: 13px; outline: none; max-width: 110px;
}
.cal-event-add-btn {
  padding: 9px 16px; border: 0; border-radius: 10px;
  background: linear-gradient(180deg, #FFFFFF 0%, #E8E5DD 100%);
  color: #0A0A0B; font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
}
@media (max-width: 480px) {
  .cal-card { padding: 16px; }
  .cal-day { height: 38px; }
}
```

- [ ] **Step 2: Modify `calRenderGrid()` to support selection and the expand-in-place detail strip; add supporting functions and event listeners**

In `index.html`, find this block:

```js
  function calRenderGrid() {
    var state = calLoad();
    var weeks = calBuildWeeks(viewYear, viewMonth);
    var today = calToday();
    var html = '';
    weeks.forEach(function (week) {
      html += '<div class="cal-week">';
      week.forEach(function (day) {
        if (day == null) { html += '<div class="cal-day cal-day-empty"></div>'; return; }
        var dateStr = calDateStr(viewYear, viewMonth, day);
        var isToday = today.y === viewYear && today.m === viewMonth && today.d === day;
        var hasEvents = state.events.some(function (e) { return e.date === dateStr; });
        html += '<div class="cal-day' + (isToday ? ' cal-day-today' : '') + '" data-date="' + dateStr + '">' +
                  '<span class="cal-day-num">' + day + '</span>' +
                  (hasEvents ? '<span class="cal-day-dot"></span>' : '') +
                '</div>';
      });
      html += '</div>';
    });
    document.getElementById('calGrid').innerHTML = html;
    document.getElementById('calMonthLabel').textContent = CAL_MONTHS[viewMonth] + ' ' + viewYear;
  }

  document.getElementById('calPrevBtn').addEventListener('click', function () {
```

Replace it with:

```js
  var selectedDate = null;

  function calEscapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
    });
  }

  function calRenderDetailHtml(dateStr, state) {
    var dayEvents = state.events.filter(function (e) { return e.date === dateStr; }).sort(function (a, b) {
      return (a.time || '').localeCompare(b.time || '');
    });
    var parts = dateStr.split('-');
    var label = CAL_MONTHS[parseInt(parts[1], 10) - 1] + ' ' + parseInt(parts[2], 10) + ', ' + parts[0];
    var listHtml = dayEvents.length === 0
      ? '<div class="cal-detail-empty">No events yet.</div>'
      : dayEvents.map(function (e) {
          return '<div class="cal-event-row" data-id="' + e.id + '">' +
                   '<span class="cal-event-title">' + calEscapeHtml(e.title) + '</span>' +
                   (e.time ? '<span class="cal-event-time">' + calEscapeHtml(e.time) + '</span>' : '') +
                   '<button type="button" class="cal-event-delete" data-delete-id="' + e.id + '">×</button>' +
                 '</div>';
        }).join('');
    return '' +
      '<div class="cal-day-detail">' +
        '<div class="cal-detail-heading">' + label + '</div>' +
        '<div class="cal-event-list">' + listHtml + '</div>' +
        '<div class="cal-event-add-row">' +
          '<input class="cal-event-input" id="calEventTitleInput" type="text" placeholder="Event title…" autocomplete="off">' +
          '<input class="cal-event-time-input" id="calEventTimeInput" type="time">' +
          '<button class="cal-event-add-btn" id="calEventAddBtn" type="button">+ Add</button>' +
        '</div>' +
      '</div>';
  }

  function calRenderGrid() {
    var state = calLoad();
    var weeks = calBuildWeeks(viewYear, viewMonth);
    var today = calToday();
    var html = '';
    weeks.forEach(function (week) {
      html += '<div class="cal-week">';
      week.forEach(function (day) {
        if (day == null) { html += '<div class="cal-day cal-day-empty"></div>'; return; }
        var dateStr = calDateStr(viewYear, viewMonth, day);
        var isToday = today.y === viewYear && today.m === viewMonth && today.d === day;
        var hasEvents = state.events.some(function (e) { return e.date === dateStr; });
        var isSelected = selectedDate === dateStr;
        html += '<div class="cal-day' + (isToday ? ' cal-day-today' : '') + (isSelected ? ' cal-day-selected' : '') + '" data-date="' + dateStr + '">' +
                  '<span class="cal-day-num">' + day + '</span>' +
                  (hasEvents ? '<span class="cal-day-dot"></span>' : '') +
                '</div>';
      });
      html += '</div>';
      var weekHasSelected = selectedDate && week.some(function (day) { return day != null && calDateStr(viewYear, viewMonth, day) === selectedDate; });
      if (weekHasSelected) html += calRenderDetailHtml(selectedDate, state);
    });
    document.getElementById('calGrid').innerHTML = html;
    document.getElementById('calMonthLabel').textContent = CAL_MONTHS[viewMonth] + ' ' + viewYear;
    var addBtn = document.getElementById('calEventAddBtn');
    if (addBtn) addBtn.addEventListener('click', calAddEvent);
    var titleInput = document.getElementById('calEventTitleInput');
    if (titleInput) titleInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') calAddEvent(); });
  }

  function calAddEvent() {
    var titleEl = document.getElementById('calEventTitleInput');
    var timeEl = document.getElementById('calEventTimeInput');
    var title = titleEl.value.trim();
    if (!title || !selectedDate) return;
    var state = calLoad();
    state.events.push({ id: calUid(), date: selectedDate, title: title, time: timeEl.value });
    calSave(state);
    calRenderGrid();
  }

  document.getElementById('calGrid').addEventListener('click', function (e) {
    var del = e.target.closest('[data-delete-id]');
    if (del) {
      var state = calLoad();
      state.events = state.events.filter(function (ev) { return ev.id !== del.getAttribute('data-delete-id'); });
      calSave(state);
      calRenderGrid();
      return;
    }
    var dayCell = e.target.closest('.cal-day[data-date]');
    if (dayCell) {
      var dateStr = dayCell.getAttribute('data-date');
      selectedDate = (selectedDate === dateStr) ? null : dateStr;
      calRenderGrid();
    }
  });

  document.getElementById('calPrevBtn').addEventListener('click', function () {
```

- [ ] **Step 3: Verify the file is well-formed**

Run the same multi-script-block check from Task 1 Step 4:
```bash
node -e "
var fs = require('fs');
var s = fs.readFileSync('index.html', 'utf8');
var re = /<script>([\s\S]*?)<\/script>/g;
var m, count = 0;
while ((m = re.exec(s))) { new Function(m[1]); count++; }
console.log('checked', count, 'inline script blocks OK');
"
```
Expected: `checked 2 inline script blocks OK`

- [ ] **Step 4: Manually verify in a browser**

Serve the directory and use Playwright MCP tools (or the curl/code-trace fallback from Task 1 Step 5 if Chromium is unavailable) to confirm:
- Clicking a day cell expands a detail strip directly below that day's week row, showing "No events yet." and an add-event form
- Adding an event with a title (and optionally a time) makes it appear in the list immediately, and a dot appears on that day's cell
- Clicking the same day again collapses the strip; clicking a different day moves the strip there instead
- Deleting an event removes it from the list and the day's dot disappears once no events remain for that day
- Reloading the page and re-selecting the same day shows the event persisted

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "$(cat <<'EOF'
Add day selection and event add/delete to hub Calendar

Phase 3b task 2: clicking a day inserts an expand-in-place detail
strip below that week's row (not a modal, not a resized grid cell)
showing the day's events and an add-event form. Title is required;
date comes from the selected day; no confirmation on delete.
EOF
)"
```

---

### Task 3: Upcoming agenda list

**Files:**
- Modify: `index.html` (CSS: add agenda title/date-label rules; HTML: add a second `.cal-card` for the agenda; JS: add `calRenderAgenda()` and call it from `calRenderGrid()`)

**Interfaces:**
- Consumes from Tasks 1-2: `calLoad()`, `calToday()`, `calDateStr(y, m, day)`, `calEscapeHtml(s)`, `CAL_MONTHS`, the existing `calRenderGrid()` (this task adds one line to its body)
- Produces: nothing consumed elsewhere (last task in this plan)

- [ ] **Step 1: Add agenda CSS**

In `index.html`, find this block (the end of the Calendar CSS added in Task 2):

```css
.cal-event-add-btn {
  padding: 9px 16px; border: 0; border-radius: 10px;
  background: linear-gradient(180deg, #FFFFFF 0%, #E8E5DD 100%);
  color: #0A0A0B; font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
}
@media (max-width: 480px) {
  .cal-card { padding: 16px; }
  .cal-day { height: 38px; }
}
```

Replace it with:

```css
.cal-event-add-btn {
  padding: 9px 16px; border: 0; border-radius: 10px;
  background: linear-gradient(180deg, #FFFFFF 0%, #E8E5DD 100%);
  color: #0A0A0B; font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
}
.cal-agenda-title {
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--text-tertiary); margin-bottom: 10px;
}
.cal-event-date {
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  color: var(--text-tertiary); flex-shrink: 0; width: 56px;
}
@media (max-width: 480px) {
  .cal-card { padding: 16px; }
  .cal-day { height: 38px; }
}
```

- [ ] **Step 2: Add the agenda card HTML**

In `index.html`, find this block (the end of the Calendar section, right after `#calGrid`'s container closes):

```html
      <div id="calGrid"></div>
    </div>
  </div>

  <div class="bento">
```

Replace it with:

```html
      <div id="calGrid"></div>
    </div>

    <div class="cal-card">
      <div class="cal-agenda-title">Upcoming</div>
      <div id="calAgenda"></div>
    </div>
  </div>

  <div class="bento">
```

- [ ] **Step 3: Add `calRenderAgenda()` and call it from `calRenderGrid()`**

In `index.html`, find this block (the tail end of `calRenderGrid()`):

```js
    document.getElementById('calGrid').innerHTML = html;
    document.getElementById('calMonthLabel').textContent = CAL_MONTHS[viewMonth] + ' ' + viewYear;
    var addBtn = document.getElementById('calEventAddBtn');
    if (addBtn) addBtn.addEventListener('click', calAddEvent);
    var titleInput = document.getElementById('calEventTitleInput');
    if (titleInput) titleInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') calAddEvent(); });
  }
```

Replace it with:

```js
    document.getElementById('calGrid').innerHTML = html;
    document.getElementById('calMonthLabel').textContent = CAL_MONTHS[viewMonth] + ' ' + viewYear;
    var addBtn = document.getElementById('calEventAddBtn');
    if (addBtn) addBtn.addEventListener('click', calAddEvent);
    var titleInput = document.getElementById('calEventTitleInput');
    if (titleInput) titleInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') calAddEvent(); });
    calRenderAgenda();
  }

  function calTodayStr() {
    var t = calToday();
    return calDateStr(t.y, t.m, t.d);
  }

  function calAgendaDateLabel(dateStr) {
    var parts = dateStr.split('-');
    var d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    var weekday = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getDay()];
    return weekday + ' ' + CAL_MONTHS[d.getMonth()].slice(0, 3) + ' ' + d.getDate();
  }

  function calRenderAgenda() {
    var state = calLoad();
    var today = calTodayStr();
    var upcoming = state.events
      .filter(function (e) { return e.date >= today; })
      .sort(function (a, b) {
        if (a.date !== b.date) return a.date < b.date ? -1 : 1;
        return (a.time || '').localeCompare(b.time || '');
      })
      .slice(0, 5);
    var el = document.getElementById('calAgenda');
    if (upcoming.length === 0) { el.innerHTML = '<div class="cal-detail-empty">Nothing on the calendar yet.</div>'; return; }
    el.innerHTML = upcoming.map(function (e) {
      return '<div class="cal-event-row">' +
               '<span class="cal-event-date">' + calAgendaDateLabel(e.date) + '</span>' +
               '<span class="cal-event-title">' + calEscapeHtml(e.title) + '</span>' +
               (e.time ? '<span class="cal-event-time">' + calEscapeHtml(e.time) + '</span>' : '') +
             '</div>';
    }).join('');
  }
```

- [ ] **Step 4: Verify the file is well-formed**

Run the same multi-script-block check from Task 1 Step 4:
```bash
node -e "
var fs = require('fs');
var s = fs.readFileSync('index.html', 'utf8');
var re = /<script>([\s\S]*?)<\/script>/g;
var m, count = 0;
while ((m = re.exec(s))) { new Function(m[1]); count++; }
console.log('checked', count, 'inline script blocks OK');
"
```
Expected: `checked 2 inline script blocks OK`

- [ ] **Step 5: Manually verify in a browser**

Serve the directory and use Playwright MCP tools (or the curl/code-trace fallback from Task 1 Step 5 if Chromium is unavailable) to confirm:
- With zero events, the agenda card shows "Nothing on the calendar yet."
- Adding events on several different future dates (some in the current month, at least one in a different month) shows them in the agenda sorted soonest-first, capped at 5, regardless of which month the grid above is currently displaying
- An event dated in the past does NOT appear in the agenda
- Deleting an event via the day-detail strip removes it from the agenda too (since `calRenderAgenda()` now runs on every `calRenderGrid()` call)
- Navigating the month grid to a different month does not change the agenda's contents

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "$(cat <<'EOF'
Add Upcoming agenda list to hub Calendar

Phase 3b task 3 (final): next 5 events sorted by date/time, shown
regardless of which month the grid above is displaying. Completes
the Calendar feature and phase 3 of the dashboard redesign.
EOF
)"
```
