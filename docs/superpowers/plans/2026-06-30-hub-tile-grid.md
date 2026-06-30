# Hub Tile Grid Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the now-redundant Water/Caffeine hub tiles, add a School tile, and make all remaining tiles uniform size on a 3-column desktop grid.

**Architecture:** Pure HTML/CSS edit to `index.html` — no JS, no data model changes, no new files. The bento grid's tile markup and its supporting CSS (tile sizing, grid columns, responsive breakpoints) are edited together since they change in lockstep.

**Tech Stack:** Plain HTML/CSS, matching the rest of the codebase. No test framework exists in this repo.

## Global Constraints

- Final tile set, in order: Main 🏠 `#6BE3A4` → `main.html`, Fitness 💪 `#7DD3FC` → `gym.html`, Health 💊 `#A7F3D0` → `health.html`, Finance 📊 `#F2C063` → `finance.html`, Nova 🧠 `#A78BFA` → `nova-lite.html`, School 🎓 `#F472B6` → `school.html`.
- Water and Caffeine tiles are deleted outright, not just unlinked.
- All tiles are the same size — no `big`/`wide` class variants remain anywhere (CSS or markup).
- Desktop grid is `repeat(3, 1fr)` (was `repeat(4, 1fr)`) so 6 uniform tiles fill exactly 2 rows with no empty cells. Tablet (`repeat(2, 1fr)`) and mobile (`1fr`) breakpoints are unchanged in column count — only their now-dead `.tile.big`/`.tile.wide` override rules are removed.
- `tile-num` eyebrow labels are renumbered ·01 through ·06 to match the new order.

---

### Task 1: Remove Water/Caffeine tiles, add School tile, make all tiles uniform

**Files:**
- Modify: `index.html:63-138` (bento/tile CSS)
- Modify: `index.html:222-322` (bento tile markup)

**Interfaces:**
- Consumes: nothing (only task in this plan)
- Produces: nothing consumed elsewhere in this plan

- [ ] **Step 1: Update the bento/tile CSS — remove size variants, change grid to 3 columns**

In `index.html`, find this block (currently lines 63-138):

```css
.bento {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: 168px;
  grid-auto-flow: dense;
  gap: 14px;
}
.tile {
  --accent: #6BE3A4;                 /* each tile overrides this */
  position: relative; overflow: hidden;
  display: flex; flex-direction: column;
  padding: 20px;
  border-radius: 18px;
  text-decoration: none;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  backdrop-filter: blur(24px) saturate(1.2);
  -webkit-backdrop-filter: blur(24px) saturate(1.2);
  box-shadow: 0 12px 40px rgba(0,0,0,0.45);
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}
/* The "its own style" bit — a faint accent glow per tile. */
.tile::before {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(circle at 78% 18%,
              color-mix(in srgb, var(--accent) 22%, transparent), transparent 55%);
  opacity: 0.7; transition: opacity 0.18s ease;
}
.tile:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--accent) 40%, transparent);
  box-shadow: 0 16px 48px rgba(0,0,0,0.55);
}
.tile:hover::before { opacity: 1; }

/* Tile sizes */
.tile.big  { grid-column: span 2; grid-row: span 2; }
.tile.wide { grid-column: span 2; }

/* Tile contents */
.tile-top { display: flex; align-items: flex-start; justify-content: space-between; }
.tile-num {
  font-family: var(--font-mono); font-size: 12px; font-weight: 600;
  letter-spacing: 0.08em; color: var(--text-tertiary);
}
.tile-emoji {
  font-size: 26px; line-height: 1;
  filter: drop-shadow(0 0 10px color-mix(in srgb, var(--accent) 60%, transparent));
}
.tile-spacer { flex: 1; }
.tile-title {
  font-size: 22px; font-weight: 700; letter-spacing: -0.02em;
  color: var(--text-primary); margin: 0 0 4px;
}
.tile.big .tile-title { font-size: 28px; }
.tile-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.tile-sub {
  font-size: 13px; color: var(--text-tertiary);
}
.tile-arrow {
  font-size: 18px; color: var(--accent);
  transition: transform 0.18s ease; flex-shrink: 0;
}
.tile:hover .tile-arrow { transform: translateX(4px); }

/* ===== Responsive: collapse the bento on small screens ===== */
@media (max-width: 720px) {
  .bento { grid-template-columns: repeat(2, 1fr); grid-auto-rows: 150px; }
  .tile.big { grid-column: span 2; grid-row: span 1; }
  .tile.big .tile-title { font-size: 22px; }
}
@media (max-width: 440px) {
  body { padding: max(20px, env(safe-area-inset-top)) 14px 50px; }
  .bento { grid-template-columns: 1fr; grid-auto-rows: 132px; }
  .tile.big, .tile.wide { grid-column: span 1; }
}
```

