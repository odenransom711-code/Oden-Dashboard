# Finance page: Stock Signals tab

## Context

The user wants to surface weekly options-trading signals from an external GitHub repo (`adv-andrew/mcmc-cuda-model` — a Monte Carlo/regime-switching options scanner, run via `python scripts/options_now.py`, MIT-licensed, not owned by this dashboard's user) on the Finance page.

This is the first of two sub-projects:
- **This spec** — the Finance page UI that displays whatever signal data exists, built and verified against manually-seeded test data.
- **Next spec (separate)** — the actual weekly automation: a scheduled routine that clones the repo, runs the script, parses its console output, and pushes structured results to the same backend this UI reads from.

Building the UI first, against manual test data, means there's something visually verifiable before the (more failure-prone, external-repo-dependent) automation piece exists.

### Why this shape

The upstream repo's `options_now.py` scans 49 tickers with 25,000 Monte Carlo simulations, filters by signal strength/slope/volatility thresholds, and prints its top 5 ranked results to console — each with a ticker, CALL/PUT direction, confidence score (0-100), strike price, and expiration date, plus an overall market regime (BULL/BEAR/NEUTRAL) derived from SPY. This spec's data model mirrors that shape exactly; it doesn't invent additional fields the source data doesn't have.

## Design

### Placement: new "Signals" tab

`finance.html` already organizes its content into four tabs via a bottom tab bar (`net`, `subs`, `incoming`, `wish` — finance.html:1873-1888, switching logic at finance.html:1925-1937). This adds a fifth, sibling tab: `signals`, with a 📈 icon, following the exact same pattern — a new `<button class="bot-tab" data-tab="signals">`, a new `<div class="section" data-section="signals">`, and `'signals'` added to the tab-switching whitelist array (finance.html:1937, currently `['net','subs','incoming','wish']`).

### Data model

New localStorage key `stockpicks_v1`:

```js
{
  updatedAt: "2026-07-06T13:04:00Z",   // ISO timestamp of the last successful automation run
  regime: "BULL",                       // "BULL" | "BEAR" | "NEUTRAL", from get_regime()
  signals: [
    {
      rank: 1,
      ticker: "HD",
      direction: "PUT",                 // "CALL" | "PUT"
      confidence: 72,                   // 0-100
      strike: 385,
      expiration: "2026-07-17"          // YYYY-MM-DD
    }
  ]
}
```

Synced via `window.initCloudSync({ appKey: 'stockpicks', syncedKeys: ['stockpicks_v1'], onApplied: renderSignals })` — `stockpicks` is confirmed unused (existing appKeys: `caffeine`, `finance`, `health`, `goals`, `template`, `school`, `calendar`). This page never writes to `stockpicks_v1` itself — no add/edit form exists for it — so in practice it's a one-way feed: whatever the (future) automation pushes to Supabase is what gets pulled down and rendered here.

### Layout

Inside the `signals` section:

1. **Meta row** — small eyebrow-style text (matching the page's existing `.wish-hero-eyebrow`-style typography): "Last updated: Mon Jul 6, 9:04 AM" (formatted from `updatedAt`, in the user's local time), plus a market-regime badge (BULL green / BEAR red / NEUTRAL neutral-gray, reusing `--success`/`--danger`/`--text-tertiary`). If `updatedAt` is more than 9 days old (meaning last Monday's automated run likely failed, since it's meant to run weekly), the meta row shows a "stale" warning state instead of hiding the data — old signals are still shown, just visibly flagged as outdated rather than silently presented as current.
2. **Signal list** — one card per signal (up to 5), each row showing: rank number, ticker (bold, large), a CALL/PUT badge (`--success` green for CALL, `--danger` red for PUT — consistent with how the rest of the page already uses these tokens for positive/negative states), and the confidence score as a large number. Strike price and expiration render as smaller secondary text beneath the ticker (e.g. "Strike 385 · Exp Jul 17").
3. **Empty state** — when `signals` is empty or the key doesn't exist yet, render the exact same visual pattern as the Wishlist tab's empty state (finance.html:996-1013: icon + title + subtext), reworded for this context ("No signals yet" / explaining that this fills in once the weekly scan runs).

### Error handling

None beyond the staleness flag described above — there's no user input to validate on this page (pure display), and a missing/malformed `stockpicks_v1` value falls back to the empty state via the same defensive `try { JSON.parse(...) } catch { return null }` pattern already used elsewhere in this codebase.

### Testing

No automated test framework exists in this repo. Verification is manual: seed `localStorage.setItem('stockpicks_v1', JSON.stringify({...}))` with representative test data (via browser devtools or Playwright's `browser_evaluate`, if available in the execution environment) covering: a normal populated state (5 signals, mixed CALL/PUT, recent `updatedAt`), a stale-data state (`updatedAt` >9 days old), and an empty/missing-key state — confirm each renders correctly and matches the page's existing visual language (card styling, color tokens, typography).
