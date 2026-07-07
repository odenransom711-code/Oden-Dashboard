# Fitness Quick Split-Tag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a row of tappable split chips to `gym.html` that mark today's workout done — with which split — without requiring any individual exercise sets to be logged first.

**Architecture:** Extend the existing `doneDays[dateKey]` localStorage record from a bare ISO-timestamp string to `{ ts, split }`, so both the new quick-tag chips and the existing "Mark workout done" button write to the same structure. `renderPastWorkouts()` is extended to include quick-tagged-only days (previously it only ever showed days with at least one logged exercise set) and to display the tagged split name when a day has no logged exercises to summarize.

**Tech Stack:** Plain HTML/CSS/JS, matching `gym.html`'s existing conventions (`const`/arrow functions, `$()` id-lookup helper, template-string HTML building via string concatenation). No test framework exists in this repo.

## Global Constraints

- `doneDays[dateKey]` shape changes from a bare ISO string to `{ ts: ISOString, split: string }`. Every read site (`renderTodaysWorkout`, `renderPastWorkouts`) already only does a truthy check (`!!doneDays[key]`), so this shape change is safe — confirmed via `grep -n "doneDays"` that no code reads it as a string anywhere.
- The existing "Mark workout done" button (`#poTwDoneBtn`) keeps its exact current behavior (toggle on/off, disabled when zero sets logged and not already done) — it's just updated to also write a `split` field, using `todaySplit().name` at the moment it's clicked.
- Quick-tag chips are NOT gated by logged-set count — tapping one always works, regardless of whether any exercises were logged today.
- Only *today* can be quick-tagged — no retroactive tagging UI for past days (explicit scope cut in the spec).
- One tag per day: tapping a different chip while one is already tagged switches the tag (doesn't add a second entry); tapping the already-tagged chip again removes the tag.
- Visual style must reuse the existing design tokens already used elsewhere in `gym.html`: `--good`, `--border`, `--text-1`/`--text-2`/`--text-3`, pill shape (`border-radius: 999px`), matching `.po-tw-done-btn`'s existing look.

---

### Task 1: Quick-tag chip row + doneDays shape change + Past Workouts update

**Files:**
- Modify: `gym.html` (CSS: add `.po-quicktag-*` rules; HTML: insert the chip row container; JS: add `renderQuickTagRow()`, modify the `#poTwDoneBtn` click handler, modify `renderPastWorkouts()`, wire `renderQuickTagRow()` into `renderAll()`)

**Interfaces:**
- Consumes: `state.splitRotation` (array of split name strings), `todaySplit()` → `{name, index}`, `wtDateKey(date)` → `'YYYY-MM-DD'` string, `doneDays` (module-level object, already declared), `loadDoneDays()`/`saveDoneDays(d)`, `logsByDay()` → `{[dateKey]: [{ex, log}]}`, `summarizeDay(daySets)` → `{perEx, totalSets, totalVol}`, `fmtPastDate(dk)`, `escape(s)` (existing HTML-escape helper used throughout this file), `$(id)` (existing `document.getElementById` shorthand) — all pre-existing, unchanged
- Produces: nothing consumed elsewhere (only task in this plan)

- [ ] **Step 1: Add quick-tag chip CSS**

In `gym.html`, find this block (currently lines 809-810, the end of the `.po-tw-empty` rules, just before the past-toggle rules):

```css
.po-tw-empty {
  text-align: center; padding: 14px 0;
  font-size: 12px; color: var(--text-3); font-style: italic;
}
.po-tw-empty.hidden { display: none; }

.po-tw-past-toggle {
```

Replace it with:

```css
.po-tw-empty {
  text-align: center; padding: 14px 0;
  font-size: 12px; color: var(--text-3); font-style: italic;
}
.po-tw-empty.hidden { display: none; }

.po-quicktag-row {
  display: flex; flex-wrap: wrap; gap: 8px;
  margin-bottom: 14px;
}
.po-quicktag-chip {
  background: rgba(255,255,255,0.025);
  border: 1px solid var(--border);
  color: var(--text-2);
  border-radius: 999px;
  padding: 8px 14px;
  font-family: inherit; font-size: 12px; font-weight: 600;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.po-quicktag-chip:hover { background: rgba(255,255,255,0.05); color: var(--text-1); }
.po-quicktag-chip.is-suggested { border-color: rgba(255,255,255,0.16); }
.po-quicktag-chip.is-tagged {
  background: rgba(110,231,183,0.16);
  color: var(--good);
  border-color: rgba(110,231,183,0.30);
}

.po-tw-past-toggle {
```

- [ ] **Step 2: Insert the quick-tag chip row HTML, before "Today's workout"**

In `gym.html`, find this block (currently lines 1550-1561):

```html
    <div class="po-sub-section">
      <div class="po-sub-title">History</div>
      <div id="historyCard">
        <div class="po-empty">No logs yet.</div>
      </div>
    </div>

    <!-- Today's Workout — every set logged today, grouped by exercise.
         "Mark done" stamps the day so the past-workouts list shows it
         as a completed session. The volume here also feeds the
         composition estimate at the top of the page. -->
    <div class="po-sub-section">
      <div class="po-sub-title">Today's workout</div>
```

Replace it with:

```html
    <div class="po-sub-section">
      <div class="po-sub-title">History</div>
      <div id="historyCard">
        <div class="po-empty">No logs yet.</div>
      </div>
    </div>

    <!-- Quick tag — mark today's split done with zero exercise logging.
         Writes the same doneDays[key] record the "Mark workout done"
         button writes ({ts, split}), just without requiring any logged
         sets first. Tapping the already-tagged chip again un-tags it. -->
    <div class="po-quicktag-row" id="poQuickTagRow"></div>

    <!-- Today's Workout — every set logged today, grouped by exercise.
         "Mark done" stamps the day so the past-workouts list shows it
         as a completed session. The volume here also feeds the
         composition estimate at the top of the page. -->
    <div class="po-sub-section">
      <div class="po-sub-title">Today's workout</div>
```

- [ ] **Step 3: Add `renderQuickTagRow()`**

In `gym.html`, find this block (the tail of `renderTodaysWorkout()`, currently lines 2172-2179):

```js
    // Done button state
    const btn = $('poTwDoneBtn');
    const isDone = !!doneDays[todayKey];
    btn.textContent = isDone ? '✓ Done' : 'Mark workout done';
    btn.classList.toggle('is-done', isDone);
    btn.disabled = sum.totalSets === 0 && !isDone;
    btn.style.opacity = btn.disabled ? '0.4' : '';
  }
```

Replace it with:

```js
    // Done button state
    const btn = $('poTwDoneBtn');
    const isDone = !!doneDays[todayKey];
    btn.textContent = isDone ? '✓ Done' : 'Mark workout done';
    btn.classList.toggle('is-done', isDone);
    btn.disabled = sum.totalSets === 0 && !isDone;
    btn.style.opacity = btn.disabled ? '0.4' : '';
  }

  function renderQuickTagRow() {
    const row = $('poQuickTagRow');
    const rot = state.splitRotation || [];
    const todayKey = wtDateKey(new Date());
    const suggested = todaySplit().name;
    const entry = doneDays[todayKey];
    const tagged = entry && entry.split;
    row.innerHTML = rot.map(name => {
      const isTagged = tagged === name;
      const isSuggested = !tagged && name === suggested;
      const cls = 'po-quicktag-chip' + (isTagged ? ' is-tagged' : '') + (isSuggested ? ' is-suggested' : '');
      return '<button type="button" class="' + cls + '" data-split="' + escape(name) + '">' + escape(name) + '</button>';
    }).join('');
    row.querySelectorAll('.po-quicktag-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const split = chip.dataset.split;
        const key = wtDateKey(new Date());
        if (doneDays[key] && doneDays[key].split === split) {
          delete doneDays[key];
        } else {
          doneDays[key] = { ts: new Date().toISOString(), split: split };
        }
        saveDoneDays(doneDays);
        renderQuickTagRow();
        renderTodaysWorkout();
        renderPastWorkouts();
      });
    });
  }
```

- [ ] **Step 4: Update the `#poTwDoneBtn` handler to write `{ts, split}` and re-render the chip row**

In `gym.html`, find this block (currently lines 2214-2224):

```js
  $('poTwDoneBtn').addEventListener('click', () => {
    const todayKey = wtDateKey(new Date());
    if (doneDays[todayKey]) {
      delete doneDays[todayKey];
    } else {
      doneDays[todayKey] = new Date().toISOString();
    }
    saveDoneDays(doneDays);
    renderTodaysWorkout();
    renderPastWorkouts();
  });
```

Replace it with:

```js
  $('poTwDoneBtn').addEventListener('click', () => {
    const todayKey = wtDateKey(new Date());
    if (doneDays[todayKey]) {
      delete doneDays[todayKey];
    } else {
      doneDays[todayKey] = { ts: new Date().toISOString(), split: todaySplit().name };
    }
    saveDoneDays(doneDays);
    renderQuickTagRow();
    renderTodaysWorkout();
    renderPastWorkouts();
  });
```

- [ ] **Step 5: Update `renderPastWorkouts()` to include quick-tagged-only days and show the tagged split**

In `gym.html`, find this exact block (the full body of `renderPastWorkouts()`, currently lines 2181-2212):

```js
  function renderPastWorkouts() {
    const todayKey = wtDateKey(new Date());
    const all = logsByDay();
    const past = Object.entries(all)
      .filter(([dk]) => dk !== todayKey)
      .sort((a, b) => b[0].localeCompare(a[0]));
    $('poTwPastCount').textContent = past.length;
    const body = $('poTwPastBody');
    if (!past.length) {
      body.innerHTML = '<div class="po-tw-past-empty">No past workouts yet.</div>';
      return;
    }
    const u = state.units;
    body.innerHTML = past.slice(0, 30).map(([dk, sets]) => {
      const sum = summarizeDay(sets);
      const isDone = !!doneDays[dk];
      const exNames = sum.perEx.map(e => e.ex.name).slice(0, 3).join(', ')
        + (sum.perEx.length > 3 ? '…' : '');
      return '<div class="po-tw-past-day">'
        + '<div class="po-tw-past-day-h">'
        +   '<span class="po-tw-past-day-date">' + fmtPastDate(dk) + '</span>'
        +   '<span class="po-tw-past-day-summary">'
        +     sum.totalSets + ' sets · ' + Math.round(sum.totalVol).toLocaleString() + ' ' + u
        +     (isDone ? ' <span class="po-tw-past-day-done">DONE</span>' : '')
        +   '</span>'
        + '</div>'
        + '<div class="po-tw-past-day-summary" style="margin-top:6px; font-size:11px; color:var(--text-3);">'
        +   escape(exNames)
        + '</div>'
        + '</div>';
    }).join('');
  }
```

Replace it with:

```js
  function renderPastWorkouts() {
    const todayKey = wtDateKey(new Date());
    const all = logsByDay();
    const dayKeys = new Set(Object.keys(all));
    Object.keys(doneDays).forEach(k => dayKeys.add(k));
    dayKeys.delete(todayKey);
    const past = Array.from(dayKeys).sort((a, b) => b.localeCompare(a));
    $('poTwPastCount').textContent = past.length;
    const body = $('poTwPastBody');
    if (!past.length) {
      body.innerHTML = '<div class="po-tw-past-empty">No past workouts yet.</div>';
      return;
    }
    const u = state.units;
    body.innerHTML = past.slice(0, 30).map((dk) => {
      const sets = all[dk] || [];
      const sum = summarizeDay(sets);
      const entry = doneDays[dk];
      const isDone = !!entry;
      const taggedSplit = isDone && entry.split;
      const exNames = sum.perEx.length
        ? sum.perEx.map(e => e.ex.name).slice(0, 3).join(', ') + (sum.perEx.length > 3 ? '…' : '')
        : (taggedSplit ? taggedSplit + ' · quick tag' : '');
      return '<div class="po-tw-past-day">'
        + '<div class="po-tw-past-day-h">'
        +   '<span class="po-tw-past-day-date">' + fmtPastDate(dk) + '</span>'
        +   '<span class="po-tw-past-day-summary">'
        +     sum.totalSets + ' sets · ' + Math.round(sum.totalVol).toLocaleString() + ' ' + u
        +     (isDone ? ' <span class="po-tw-past-day-done">DONE</span>' : '')
        +   '</span>'
        + '</div>'
        + '<div class="po-tw-past-day-summary" style="margin-top:6px; font-size:11px; color:var(--text-3);">'
        +   escape(exNames)
        + '</div>'
        + '</div>';
    }).join('');
  }
```

- [ ] **Step 6: Wire `renderQuickTagRow()` into the page-load render orchestrator**

In `gym.html`, find this block (currently lines 2062-2068):

```js
  function renderAll() {
    renderDayPill();
    renderFilters(); renderSelect(); renderForm(); renderLastSet();
    renderRepsRow();
    renderRx(); renderStats(); renderSparkline(); renderHistory();
    renderTodaysWorkout();
    renderPastWorkouts();
```

Replace it with:

```js
  function renderAll() {
    renderDayPill();
    renderFilters(); renderSelect(); renderForm(); renderLastSet();
    renderRepsRow();
    renderRx(); renderStats(); renderSparkline(); renderHistory();
    renderQuickTagRow();
    renderTodaysWorkout();
    renderPastWorkouts();
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
Expected: prints a count with no syntax errors thrown (note the count itself — `gym.html` has both the `CONFIG` script block near the top and the main app IIFE further down; both must parse cleanly).

- [ ] **Step 8: Manually verify in a browser**

Serve the directory (`python3 -m http.server 8123` from the repo root) and use Playwright MCP tools to navigate to `http://localhost:8123/gym.html`, seeding/clearing `localStorage` via `browser_evaluate` as needed (or, if Playwright's Chromium binary is unavailable in this environment — a known issue seen throughout this project — fall back to curl-fetching the served HTML to confirm `#poQuickTagRow` exists in the right position, and manually tracing the click handler logic and the `renderPastWorkouts()` union-of-keys logic by reading the code; report this fallback clearly and use `DONE_WITH_CONCERNS` if used).

Confirm:
- The quick-tag row renders one chip per entry in the configured split rotation, with today's computed split visually distinguished (`is-suggested`)
- Tapping an untagged chip with zero exercises logged today marks it `is-tagged` (green) immediately, and the "Mark workout done" button also flips to its done state (since both read the same `doneDays[todayKey]`)
- Tapping the tagged chip again removes the tag; both the chip and the "Mark workout done" button revert
- Tapping a different chip while one is tagged switches the tag to the new chip (only one chip shows `is-tagged` at a time)
- After tagging today with zero exercises logged, expanding "Past workouts" the next day (or by manipulating `doneDays`/date in devtools for testing) shows that day with a "DONE" badge and "`<Split>` · quick tag" text instead of a blank exercise summary
- Logging an exercise set and clicking "Mark workout done" still works exactly as before, and now also sets `doneDays[todayKey].split` to today's rotation split

- [ ] **Step 9: Commit**

```bash
git add gym.html
git commit -m "$(cat <<'EOF'
Add quick split-tagging to Fitness page

Lets you mark today's split done with a single tap, no exercise
logging required. Extends doneDays[date] from a bare timestamp to
{ts, split} so both the new chip row and the existing "Mark workout
done" button write to the same record. Past Workouts now also
surfaces quick-tagged-only days (previously only days with logged
exercise sets ever appeared there).
EOF
)"
```