Replace it with:

```css
.bento {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: 168px;
  grid-auto-flow: dense;
  gap: 14px;
}
.tile {
  --accent: #6BE3A4;                 /* each tile overrides this */
  position: relative; overflow: hidden;
  display: flex; flex-direction: column;
  padding: 20px;
  border-radius: 18px;
  text-decoration: none;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  backdrop-filter: blur(24px) saturate(1.2);
  -webkit-backdrop-filter: blur(24px) saturate(1.2);
  box-shadow: 0 12px 40px rgba(0,0,0,0.45);
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}
/* The "its own style" bit — a faint accent glow per tile. */
.tile::before {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(circle at 78% 18%,
              color-mix(in srgb, var(--accent) 22%, transparent), transparent 55%);
  opacity: 0.7; transition: opacity 0.18s ease;
}
.tile:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--accent) 40%, transparent);
  box-shadow: 0 16px 48px rgba(0,0,0,0.55);
}
.tile:hover::before { opacity: 1; }

/* Tile contents */
.tile-top { display: flex; align-items: flex-start; justify-content: space-between; }
.tile-num {
  font-family: var(--font-mono); font-size: 12px; font-weight: 600;
  letter-spacing: 0.08em; color: var(--text-tertiary);
}
.tile-emoji {
  font-size: 26px; line-height: 1;
  filter: drop-shadow(0 0 10px color-mix(in srgb, var(--accent) 60%, transparent));
}
.tile-spacer { flex: 1; }
.tile-title {
  font-size: 22px; font-weight: 700; letter-spacing: -0.02em;
  color: var(--text-primary); margin: 0 0 4px;
}
.tile-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.tile-sub {
  font-size: 13px; color: var(--text-tertiary);
}
.tile-arrow {
  font-size: 18px; color: var(--accent);
  transition: transform 0.18s ease; flex-shrink: 0;
}
.tile:hover .tile-arrow { transform: translateX(4px); }

/* ===== Responsive: collapse the bento on small screens ===== */
@media (max-width: 720px) {
  .bento { grid-template-columns: repeat(2, 1fr); grid-auto-rows: 150px; }
}
@media (max-width: 440px) {
  body { padding: max(20px, env(safe-area-inset-top)) 14px 50px; }
  .bento { grid-template-columns: 1fr; grid-auto-rows: 132px; }
}
```

- [ ] **Step 2: Replace the bento tile markup — drop Water/Caffeine, add School, drop size classes**

In `index.html`, find this block (currently lines 222-322):

```html
  <div class="bento">

    <!-- Big tile -->
    <a class="tile big" href="main.html" style="--accent:#6BE3A4">
      <div class="tile-top">
        <span class="tile-num">·01</span>
        <span class="tile-emoji">🏠</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Main</h2>
      <div class="tile-foot">
        <span class="tile-sub">Goals & daily plan</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

    <!-- Wide tile -->
    <a class="tile wide" href="gym.html" style="--accent:#7DD3FC">
      <div class="tile-top">
        <span class="tile-num">·02</span>
        <span class="tile-emoji">💪</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Fitness</h2>
      <div class="tile-foot">
        <span class="tile-sub">Workouts, splits, sessions</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

    <!-- Small tile -->
    <a class="tile" href="health.html" style="--accent:#A7F3D0">
      <div class="tile-top">
        <span class="tile-num">·03</span>
        <span class="tile-emoji">💊</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Health</h2>
      <div class="tile-foot">
        <span class="tile-sub">Supplements & vitals</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

    <!-- Small tile -->
    <a class="tile" href="po-water.html" style="--accent:#60A5FA">
      <div class="tile-top">
        <span class="tile-num">·04</span>
        <span class="tile-emoji">💧</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Water</h2>
      <div class="tile-foot">
        <span class="tile-sub">Hydration</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

    <!-- Wide tile -->
    <a class="tile wide" href="finance.html" style="--accent:#F2C063">
      <div class="tile-top">
        <span class="tile-num">·05</span>
        <span class="tile-emoji">📊</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Finance</h2>
      <div class="tile-foot">
        <span class="tile-sub">Net worth & spending</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

    <!-- Small tile -->
    <a class="tile" href="caffeine.html" style="--accent:#C9A36B">
      <div class="tile-top">
        <span class="tile-num">·06</span>
        <span class="tile-emoji">☕</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Caffeine</h2>
      <div class="tile-foot">
        <span class="tile-sub">Intake & timing</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

    <!-- Wide tile -->
    <a class="tile wide" href="nova-lite.html" style="--accent:#A78BFA">
      <div class="tile-top">
        <span class="tile-num">·07</span>
        <span class="tile-emoji">🧠</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Nova</h2>
      <div class="tile-foot">
        <span class="tile-sub">Your AI mentor</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

  </div>
```

