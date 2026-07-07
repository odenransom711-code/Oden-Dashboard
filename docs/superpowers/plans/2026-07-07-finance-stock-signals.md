# Finance Stock Signals Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fifth "Signals" tab to `finance.html` that displays weekly options-trading signals from `stockpicks_v1` localStorage — a pure display feature, no add/edit UI, populated later by a separate automation project.

**Architecture:** Extend `finance.html`'s existing 4-tab bottom-nav pattern (`net`/`subs`/`incoming`/`wish`) with a 5th tab (`signals`), reusing the page's existing `storeGet`/`escapeHtml` helpers and `.card`/`.wish-empty-*` CSS classes rather than introducing new ones where equivalents already exist. Cloud sync uses its own dedicated `appKey: 'stockpicks'` (a second, isolated `initCloudSync` registration on top of the page's existing `appKey: 'finance'` one) so a future automation script can write to it without ever touching the user's manually-entered net-worth/subscriptions/wishlist data.

**Tech Stack:** Plain HTML/CSS/JS, matching `finance.html`'s existing conventions exactly (`const`/arrow functions, `storeGet`/`storeSet` localStorage helpers, `escapeHtml` for XSS-safe interpolation). No test framework exists in this repo.

## Global Constraints

- Data model: `stockpicks_v1` = `{ updatedAt: ISOString, regime: "BULL"|"BEAR"|"NEUTRAL", signals: [{rank, ticker, direction: "CALL"|"PUT", confidence, strike, expiration}] }`.
- Cloud sync: `appKey: 'stockpicks'` (confirmed unused — existing appKeys: `caffeine`, `finance`, `health`, `goals`, `template`, `school`, `calendar`), registered inside `document.addEventListener('DOMContentLoaded', ...)`, matching the page's own existing `appKey: 'finance'` registration pattern (finance.html:3383-3392) exactly — this codebase has a known bug class (found during a prior phase of this project) where a bare `if (window.initCloudSync)` check at top-level script-execution time silently never fires because it runs before the deferred `sync.js` loads; the `DOMContentLoaded` wrapper avoids it.
- This page never writes to `stockpicks_v1` — no add/edit form exists for it in this plan. It's a one-way feed: whatever a future automation pushes to Supabase is what gets displayed.
- Staleness: if `updatedAt` is more than 9 days old, show the data but visually flag it as stale rather than hiding it.
- Reuse existing classes where they already do the job: `.card` for the card wrapper, `.wish-empty-card`/`.wish-empty-icon`/`.wish-empty-title`/`.wish-empty-sub` for the empty state, `.section-title`/`.section-title-text` for the heading, `--success`/`--danger`/`--text-tertiary`/`--font-mono` design tokens for CALL/PUT/regime coloring.

---

### Task 1: Add the Signals tab (CSS, HTML, JS)

**Files:**
- Modify: `finance.html` (CSS: add `.sig-*` rules; HTML: add tab button, section, and whitelist entry; JS: add `renderSignals()` inside the existing IIFE, expose it on `window`, and register its own `initCloudSync` call)

**Interfaces:**
- Consumes: `storeGet(key)` (finance.html's existing localStorage-JSON-parse helper), `escapeHtml(s)` (finance.html:2443), the existing tab-switching mechanism (`.bot-tab`/`.section[data-section]`/`TAB_KEY` whitelist array)
- Produces: nothing consumed elsewhere in this plan (only task)

- [ ] **Step 1: Add Signals CSS**

In `finance.html`, find this block (currently lines 1011-1016):

```css
.wish-empty-sub {
  font-size: 12px; color: var(--text-tertiary);
  line-height: 1.5; max-width: 320px; margin: 0 auto;
}

/* ===== Wishlist rows ===== */
```

Replace it with:

```css
.wish-empty-sub {
  font-size: 12px; color: var(--text-tertiary);
  line-height: 1.5; max-width: 320px; margin: 0 auto;
}

/* ===== Stock Signals ===== */
.sig-meta-row {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 14px; flex-wrap: wrap;
}
.sig-meta-updated {
  font-size: 11px; color: var(--text-tertiary);
  font-family: var(--font-mono);
}
.sig-meta-updated.stale { color: var(--warning); }
.sig-regime-badge {
  font-size: 10px; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase;
  padding: 5px 10px; border-radius: 999px;
  font-family: var(--font-mono);
}
.sig-regime-badge.bull { background: rgba(107,227,164,0.14); color: var(--success); }
.sig-regime-badge.bear { background: rgba(255,107,107,0.14); color: var(--danger); }
.sig-regime-badge.neutral { background: rgba(255,255,255,0.06); color: var(--text-tertiary); }
.sig-card {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 16px; margin-bottom: 8px;
}
.sig-rank {
  font-family: var(--font-mono); font-size: 13px; font-weight: 700;
  color: var(--text-tertiary); width: 20px; flex-shrink: 0;
}
.sig-body { flex: 1; min-width: 0; }
.sig-ticker { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.sig-detail {
  font-size: 11.5px; color: var(--text-tertiary); margin-top: 2px;
  font-family: var(--font-mono);
}
.sig-direction {
  font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase;
  padding: 5px 10px; border-radius: 8px; flex-shrink: 0;
}
.sig-direction.call { background: rgba(107,227,164,0.14); color: var(--success); }
.sig-direction.put { background: rgba(255,107,107,0.14); color: var(--danger); }
.sig-confidence {
  font-family: var(--font-mono); font-size: 20px; font-weight: 700;
  color: var(--text-primary); flex-shrink: 0; min-width: 46px; text-align: right;
}

/* ===== Wishlist rows ===== */
```

- [ ] **Step 2: Add the Signals tab button and section HTML**

In `finance.html`, find this block (currently lines 1861-1889):

```html
  <div id="wishList"></div>
  <div class="wish-empty-card" id="wishEmpty">
    <div class="wish-empty-icon">🎯</div>
    <div class="wish-empty-title">No wishes yet</div>
    <div class="wish-empty-sub">Add anything you're saving for — the dashboard will calculate what % of your net worth it'd cost.</div>
  </div>
</div>

</div>

<!-- ===== BOTTOM TAB BAR ===== -->
<nav class="bottom-tabs" id="bottomTabs" aria-label="Sections">
  <button class="bot-tab active" data-tab="net">
    <span class="bot-tab-icon">📊</span>
    <span class="bot-tab-label">Net Worth</span>
  </button>
  <button class="bot-tab" data-tab="subs">
    <span class="bot-tab-icon">🔁</span>
    <span class="bot-tab-label">Subs</span>
  </button>
  <button class="bot-tab" data-tab="incoming">
    <span class="bot-tab-icon">📦</span>
    <span class="bot-tab-label">Orders</span>
  </button>
  <button class="bot-tab" data-tab="wish">
    <span class="bot-tab-icon">🎯</span>
    <span class="bot-tab-label">Wishlist</span>
  </button>
</nav>
```

Replace it with:

```html
  <div id="wishList"></div>
  <div class="wish-empty-card" id="wishEmpty">
    <div class="wish-empty-icon">🎯</div>
    <div class="wish-empty-title">No wishes yet</div>
    <div class="wish-empty-sub">Add anything you're saving for — the dashboard will calculate what % of your net worth it'd cost.</div>
  </div>
</div>

<div class="section" data-section="signals" hidden>
  <div class="section-title">
    <span class="section-title-text">STOCK SIGNALS</span>
  </div>

  <div class="sig-meta-row">
    <span class="sig-meta-updated" id="sigUpdated">—</span>
    <span class="sig-regime-badge" id="sigRegime" style="display:none"></span>
  </div>

  <div id="sigList"></div>
  <div class="wish-empty-card" id="sigEmpty">
    <div class="wish-empty-icon">📈</div>
    <div class="wish-empty-title">No signals yet</div>
    <div class="wish-empty-sub">This fills in automatically once the weekly options scan runs — check back Monday.</div>
  </div>
</div>

</div>

<!-- ===== BOTTOM TAB BAR ===== -->
<nav class="bottom-tabs" id="bottomTabs" aria-label="Sections">
  <button class="bot-tab active" data-tab="net">
    <span class="bot-tab-icon">📊</span>
    <span class="bot-tab-label">Net Worth</span>
  </button>
  <button class="bot-tab" data-tab="subs">
    <span class="bot-tab-icon">🔁</span>
    <span class="bot-tab-label">Subs</span>
  </button>
  <button class="bot-tab" data-tab="incoming">
    <span class="bot-tab-icon">📦</span>
    <span class="bot-tab-label">Orders</span>
  </button>
  <button class="bot-tab" data-tab="wish">
    <span class="bot-tab-icon">🎯</span>
    <span class="bot-tab-label">Wishlist</span>
  </button>
  <button class="bot-tab" data-tab="signals">
    <span class="bot-tab-icon">📈</span>
    <span class="bot-tab-label">Signals</span>
  </button>
</nav>
```

- [ ] **Step 3: Add `signals` to the tab whitelist**

In `finance.html`, find this line (currently line 1938):

```js
  setActiveTab(savedTab && ['net','subs','incoming','wish'].includes(savedTab) ? savedTab : 'net');
```

Replace it with:

```js
  setActiveTab(savedTab && ['net','subs','incoming','wish','signals'].includes(savedTab) ? savedTab : 'net');
```

- [ ] **Step 4: Add `renderSignals()` to the main IIFE and expose it on `window`**

In `finance.html`, find this block (the tail of the main IIFE, currently lines 3374-3380):

```js
  function safeRenderTicker() {
    try { renderTicker(); } catch (e) { console.error('ticker render failed', e); }
  }
  safeRenderTicker();
  setInterval(safeRenderTicker, 1500);

})();
```

Replace it with:

```js
  function safeRenderTicker() {
    try { renderTicker(); } catch (e) { console.error('ticker render failed', e); }
  }
  safeRenderTicker();
  setInterval(safeRenderTicker, 1500);

  // ============================================================
  // STOCK SIGNALS — pure display, no add/edit UI. Populated by a
  // separate weekly automation writing to the 'stockpicks_v1' key
  // under its own dedicated 'stockpicks' cloud-sync appKey.
  // ============================================================
  function formatSigUpdated(iso) {
    if (!iso) return null;
    const d = new Date(iso);
    if (isNaN(d.getTime())) return null;
    const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    let h = d.getHours();
    const ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12; if (h === 0) h = 12;
    const min = String(d.getMinutes()).padStart(2, '0');
    return days[d.getDay()] + ' ' + months[d.getMonth()] + ' ' + d.getDate() + ', ' + h + ':' + min + ' ' + ampm;
  }

  function renderSignals() {
    const state = storeGet('stockpicks_v1');
    const updatedEl = document.getElementById('sigUpdated');
    const regimeEl = document.getElementById('sigRegime');
    const listEl = document.getElementById('sigList');
    const emptyEl = document.getElementById('sigEmpty');
    if (!updatedEl || !regimeEl || !listEl || !emptyEl) return;

    if (!state || !Array.isArray(state.signals) || state.signals.length === 0) {
      updatedEl.textContent = '—';
      updatedEl.classList.remove('stale');
      regimeEl.style.display = 'none';
      listEl.innerHTML = '';
      emptyEl.style.display = '';
      return;
    }

    emptyEl.style.display = 'none';

    const formatted = formatSigUpdated(state.updatedAt);
    const ageMs = state.updatedAt ? (Date.now() - new Date(state.updatedAt).getTime()) : null;
    const isStale = ageMs != null && ageMs > 9 * 24 * 60 * 60 * 1000;
    updatedEl.textContent = formatted ? ('Last updated: ' + formatted + (isStale ? ' (stale)' : '')) : '—';
    updatedEl.classList.toggle('stale', isStale);

    if (state.regime) {
      const r = String(state.regime).toLowerCase();
      regimeEl.style.display = '';
      regimeEl.textContent = state.regime;
      regimeEl.className = 'sig-regime-badge ' + (r === 'bull' ? 'bull' : r === 'bear' ? 'bear' : 'neutral');
    } else {
      regimeEl.style.display = 'none';
    }

    listEl.innerHTML = state.signals.map(function (s) {
      const dirClass = String(s.direction).toLowerCase() === 'call' ? 'call' : 'put';
      const detailBits = [];
      if (s.strike != null) detailBits.push('Strike ' + s.strike);
      if (s.expiration) detailBits.push('Exp ' + s.expiration);
      return '' +
        '<div class="card sig-card">' +
          '<span class="sig-rank">#' + escapeHtml(String(s.rank != null ? s.rank : '')) + '</span>' +
          '<div class="sig-body">' +
            '<span class="sig-ticker">' + escapeHtml(s.ticker) + '</span>' +
            (detailBits.length ? '<div class="sig-detail">' + escapeHtml(detailBits.join(' · ')) + '</div>' : '') +
          '</div>' +
          '<span class="sig-direction ' + dirClass + '">' + escapeHtml(s.direction) + '</span>' +
          '<span class="sig-confidence">' + escapeHtml(String(s.confidence != null ? s.confidence : '—')) + '</span>' +
        '</div>';
    }).join('');
  }

  renderSignals();
  window.renderSignals = renderSignals;

})();
```

- [ ] **Step 5: Register the `stockpicks` cloud sync**

In `finance.html`, find this block (the end of the file):

```js
<script>
document.addEventListener('DOMContentLoaded', function () {
  if (typeof initCloudSync !== 'function') return;
  initCloudSync({
    appKey: 'finance',
    syncedKeys: ['subs', 'wishlist', 'incoming_orders', 'nw_currency', 'nw:activity', 'nw:history'],
    syncedPrefixes: ['nw:'],
    onApplied: function () {
      window.dispatchEvent(new Event('storage'));
    }
  });
});
</script>
```

Replace it with:

```js
<script>
document.addEventListener('DOMContentLoaded', function () {
  if (typeof initCloudSync !== 'function') return;
  initCloudSync({
    appKey: 'finance',
    syncedKeys: ['subs', 'wishlist', 'incoming_orders', 'nw_currency', 'nw:activity', 'nw:history'],
    syncedPrefixes: ['nw:'],
    onApplied: function () {
      window.dispatchEvent(new Event('storage'));
    }
  });
});
</script>

<script>
document.addEventListener('DOMContentLoaded', function () {
  if (typeof initCloudSync !== 'function') return;
  initCloudSync({
    appKey: 'stockpicks',
    syncedKeys: ['stockpicks_v1'],
    onApplied: function () {
      if (window.renderSignals) window.renderSignals();
    }
  });
});
</script>
```

- [ ] **Step 6: Verify the file is well-formed**

Run:
```bash
node -e "
var fs = require('fs');
var s = fs.readFileSync('finance.html', 'utf8');
var re = /<script>([\s\S]*?)<\/script>/g;
var m, count = 0;
while ((m = re.exec(s))) { new Function(m[1]); count++; }
console.log('checked', count, 'inline script blocks OK');
"
```
Expected: the command prints a count matching however many bare (no-`src`) `<script>` tags exist in `finance.html` after this change (this file had some number before this edit — this task adds exactly one new bare `<script>` block in Step 5; confirm the count increased by exactly 1 versus the pre-edit file, and that every block compiles with no syntax error).

- [ ] **Step 7: Manually verify in a browser**

Serve the directory (`python3 -m http.server 8123` from the repo root) and use Playwright MCP tools to navigate to `http://localhost:8123/finance.html`, then use `browser_evaluate` to seed test data before checking the render, e.g.:

```js
localStorage.setItem('stockpicks_v1', JSON.stringify({
  updatedAt: new Date().toISOString(),
  regime: 'BULL',
  signals: [
    { rank: 1, ticker: 'HD', direction: 'PUT', confidence: 72, strike: 385, expiration: '2026-07-17' },
    { rank: 2, ticker: 'NVDA', direction: 'CALL', confidence: 68, strike: 140, expiration: '2026-07-24' }
  ]
}));
```

then reload and click the "Signals" tab button (`[data-tab="signals"]`) to confirm:
- The Signals tab appears as a 5th tab in the bottom bar and switches correctly (other tabs hide, Signals section shows)
- With the seeded data above, two signal cards render: HD (red PUT badge, confidence 72, "Strike 385 · Exp Jul 17") and NVDA (green CALL badge, confidence 68)
- The meta row shows "Last updated: <today's formatted date/time>" and a green "BULL" badge
- Re-seed with `updatedAt` set to 10+ days ago (`new Date(Date.now() - 10*24*60*60*1000).toISOString()`) and confirm the updated-text turns the stale (amber) color and includes "(stale)"
- Clear `stockpicks_v1` (`localStorage.removeItem('stockpicks_v1')`) and reload — confirm the empty state ("No signals yet") renders instead of an empty/broken list

**If Playwright's Chromium binary is unavailable in this environment** (a known issue seen throughout this project), fall back to: curl-fetching the served HTML to confirm the new tab button, section, and script block exist with correct ids/classes, and manually trace `renderSignals()` against the three test scenarios above by reading the code. Report this fallback clearly and use `DONE_WITH_CONCERNS` if used.

- [ ] **Step 8: Commit**

```bash
git add finance.html
git commit -m "$(cat <<'EOF'
Add Stock Signals tab to Finance page

Displays weekly options-trading signals (ticker, CALL/PUT, confidence,
strike, expiration) from a new stockpicks_v1 localStorage key, synced
via its own dedicated 'stockpicks' cloud-sync appKey so a future
automation script can populate it without touching the user's own
finance data. No add/edit UI in this page — pure display, with a
staleness flag if the data is more than 9 days old.
EOF
)"
```
