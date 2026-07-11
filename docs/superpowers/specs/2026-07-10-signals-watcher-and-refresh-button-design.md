# Signals watcher + "Refresh now" button

## Context

`scripts/weekly_signals.py` (shipped, phase (a) of this automation project) clones the upstream `mcmc-cuda-model` repo, runs its options scanner in a dedicated venv, parses the output, and pushes `{updatedAt, regime, signals}` to Supabase's `stockpicks` row — which the Finance page's Stock Signals section already reads and renders. This is phase (b) and (c): getting that script to actually run on a schedule, and letting the user manually trigger a run from the dashboard.

The dashboard is a static site deployed on Vercel and used from multiple devices (phone, other computers), but `weekly_signals.py` can only run on the user's own Mac — it needs a real filesystem, git, and a Python venv, none of which a Vercel serverless function can provide. This creates a genuine architecture question: how does a button on a publicly-hosted, cross-device site reach a script that only runs on one specific machine?

## Design

### Architecture

Two new pieces on top of the already-shipped `weekly_signals.py`:

- **`scripts/signals_watcher.py`** — a lightweight script that macOS's `launchd` wakes every 15 minutes. It does one cheap Supabase read, then decides whether to run the full (~1-2 min) scan by shelling out to `python3 weekly_signals.py` as a subprocess (clean crash isolation, reuses that script's existing success/failure handling as-is, no changes to `weekly_signals.py` needed).
- **A launchd LaunchAgent** — runs as the user (no sudo), starts at login, stops at logout. Not a LaunchDaemon: this is a personal script on a personal Mac, and a LaunchAgent needs no elevated privileges to install. `signals_watcher.py --install` writes the plist to `~/Library/LaunchAgents` and loads it via `launchctl`; `--uninstall` reverses this.
- **Finance page changes**: a "Refresh now" button in the Stock Signals section that requests a scan via Supabase (the same backend every other cross-device feature in this dashboard already uses), plus a status line reflecting whether a request is pending, fulfilled, or possibly stuck.

This deliberately avoids exposing any local server to the internet, and avoids running two separate systems (a weekly cron-like job and a separate always-on HTTP server) — one watcher, woken periodically, handles both the scheduled and the manual trigger paths through the same due-check logic.

### Data flow

One new Supabase `app_state` row: `key: 'stockpicks_refresh'`, `data: {requestedAt: ISOString}`. Same table, same public/publishable credentials already embedded in `sync.js` — no new secret, no new backend.

`signals_watcher.py`'s due-check, run every 15 minutes:

```
state     = GET stockpicks row from Supabase          (missing → treat as never-run)
refreshReq = GET stockpicks_refresh row from Supabase  (missing → no pending request)
now_et    = current time converted to America/New_York (via stdlib zoneinfo, independent
            of the Mac's system timezone)

weeklyDue = now_et.weekday() == Monday
            and 9:30 <= now_et.time() < 9:45
            and (state.updatedAt is missing OR state.updatedAt is before this week's
                 Monday 9:30 ET)

manualDue = refreshReq.requestedAt exists
            and (state.updatedAt is missing OR refreshReq.requestedAt > state.updatedAt)

if weeklyDue or manualDue:
    acquire lock, run `python3 weekly_signals.py` as a subprocess, release lock
```

On success, `weekly_signals.py` already pushes a fresh `stockpicks.updatedAt` — which is exactly what makes `weeklyDue` and `manualDue` both re-evaluate to false on the next check, with no separate "handled" flag required. On failure, nothing is pushed, so the same due-check fires again next cycle (retry forever, no attempt cap — a failed run is cheap, and this guarantees self-healing the moment whatever was broken gets fixed, e.g. once a compatible Python version is available for the venv).

The Finance page's "Refresh now" button POSTs `{requestedAt: now}` to the `stockpicks_refresh` row using the same REST upsert pattern `sync.js` already uses elsewhere, then shows a "Refresh requested..." status. The page's existing `stockpicks` cloud-sync subscription (already wired up, unchanged) naturally re-renders the Signals section the moment the watcher's scan pushes new data — no polling added to the page itself.

### Error handling & safety

