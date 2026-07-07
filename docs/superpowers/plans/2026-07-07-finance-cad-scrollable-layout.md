# Finance CAD Currency + Scrollable Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make CAD the default/selectable currency on the Finance page instead of CHF, and convert the page from a 5-tab switcher into one continuous scrollable page with Signals repositioned directly under Net Worth.

**Architecture:** Two independent, sequential edits to `finance.html`. Task 1 touches only user-facing currency strings (dropdown options, fallback defaults, placeholder text) — it deliberately does NOT rename internal JS identifiers like `amountCHF`/`deltaCHF`/`nwGrandCHF()` or the exchange-rate API's fetch URL, since those are cosmetic-only internal implementation details never shown to the user, and renaming them across ~40 locations in complex financial math would add real risk for zero functional benefit. Task 2 removes the tab-switching mechanism entirely and moves the Signals section's HTML block to a new position.

**Tech Stack:** Plain HTML/CSS/JS, matching `finance.html`'s existing conventions. No test framework exists in this repo.

## Global Constraints

- No data migration needed — confirmed no real financial data is currently stored, so this is a clean default swap, not a currency conversion of existing records.
- Only these CHF references become CAD: the 4 `<option value="CHF">CHF</option>` dropdown entries, the 3 hardcoded "CHF 0" placeholder texts, the 1 static "CHF" label span, and the 11 quoted `'CHF'` string-literal fallback defaults (including the one inside the `ccyOpts` array). **Every other occurrence of the substring "CHF" in this file — internal variable names (`amountCHF`, `curCHF`, `nextCHF`, `deltaCHF`, `annualSubsCHF`, `grandCHF`), the function name `nwGrandCHF()`, the stored object property key `amountCHF:`, code comments, the `exchangeRates` object's `CHF` key, and the `open.er-api.com/v6/latest/CHF` fetch URL — must NOT change.**
- The exchange-rate API already returns a `CAD` field in its response alongside `USD`/`EUR`/`GBP` — add it to the `exchangeRates` object, don't change the fetch URL or remove the existing `CHF` entry.
- After the layout change, final section order top-to-bottom must be: Net Worth, Signals, Subscriptions, Orders, Wishlist — with no `hidden` attributes anywhere and no tab bar.
- `data-section="..."` attributes on each section `<div>` must be preserved (existing CSS selectors depend on them, e.g. `[data-section="subs"] .quick-add`) — only the JS that toggles visibility based on them is removed.

---

### Task 1: Swap CHF for CAD in all user-facing currency strings

**Files:**
- Modify: `finance.html` (5 separate edits: 4 option tags, 3 placeholder texts, 1 label span, 11 quoted fallback literals, 2 additions to `exchangeRates`)

**Interfaces:**
- Consumes: nothing (independent of Task 2)
- Produces: nothing consumed by Task 2 (both tasks are independent edits to the same file, safe to apply in either order, but this plan does Task 1 first)

- [ ] **Step 1: Replace all 4 currency dropdown option tags**

In `finance.html`, using **replace_all**, find this exact text (appears identically 4 times, at what are currently lines 1649, 1796, 1833, 1890):

```html
<option value="CHF">CHF</option>
```

Replace every occurrence with:

```html
<option value="CAD">CAD</option>
```

- [ ] **Step 2: Replace all 3 "CHF 0" placeholder texts**