Replace it with:

```html
  <div class="bento">

    <a class="tile" href="main.html" style="--accent:#6BE3A4">
      <div class="tile-top">
        <span class="tile-num">·01</span>
        <span class="tile-emoji">🏠</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Main</h2>
      <div class="tile-foot">
        <span class="tile-sub">Goals & daily plan</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

    <a class="tile" href="gym.html" style="--accent:#7DD3FC">
      <div class="tile-top">
        <span class="tile-num">·02</span>
        <span class="tile-emoji">💪</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Fitness</h2>
      <div class="tile-foot">
        <span class="tile-sub">Workouts, splits, sessions</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

    <a class="tile" href="health.html" style="--accent:#A7F3D0">
      <div class="tile-top">
        <span class="tile-num">·03</span>
        <span class="tile-emoji">💊</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Health</h2>
      <div class="tile-foot">
        <span class="tile-sub">Supplements & vitals</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

    <a class="tile" href="finance.html" style="--accent:#F2C063">
      <div class="tile-top">
        <span class="tile-num">·04</span>
        <span class="tile-emoji">📊</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Finance</h2>
      <div class="tile-foot">
        <span class="tile-sub">Net worth & spending</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

    <a class="tile" href="nova-lite.html" style="--accent:#A78BFA">
      <div class="tile-top">
        <span class="tile-num">·05</span>
        <span class="tile-emoji">🧠</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">Nova</h2>
      <div class="tile-foot">
        <span class="tile-sub">Your AI mentor</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

    <a class="tile" href="school.html" style="--accent:#F472B6">
      <div class="tile-top">
        <span class="tile-num">·06</span>
        <span class="tile-emoji">🎓</span>
      </div>
      <div class="tile-spacer"></div>
      <h2 class="tile-title">School</h2>
      <div class="tile-foot">
        <span class="tile-sub">Classes, grades & deadlines</span>
        <span class="tile-arrow">→</span>
      </div>
    </a>

  </div>
```

- [ ] **Step 3: Verify the file is well-formed**

Run: `python3 -c "import re; s=open('index.html').read(); print('tile count:', s.count('class=\"tile\"')); print('big/wide remnants:', s.count('tile big'), s.count('tile wide'))"`
Expected: `tile count: 6` and `big/wide remnants: 0 0`

- [ ] **Step 4: Manually verify in a browser**

Run: `python3 -m http.server 8123` from the repo root, then use Playwright MCP tools to navigate to `http://localhost:8123/index.html` and take a snapshot/screenshot (or, if Playwright's Chromium binary is unavailable in this environment — a known issue — fall back to: curl-fetching the page to confirm exactly 6 `<a class="tile"` elements exist with hrefs `main.html`, `gym.html`, `health.html`, `finance.html`, `nova-lite.html`, `school.html` in that order, and confirm `po-water.html`/`caffeine.html` no longer appear anywhere in the file; report this fallback clearly and use `DONE_WITH_CONCERNS` if used).

Expected, if visual verification is possible: 6 equally-sized tiles arranged 3 per row (Main, Fitness, Health / Finance, Nova, School), each tile the same height, the School tile showing a 🎓 icon in pink. Resize to ≤720px width and confirm it collapses to a 2-column, 3-row layout with tiles still uniform size. Resize to ≤440px and confirm a single column.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "$(cat <<'EOF'
Clean up hub tile grid: drop Water/Caffeine, add School, uniform sizing

Phase 3a of the dashboard redesign. Water and Caffeine tracking moved
into Health in phase 1; their hub tiles are now redundant. All 6
remaining tiles (Main, Fitness, Health, Finance, Nova, School) are
uniform size on a 3-column grid instead of mixed big/wide sizing.
EOF
)"
```
