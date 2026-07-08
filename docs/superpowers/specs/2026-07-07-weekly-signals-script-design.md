# Weekly signals scan script (`scripts/weekly_signals.py`)

## Context

This is phase (a) of a 3-phase automation project that feeds the Finance page's "Stock Signals" section (already built, shipped, reads `stockpicks_v1` from localStorage synced via a dedicated `stockpicks` Supabase `app_state` row). The other two phases — a local helper server exposing this logic over HTTP, and the actual weekly-scheduled trigger + a "Refresh now" UI button — build on top of this script and are out of scope here.

The upstream repo (`adv-andrew/mcmc-cuda-model`, MIT-licensed, public, not owned by this dashboard's user) runs a Monte Carlo options-signal scanner via `python scripts/options_now.py`. It has no CLI args, no env vars, no API key requirement (`yfinance` is free/unauthenticated), and gracefully falls back to CPU (NumPy) when its optional GPU dependency (`cupy`) isn't installed — confirmed via its actual source (`try: import cupy ... except ImportError: cp = None`). It prints formatted results to stdout only; there's no JSON/CSV output to consume directly.

## Design

### What this script does, end to end

1. Clone the upstream repo fresh into a temp directory (`git clone --depth 1`) — never reused/cached, so each run gets the current version of the scanner with no local drift to manage.
2. Ensure a dedicated virtual environment exists at `~/.oden-dashboard-signals-venv` (created once, reused across runs) with exactly the CPU-needed dependencies installed: `numpy`, `pandas`, `yfinance`, `scipy`, `pytz`, `pyyaml`. Explicitly NOT installed: `cupy-cuda12x` (no GPU on this machine, and it would likely fail to install anyway), `torch`, `streamlit`, `optuna` — none are imported by `options_now.py`'s actual code path.
3. Run `options_now.py` from inside the freshly-cloned repo using that venv's Python, capturing stdout, with a 300-second timeout.
4. Parse the captured stdout into structured data (see below).
5. Build a JSON payload matching the Finance page's existing `stockpicks_v1` schema.
6. Push it to Supabase via a direct REST POST — the same `app_state` upsert endpoint and public/publishable credentials `sync.js` already uses client-side (no new secret needed; these are not sensitive, they're already embedded in the shipped dashboard).
7. Delete the temp clone directory (always, via a `finally` block — success or failure).

### Output parsing

The upstream script's exact print formats (confirmed against its actual source, not guessed):

```
REGIME:    {regime}
...
#{i} {ticker} {type} | Confidence: {confidence:.0f}/100 ({conf_label})
   Strike: ${strike:.0f} ATM | Exp: ~{Mon DD}
   Price: ...    ← ignored
   Strength: ... ← ignored
   5d: ...        ← ignored
```

Parsing rules:
- `REGIME:\s*(.+)` → normalize to `BULL`/`BEAR`/`NEUTRAL` by substring match on the captured text (case-insensitive); anything not matching BULL or BEAR becomes NEUTRAL.
- `^#(\d+)\s+(\S+)\s+(CALL|PUT)\s+\|\s+Confidence:\s+(\d+)/100` starts a new signal record: `{rank, ticker, direction, confidence}`.
- The following `Strike:\s*\$(\d+)\s+ATM\s+\|\s+Exp:\s*~(\w{3}\s+\d+)` line attaches `strike` and a parsed `expiration` to the current record.
- **No year is printed for the expiration date** — the script infers it: parse "Mon DD" against the current year; if that resulting date is strictly before today's date, assume it means next year instead (option expirations are always in the future, so a "past" date under the current-year assumption must actually be next year's occurrence of that month/day). Format the result as `YYYY-MM-DD` to match the Finance page's schema.
- All other detail lines (Price/Vol, Strength/Slope, 5d/20d momentum) are ignored — not needed by the Finance page's display.
- Zero parsed signals in a given week is a **valid, non-error outcome** (the scanner's confidence/slope/volatility thresholds may simply not be met by any of the 49 tracked tickers that week) — the script still pushes `{updatedAt, regime, signals: []}` rather than treating it as a failure.

### Success/failure criteria

A run is considered successful — and only then pushes to Supabase — if: the subprocess exits with code 0, AND a `REGIME:` line was found in its output. If either condition fails (non-zero exit, timeout, missing regime line, clone failure, or any unhandled exception), the script prints a clear error to stderr and exits non-zero **without pushing anything** — this preserves whatever data is already in Supabase from the last successful run rather than overwriting it with garbage or an empty/error state. (What happens *after* a failed run — retry logic, notifying the user — is the scheduled-trigger phase's responsibility, not this script's.)

### CLI interface

```
python scripts/weekly_signals.py [--dry-run]
```

`--dry-run` runs the full clone → scan → parse pipeline but prints the resulting JSON payload instead of pushing it to Supabase — useful for manual testing and for this plan's own verification steps without touching real production data.

### Data model (unchanged, already shipped)

```json
{
  "updatedAt": "2026-07-06T13:04:00Z",
  "regime": "BULL",
  "signals": [
    { "rank": 1, "ticker": "HD", "direction": "PUT", "confidence": 72, "strike": 385, "expiration": "2026-07-17" }
  ]
}
```
Pushed as `{"key": "stockpicks", "data": <above>, "updated_at": "<ISO now>"}` to `{SUPABASE_URL}/rest/v1/app_state?on_conflict=key` with `Prefer: resolution=merge-duplicates` — identical upsert shape to what `sync.js`'s `flushOnUnload` already does for every other page's cloud sync.

### Error handling

Every external-failure point (git clone, venv creation, pip install, subprocess run/timeout, HTTP push) is wrapped so a failure at any stage prints a specific, identifiable error message to stderr and exits non-zero — no bare/generic exceptions swallowed silently. Network calls (`yfinance` inside the upstream script, and this script's own Supabase push) are not retried internally; a failed run is simply a failed run, left for the caller to decide whether/when to retry.

### Testing

No automated test framework exists in this repo, and this script's core logic (subprocess orchestration, network calls) isn't easily unit-testable without mocking infrastructure this project doesn't have. Verification is manual: run `python scripts/weekly_signals.py --dry-run` and confirm the printed JSON has a sane `regime` and `signals` array matching what the upstream script actually printed to the terminal in the same run; deliberately break something (e.g. temporarily point the clone URL at a nonexistent repo) and confirm the script fails loudly with a non-zero exit and no Supabase push attempt.