In `finance.html`, using **replace_all**, find this exact text (appears identically 3 times, inside `#netWorthTotal`, `#subsTotal`, and `#wishTotal`'s initial HTML):

```
CHF 0
```

Replace every occurrence with:

```
CAD 0
```

- [ ] **Step 3: Replace the static currency label span**

In `finance.html`, find this exact text (currently line 1647, appears once):

```html
<span style="font-size:11px;color:var(--text-tertiary)">CHF</span>
```

Replace it with:

```html
<span style="font-size:11px;color:var(--text-tertiary)">CAD</span>
```

- [ ] **Step 4: Replace all 11 quoted `'CHF'` fallback literals**

In `finance.html`, using **replace_all**, find this exact text (appears identically 11 times — as `currencyEl.value : 'CHF'`, `ccEl.value : 'CHF'`, `cEl.value : 'CHF'`, `ccyEl.value : 'CHF'`, `entered_currency || 'CHF'` twice, `entered_currency !== 'CHF'`, and as one element of the `['CHF','USD','EUR','GBP']` array literal):

```
'CHF'
```

Replace every occurrence with:

```
'CAD'
```

**Before running this step**, confirm the count is exactly 11: run `grep -o "'CHF'" finance.html | wc -l` and expect `11`. If the count is different, STOP and report — do not proceed with a mismatched count, since this is a whole-file `replace_all` and an unexpected count means something in the file differs from what this plan assumed.

- [ ] **Step 5: Add a CAD entry to the `exchangeRates` object**

In `finance.html`, find this exact block:

```js
  let exchangeRates = { CHF: 1, USD: 1, EUR: 1, GBP: 1 };
  async function loadExchangeRates() {
    try {
      const res = await fetch('https://open.er-api.com/v6/latest/CHF');
      const data = await res.json();
      if (data && data.rates) {
        exchangeRates = {
          CHF: 1,
          USD: data.rates.USD || 1,
          EUR: data.rates.EUR || 1,
          GBP: data.rates.GBP || 1
        };
        renderAllNetWorth();
        if (typeof renderSubs === 'function') renderSubs();
      }
    } catch (e) {}
  }
  loadExchangeRates();
```

Replace it with:

```js
  let exchangeRates = { CHF: 1, USD: 1, EUR: 1, GBP: 1, CAD: 1 };
  async function loadExchangeRates() {
    try {
      const res = await fetch('https://open.er-api.com/v6/latest/CHF');
      const data = await res.json();
      if (data && data.rates) {
        exchangeRates = {
          CHF: 1,
          USD: data.rates.USD || 1,
          EUR: data.rates.EUR || 1,
          GBP: data.rates.GBP || 1,
          CAD: data.rates.CAD || 1
        };
        renderAllNetWorth();
        if (typeof renderSubs === 'function') renderSubs();
      }
    } catch (e) {}
  }
  loadExchangeRates();
```

Note: the fetch URL stays `/latest/CHF` and the `CHF: 1` entries stay — this is intentional, not a mistake to fix. See the plan's Global Constraints.

- [ ] **Step 6: Verify the changes are scoped correctly**

Run each of these and confirm the exact expected output:

```bash
grep -c "'CHF'" finance.html
```
Expected: `0` (all 11 quoted literals became `'CAD'`)

```bash
grep -c '<option value="CHF">' finance.html
```
Expected: `0`

```bash
grep -c "CHF 0" finance.html
```
Expected: `0`

```bash
grep -c "amountCHF" finance.html
```
Expected: `19` (this identifier must be completely untouched by this task's edits — confirmed count in the file before this task begins)

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
Expected: `checked 3 inline script blocks OK` (this file has 3 bare `<script>` blocks — the main IIFE, and two trailing cloud-sync registrations for `appKey: 'finance'` and `appKey: 'stockpicks'`)

- [ ] **Step 7: Manually verify in a browser**

Serve the directory (`python3 -m http.server 8123` from the repo root) and use Playwright MCP tools to navigate to `http://localhost:8123/finance.html` (or, if Playwright's Chromium binary is unavailable in this environment — a known issue seen throughout this project — fall back to curl-fetching the page to confirm every `<option value="CAD">` and no remaining `value="CHF"` exists, and report `DONE_WITH_CONCERNS`).

Confirm: every currency `<select>` on the page (Net Worth, Subscriptions, Orders, Wishlist, and any per-item edit dropdowns) shows CAD as an option and as the default-selected value when no saved preference exists; adding a net-worth item while CAD is selected stores and re-displays a sane, non-NaN amount.

- [ ] **Step 8: Commit**

```bash
git add finance.html
git commit -m "$(cat <<'EOF'
Make CAD the default currency on the Finance page

Swaps CHF for CAD in every user-facing currency string (dropdown
options, fallback defaults, placeholder text) — no data migration
needed since no real financial data was stored yet. Internal JS
identifiers (amountCHF, nwGrandCHF, etc.) and the exchange-rate API's
CHF-based fetch are deliberately left unchanged as cosmetic-only
implementation details; the API already returns a CAD rate alongside
the others, which is now used.
EOF
)"
```

---

### Task 2: Convert Finance page from tabs to one scrollable page

**Files:**
- Modify: `finance.html` (move the Signals section's HTML block, remove the bottom tab bar, remove the tab-switching JS)

**Interfaces:**
- Consumes: nothing (independent of Task 1 — this task's find/replace blocks target text far from anything Task 1 touches, so order between the two tasks doesn't matter, though this plan does Task 1 first)
- Produces: nothing consumed elsewhere (last task in this plan)

- [ ] **Step 1: Move the Signals section — insert it after Net Worth**

In `finance.html`, find this exact block (the end of the Net Worth section, currently lines 1770-1777):

```html
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ===== ACTIVE SUBSCRIPTIONS ===== -->
<div class="section" data-section="subs">
```

Replace it with:

```html
        </div>
      </div>
    </div>
  </div>
</div>

<div class="section" data-section="signals">
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

<!-- ===== ACTIVE SUBSCRIPTIONS ===== -->
<div class="section" data-section="subs">
```

Note the new Signals section here has NO `hidden` attribute (the version being removed in Step 2 has one — don't carry it over, since nothing hides sections anymore after this task).

- [ ] **Step 2: Remove the Signals section from its old location**

In `finance.html`, find this exact block (the end of the Wishlist section followed by the old Signals section, currently lines 1909-1930):

```html
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
```

Replace it with:

```html
  </div>
</div>

</div>
```

(This removes the duplicate/old Signals block entirely, leaving Wishlist's closing `</div>` and the outer wrapper's closing `</div>` adjacent, exactly as they were before Signals was ever inserted here.)

- [ ] **Step 3: Remove the bottom tab bar**

In `finance.html`, find this exact block:

```html
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

<script>
```

Replace it with:

```html
<script>
```

- [ ] **Step 4: Remove the tab-switching JS**

In `finance.html`, find this exact block:

```js
  // ============================================================
  // BOTTOM TABS — switch between Net Worth / Subs / Orders.
  // Active tab persisted in localStorage.
  // ============================================================
  const TAB_KEY = 'finance_active_tab';
  const tabs = document.querySelectorAll('.bot-tab');
  const sections = document.querySelectorAll('.section[data-section]');
  function setActiveTab(name) {
    tabs.forEach(b => b.classList.toggle('active', b.dataset.tab === name));
    sections.forEach(s => {
      if (s.dataset.section === name) s.removeAttribute('hidden');
      else s.setAttribute('hidden', '');
    });
    storeSet(TAB_KEY, name);
    window.scrollTo({ top: 0, behavior: 'instant' });
  }
  tabs.forEach(b => b.addEventListener('click', () => setActiveTab(b.dataset.tab)));
  const savedTab = storeGet(TAB_KEY);
  setActiveTab(savedTab && ['net','subs','incoming','wish','signals'].includes(savedTab) ? savedTab : 'net');

  // ============================================================
  // NET WORTH (copied from the main dashboard, verbatim logic)
  // ============================================================
```

Replace it with:

```js
  // ============================================================
  // NET WORTH (copied from the main dashboard, verbatim logic)
  // ============================================================
```

- [ ] **Step 5: Verify the file is well-formed**

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
Expected: `checked 3 inline script blocks OK`

Also run:
```bash
grep -c 'data-section=' finance.html
```
Expected: `5` (one per section: net, signals, subs, incoming, wish — all still present, just no longer toggled)

```bash
grep -c 'bottom-tabs\|bot-tab\|setActiveTab\|TAB_KEY' finance.html
```
Expected: `0` (confirms the tab bar and its JS are fully removed)

```bash
grep -c 'hidden' finance.html
```
Expected: `0` (no section should have a `hidden` attribute left)

- [ ] **Step 6: Manually verify in a browser**

Serve the directory and use Playwright MCP tools to navigate to `http://localhost:8123/finance.html` (or the curl fallback from Task 1 Step 7 if Chromium is unavailable, reporting `DONE_WITH_CONCERNS`).

Confirm: no tab bar renders at the bottom of the page; scrolling down the page shows, in order, Net Worth, Stock Signals, Active Subscriptions, Incoming Orders, and Wishlist, all visible simultaneously with no clicking required; the Signals section's existing "No signals yet" empty state (or seeded test data from the earlier Finance Signals task, if still present in localStorage) still renders correctly in its new position; each section's own interactive features (adding a net-worth item, adding a subscription, etc.) still work exactly as before.

- [ ] **Step 7: Commit**

```bash
git add finance.html
git commit -m "$(cat <<'EOF'
Convert Finance page from tabs to one scrollable page

Removes the bottom tab bar and tab-switching JS entirely — all
sections (Net Worth, Signals, Subscriptions, Orders, Wishlist) now
render simultaneously in one continuous scroll, with Signals moved
to sit directly under Net Worth per request.
EOF
)"
```