- **Overlap protection**: a lock file (`~/.oden-dashboard-signals-watcher.lock`) holding the running PID is created immediately before the `weekly_signals.py` subprocess call and removed in a `finally` right after. If a watcher tick finds an existing lock whose PID is still alive, it skips this cycle. If the PID is dead (a previous run crashed without cleanup), the lock is treated as stale and the cycle proceeds normally — no permanent deadlock from a crash.
- **Timezone correctness**: uses Python's stdlib `zoneinfo` to convert to `America/New_York` explicitly (handles EST/EDT automatically), independent of whatever timezone the Mac's system clock is set to.
- **Market holidays**: not handled. If Monday happens to be a market holiday, the watcher still fires at 9:30-9:45 ET and runs the scan against whatever `yfinance` returns for a closed market. This is an accepted, documented limitation, not an oversight — out of scope for this phase.
- **Watcher's own failures** (e.g. can't reach Supabase for the check itself): caught, logged to stderr, watcher exits cleanly. Nothing pushed, no crash loop; the next scheduled tick tries again.
- **Refresh-request staleness in the UI**: if `stockpicks_v1.updatedAt` hasn't advanced past the request timestamp within ~20 minutes (three missed 15-minute watcher cycles, allowing time for a slow scan too), the Finance page's status line changes from "Refresh requested..." to "Still waiting — is your Mac on and awake?" rather than showing an indefinite spinner.

### File structure & interfaces

- `scripts/signals_watcher.py` (new) — pure due-check functions (`is_weekly_due(state, now)`, `is_manual_due(state, refresh_req)`) taking explicit state/time as parameters, no I/O — same pure/orchestration split `weekly_signals.py` already established. I/O layer below: Supabase GET, lock-file acquire/release, subprocess invocation of `weekly_signals.py`, and `launchd` plist install/uninstall.
  - `python3 signals_watcher.py` — one check-and-maybe-run cycle (what launchd invokes every 15 min)
  - `python3 signals_watcher.py --install` — writes the plist to `~/Library/LaunchAgents`, loads it via `launchctl`
  - `python3 signals_watcher.py --uninstall` — unloads and removes the plist
- `tests/test_signals_watcher.py` (new) — real unit tests for the pure due-check logic (Monday/non-Monday, in/out of the 9:30-9:45 ET window, already-updated-this-week, pending-vs-already-fulfilled manual request, stale-vs-live lock PID); mocked tests for the I/O orchestration (Supabase calls, subprocess, launchctl), matching the pattern already established for `weekly_signals.py`.
- `finance.html` (modified) — a "Refresh now" button and status line added to the existing Stock Signals section; button click POSTs to `stockpicks_refresh` via the same REST pattern `sync.js` uses; status line reads from the already-synced `stockpicks_v1` and a locally-tracked request timestamp. No test framework exists for this side of the repo (consistent with the rest of the dashboard) — verification is manual/browser-based, with the curl+code-trace fallback already used throughout this project if Playwright's Chromium binary is unavailable.

### Testing

`tests/test_signals_watcher.py` unit-tests the pure due-check logic directly (no mocking needed — same approach as `weekly_signals.py`'s Task 1). The I/O orchestration (Supabase reads, subprocess call to `weekly_signals.py`, lock-file handling, `launchctl` invocation) is tested via mocks, matching `weekly_signals.py`'s Task 2 pattern — no real network/subprocess/filesystem escape in the automated suite. Manual verification: run `signals_watcher.py` once directly and confirm it correctly identifies "not due" under normal conditions; `--install`/`--uninstall` verified by checking `launchctl list` before/after and confirming the plist file's presence/absence. The Finance page button is verified manually in a browser (or the curl/code-trace fallback), confirming the request POST reaches Supabase and the status line's three states (idle / requested / stuck-waiting) render correctly.

**Known dependency**: this machine currently only has Python 3.9.6 installed system-wide, and the upstream scanner repo requires Python 3.10+ — `weekly_signals.py` correctly fails closed in this state (no bad data pushed), and per the "retry forever" design above, the watcher will keep re-attempting every 15 minutes harmlessly until a compatible Python becomes available. This phase doesn't fix that dependency; it's called out here so it isn't mistaken for a new bug once this ships.
