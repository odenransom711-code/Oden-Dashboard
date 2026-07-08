# Fitness Inline Photos + Always-Visible Past Workouts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the two remaining "extra tap" gates on `gym.html` — the collapsed Past Workouts list and the button-triggered progress-photos overlay — so both render inline, always visible, matching the rest of the page.

**Architecture:** Two independent, sequential edits to `gym.html`. Task 1 removes the Past Workouts collapse/toggle (its base CSS already renders as `display: flex` — only an inline `style="display:none"` and a toggle button are removed). Task 2 removes the full-screen slide-up shell (`#wtOverlay`, `position: fixed; inset: 0`) around the progress-photos grid and re-wraps the same action buttons/file inputs/grid markup in a plain in-flow `po-sub-section`, wiring the existing `photosRender()` function into the page's `renderAll()` orchestrator so the grid has real content on page load instead of only after a click. The camera-capture screen and the full-screen single/compare photo viewer are untouched — only the browsing grid moves.

**Tech Stack:** Plain HTML/CSS/JS, matching `gym.html`'s existing conventions (`const`/arrow functions and `function` declarations mixed, `$()` id-lookup helper, template-string HTML building). No test framework exists in this repo.

## Global Constraints

- No CSS changes are needed for Task 2 — `.wt-overlay-actions`, `.wt-overlay-action`, `.wt-photo-grid`, `.wt-photo-empty`, `.wt-photo-card` etc. are plain grid/button styles with no dependency on being nested inside the removed fixed-position overlay; they render correctly in normal document flow unchanged.
- `.wt-overlay`, `.wt-overlay-inner`, `.wt-overlay-h`, `.wt-back`, `.wt-overlay-title` CSS rules become dead/unused after Task 2 — intentionally left in the stylesheet rather than cleaned up, matching the precedent already established in this project (the Finance page's tab-bar CSS was left as harmless dead code after removing the tabs it styled).
- Camera capture (`#wtCam`) and the full-screen photo viewer/compare tool (`#wtViewer`) are completely unchanged by this plan — same triggers (`openPhoto()`, the Take Photo button), same full-screen overlay behavior.
- Every element id referenced by existing JS (`#wtProgressCount`, `#wtTakePhotoBtn`, `#wtFromLibraryBtn`, `#wtFileCamera`, `#wtFileLibrary`, `#wtPhotoGrid`, `#poTwPastCount`, `#poTwPastBody`) must still exist after these edits — only their containing wrapper elements and interactivity (button vs. static label) change.
- `photosRender()` (gym.html:3069+) must run at page load, not only on a user click — wired into `renderAll()`, which already calls `renderQuickTagRow()`/`renderTodaysWorkout()`/`renderPastWorkouts()` at the same point in its body.

---

### Task 1: Past Workouts always visible

**Files:**
- Modify: `gym.html` (HTML: replace the toggle button with a static label, remove the `display:none` gate; CSS: add a small static-label style; JS: remove the toggle's click handler)

**Interfaces:**
- Consumes: nothing (independent of Task 2)
- Produces: nothing consumed by Task 2 (both tasks touch unrelated regions of the same file)

- [ ] **Step 1: Add a static past-workouts label style**

In `gym.html`, find this block (currently lines 855-861, the end of the toggle-arrow rotation rule, just before `.po-tw-past-body`):

```css
.po-tw-past-toggle[aria-expanded="true"] .po-tw-past-arrow {
  transform: rotate(180deg);
}
.po-tw-past-body {
  margin-top: 6px;
  display: flex; flex-direction: column; gap: 6px;
}
```

Replace it with:

```css
.po-tw-past-toggle[aria-expanded="true"] .po-tw-past-arrow {
  transform: rotate(180deg);
}
.po-tw-past-label {
  margin-top: 10px;
  font-size: 12px; font-weight: 600; color: var(--text-2);
  letter-spacing: 0.04em;
}
.po-tw-past-body {
  margin-top: 6px;
  display: flex; flex-direction: column; gap: 6px;
}
```

(The `.po-tw-past-toggle`/`.po-tw-past-arrow` rules above this stay in the stylesheet as dead CSS — matching the precedent of leaving unused rules behind rather than editing unrelated regions of the file.)

- [ ] **Step 2: Replace the toggle button with a static label, remove the collapse**

In `gym.html`, find this exact block (currently lines 1609-1613):

```html
      <button type="button" class="po-tw-past-toggle" id="poTwPastToggle" aria-expanded="false">
        <span>Past workouts <span class="po-tw-past-count" id="poTwPastCount">0</span></span>
        <span class="po-tw-past-arrow" id="poTwPastArrow">▾</span>
      </button>
      <div class="po-tw-past-body" id="poTwPastBody" style="display:none"></div>
```

Replace it with:

```html
      <div class="po-tw-past-label">
        Past workouts <span class="po-tw-past-count" id="poTwPastCount">0</span>
      </div>
      <div class="po-tw-past-body" id="poTwPastBody"></div>
```

- [ ] **Step 3: Remove the toggle's click handler**

In `gym.html`, find this exact block:

```js
    saveDoneDays(doneDays);
    renderQuickTagRow();
    renderTodaysWorkout();
    renderPastWorkouts();
  });
  $('poTwPastToggle').addEventListener('click', () => {
    const body = $('poTwPastBody');
    const toggle = $('poTwPastToggle');
    const open = body.style.display !== 'none';
    body.style.display = open ? 'none' : 'flex';
    body.style.flexDirection = 'column';
    toggle.setAttribute('aria-expanded', open ? 'false' : 'true');
  });
```

Replace it with:

```js
    saveDoneDays(doneDays);
    renderQuickTagRow();
    renderTodaysWorkout();
    renderPastWorkouts();
  });
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
grep -c 'poTwPastToggle' gym.html
```
Expected: `0` (both the HTML id and the JS click-handler reference are gone)

- [ ] **Step 5: Manually verify in a browser**

Serve the directory (`python3 -m http.server 8123` from the repo root) and use Playwright MCP tools to navigate to `http://localhost:8123/gym.html` (or, if Playwright's Chromium binary is unavailable in this environment — a known issue seen throughout this project — fall back to curl-fetching the served HTML to confirm `#poTwPastBody` has no `style="display:none"` and no `#poTwPastToggle` button exists, reporting `DONE_WITH_CONCERNS`).

Confirm: Past Workouts renders immediately below Today's Workout with no click needed, showing "Past workouts N" as a plain (non-clickable) label above the list.

- [ ] **Step 6: Commit**

```bash
git add gym.html
git commit -m "$(cat <<'EOF'
Make Past Workouts always visible on Fitness page

Removes the collapse-by-default toggle — the list (already backed by
existing render logic) now renders inline like every other section on
the page, with a static label instead of an expand/collapse button.
EOF
)"
```

---

### Task 2: Inline progress-photos grid

**Files:**
- Modify: `gym.html` (HTML: replace the button + full-screen overlay shell with an in-flow section wrapping the same action buttons/file inputs/grid; JS: remove the button/overlay open-close handlers, wire `photosRender()` into `renderAll()`)

**Interfaces:**
- Consumes: `photosRender()` (gym.html:3069+, pre-existing, unchanged — reads the module-level `photos` array and populates `#wtPhotoGrid` and `#wtProgressCount`), `renderAll()` (pre-existing render orchestrator, this task adds one line to its body)
- Produces: nothing consumed by Task 1 (independent edits to unrelated regions of the same file)

- [ ] **Step 1: Replace the progress-photos button + overlay shell with an inline section**

In `gym.html`, find this exact block:

```html
    <button class="wt-progress-link" id="wtProgressLink" type="button" aria-label="Open progress photos">
      <div>
        <div class="wt-progress-label">PROGRESS PHOTOS</div>
        <div class="wt-progress-count" id="wtProgressCount">0 photos</div>
      </div>
      <span class="wt-progress-arrow">→</span>
    </button>
  </div>

  <!-- Progress photos overlay -->
  <div class="wt-overlay" id="wtOverlay" aria-hidden="true">
    <div class="wt-overlay-inner">
      <div class="wt-overlay-h">
        <button class="wt-back" id="wtBack" aria-label="Back">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
        </button>
        <div class="wt-overlay-title">Progress</div>
      </div>
      <div class="wt-overlay-actions">
        <button class="wt-overlay-action wt-overlay-primary" id="wtTakePhotoBtn">Take Photo</button>
        <button class="wt-overlay-action wt-overlay-secondary" id="wtFromLibraryBtn">From Library</button>
      </div>
      <input type="file" id="wtFileCamera" accept="image/*" capture="environment" style="display:none">
      <input type="file" id="wtFileLibrary" accept="image/*" style="display:none">
      <div class="wt-photo-grid" id="wtPhotoGrid">
        <div class="wt-photo-empty">No photos yet · tap Take Photo to start</div>
      </div>
    </div>
  </div>
```

Replace it with:

```html
  </div>

  <!-- Progress photos — inline grid, always visible. Tapping "Take Photo"
       still opens the full-screen camera (#wtCam), and tapping a photo
       still opens the full-screen viewer (#wtViewer) — both unchanged. -->
  <div class="po-sub-section">
    <div class="po-sub-title">Progress photos <span class="wt-progress-count" id="wtProgressCount">0 photos</span></div>
    <div class="wt-overlay-actions">
      <button class="wt-overlay-action wt-overlay-primary" id="wtTakePhotoBtn">Take Photo</button>
      <button class="wt-overlay-action wt-overlay-secondary" id="wtFromLibraryBtn">From Library</button>
    </div>
    <input type="file" id="wtFileCamera" accept="image/*" capture="environment" style="display:none">
    <input type="file" id="wtFileLibrary" accept="image/*" style="display:none">
    <div class="wt-photo-grid" id="wtPhotoGrid">
      <div class="wt-photo-empty">No photos yet · tap Take Photo to start</div>
    </div>
  </div>
```

Note: the leading `</div>` in the replacement is the SAME closing tag that was already there right after `</button>` in the original (closing the weight-tracker section's inner wrapper) — it is preserved, not new. Everything after it is new/relocated.

- [ ] **Step 2: Remove the button/overlay open-close handlers**

In `gym.html`, find this exact block:

```js
  function fileToPhoto(file) {
    const r = new FileReader();
    r.onload = (e) => photosAdd(e.target.result);
    r.readAsDataURL(file);
  }

  $('wtProgressLink').addEventListener('click', () => {
    photosRender();
    $('wtOverlay').classList.add('is-open');
    document.body.style.overflow = 'hidden';
  });
  $('wtBack').addEventListener('click', () => {
    $('wtOverlay').classList.remove('is-open');
    document.body.style.overflow = '';
  });

  // Take Photo: try in-browser camera, fall back to file input
```

Replace it with:

```js
  function fileToPhoto(file) {
    const r = new FileReader();
    r.onload = (e) => photosAdd(e.target.result);
    r.readAsDataURL(file);
  }

  // Take Photo: try in-browser camera, fall back to file input
```

- [ ] **Step 3: Wire `photosRender()` into `renderAll()`**

In `gym.html`, find this exact block:

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
    photosRender();
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
grep -c 'wtProgressLink\|wtOverlay\|wtBack\b' gym.html
```
Expected: `0` (the button, the overlay wrapper, and the back button are all fully removed — every reference gone from both HTML and JS)

```bash
grep -c 'id="wtProgressCount"\|id="wtTakePhotoBtn"\|id="wtFromLibraryBtn"\|id="wtFileCamera"\|id="wtFileLibrary"\|id="wtPhotoGrid"' gym.html
```
Expected: `6` (one occurrence of each id — these must still exist, just relocated)

- [ ] **Step 5: Manually verify in a browser**

Serve the directory and use Playwright MCP tools (or the curl/code-trace fallback from Task 1 Step 5 if Chromium is unavailable, reporting `DONE_WITH_CONCERNS`) to confirm:
- The "Progress photos" grid, "Take Photo," and "From Library" buttons render immediately on page load below the weight tracker — no click needed to reveal them
- If any photos already exist in `localStorage['po_coach_photos']`, they appear in the grid immediately (not just after a click)
- Clicking "Take Photo" still opens the full-screen camera exactly as before
- Clicking "From Library" still opens the file picker exactly as before
- Clicking an existing photo in the grid still opens the full-screen single-photo viewer exactly as before, including its Compare/Close/Delete actions

- [ ] **Step 6: Commit**

```bash
git add gym.html
git commit -m "$(cat <<'EOF'
Inline the progress-photos grid on the Fitness page

Removes the "PROGRESS PHOTOS" button and its full-screen slide-up
overlay — the photo grid and Take Photo/From Library buttons now
render directly in the page flow, always visible, wired into the
existing render cycle so photos show up immediately on page load.
The camera capture screen and the full-screen photo viewer/compare
tool are unchanged — only the browsing grid moved.
EOF
)"
```
