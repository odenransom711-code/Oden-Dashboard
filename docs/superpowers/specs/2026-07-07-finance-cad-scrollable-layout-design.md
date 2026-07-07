# Finance page: CAD default currency + single scrollable layout

## Context

Two small, related changes to `finance.html`, bundled together since both touch the same file and were requested together: (1) make CAD the default/main currency instead of CHF, (2) convert the page from a 5-tab switcher (Net Worth / Subs / Orders / Wishlist / Signals) into one continuous scrollable page with all sections always visible, with Signals repositioned to sit directly under Net Worth.

This is a detour from the in-progress stock-signals automation project (which was paused mid-brainstorm) — that resumes after this, using the new single-page layout instead of the tab structure it was originally scoped against.

No real financial data exists yet in this dashboard (confirmed with the user), so the currency change needs no data migration — it's a clean default swap.

## Design

### Currency: CHF → CAD

`CHF` appears only in `finance.html` (confirmed — no other page references it), in exactly these roles, all of which become `CAD`:
- 4 `<option value="CHF">CHF</option>` entries across the Net Worth, Subs, Orders, and Wishlist currency `<select>` elements (finance.html:1649, 1796, 1833, 1890) — since these are each the first-listed option and no explicit `selected` attribute exists anywhere, replacing the value/text with CAD makes CAD the browser's natural default-selected option with no JS changes needed.
- The `ccyOpts` array literal `['CHF','USD','EUR','GBP']` (finance.html:2723) used to build a currency `<select>`'s options dynamically for existing line-item rows.
- Every `'CHF'` fallback-default string literal used when a currency element isn't found or a stored item has no `entered_currency` recorded (finance.html:2039, 2081, 2463, 2590, 2718, 2797, 2909, 2939, 3251, 3278) — roughly a dozen occurrences, all conceptually "assume CAD if nothing else is specified."
- The hardcoded initial placeholder text `"CHF 0"` shown before any data loads (in `#netWorthTotal`, `#subsTotal`, `#wishTotal`).

**Left unchanged:** the `exchangeRates` object's internal handling and the `open.er-api.com/v6/latest/CHF` fetch URL. The API already returns a `data.rates.CAD` field in the same response (it returns rates for every supported currency, not just the four currently used) — no separate API call or URL change is needed, only using the field that's already present. Internal JS variable names like `amountCHF`, `deltaCHF`, `grandCHF` (used throughout the net-worth/subscriptions math as the invisible internal ledger unit) are **not** renamed — this is a purely cosmetic label never shown to the user, and a wide rename across ~1000+ lines of financial math carries real risk (typos, missed occurrences) for zero functional benefit. The math is currency-agnostic by construction: it already treats whichever currency has `exchangeRates[x] === 1` as the implicit base and converts every other currency relative to it; CAD slots in exactly like USD/EUR/GBP already do.

### Layout: tabs → one scrollable page

Currently, `finance.html`'s 5 sections (`data-section="net"`, `"subs"`, `"incoming"`, `"wish"`, `"signals"`) are toggled via a bottom tab bar (`<nav class="bottom-tabs">`, finance.html:1933-1954) and a `setActiveTab()` function (finance.html:1992-2003) that sets/removes a `hidden` attribute per section based on which tab was clicked, persisting the active tab to `localStorage['finance_active_tab']`.

Changes:
1. **Remove the bottom tab bar** (the entire `<nav class="bottom-tabs">...</nav>` block) and **remove the tab-switching JS** (`TAB_KEY`, the `tabs`/`sections` queries, `setActiveTab()`, its click-listener wiring, and the `savedTab`/whitelist initialization call) — none of this is needed once nothing is hidden.
2. **Remove the `hidden` attribute** from the Signals section's wrapping `<div>` (the only section that currently has one — it was added when Signals was built as a 5th tab).
3. **Move the Signals section** from its current position (after Wishlist, before the now-removed tab bar) to directly after Net Worth's closing `</div>` and before the `<!-- ===== ACTIVE SUBSCRIPTIONS ===== -->` comment — so the final section order top-to-bottom is: Net Worth, Signals, Subscriptions, Orders, Wishlist.
4. **`data-section="..."` attributes stay** on each section `<div>` — existing CSS (e.g. `[data-section="subs"] .quick-add { ... }`, finance.html:1366-1400) selects on them and would break if removed. Only the JS that *toggles visibility* based on them is removed, not the attributes themselves.

No other page behavior changes — every section's own internal logic (add/edit/delete items, charts, the Signals render function, cloud sync) is untouched; this is purely a "stop hiding sections, reorder one of them" change plus the currency default swap.

## Testing

No automated test framework exists in this repo. Verification is manual: load the page and confirm all 5 sections render simultaneously in the order Net Worth → Signals → Subscriptions → Orders → Wishlist with no tab bar and no scroll-jumping; confirm every currency `<select>` on the page defaults to CAD with no saved preference, and that CAD appears correctly in the dropdown option list alongside USD/EUR/GBP (no CHF anywhere); confirm adding a net-worth or subscription item while CAD is selected stores and displays a sane amount (no NaN, no wildly wrong conversion); confirm the existing Signals section (and its "Refresh now" affordance, once built) still renders/functions correctly in its new position.
