# Signals Watcher and Refresh-Now Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get `scripts/weekly_signals.py` actually running on a schedule (Monday NYSE open) and on-demand (a "Refresh now" button on the Finance page), via a lightweight `signals_watcher.py` woken every 15 minutes by a macOS `launchd` LaunchAgent — with no local server exposed to the internet.

**Architecture:** A pure/orchestration split matching `weekly_signals.py`'s existing pattern: `signals_watcher.py`'s due-check logic is pure functions taking explicit state/time, fully unit-tested; the Supabase reads, lock-file handling, subprocess invocation, and `launchd` install/uninstall are I/O, tested via mocks. The watcher and the Finance page's button never talk to each other directly — they're connected only through two Supabase `app_state` rows (`stockpicks`, already used by `weekly_signals.py`; `stockpicks_refresh`, new), the same mechanism every other cross-device feature in this dashboard already uses. Along the way, this plan also fixes a real bug discovered in the already-shipped `weekly_signals.py`: it currently pushes an unwrapped payload that the Finance page's client-side sync code can never actually apply to localStorage.

**Tech Stack:** Python 3 standard library only (`argparse`, `json`, `os`, `subprocess`, `urllib.request`, `zoneinfo`, `datetime`) for `signals_watcher.py`, matching `weekly_signals.py`. Plain JS (no framework) for the Finance page changes, matching the rest of this static-HTML dashboard. `pytest` (already installed, confirmed `8.4.2`) for tests.

## Global Constraints

- `signals_watcher.py` is woken by `launchd` every **15 minutes**.
- The weekly scan fires only when it's **Monday**, current time is in **9:30-9:45 America/New_York** (computed via stdlib `zoneinfo`, independent of the Mac's system timezone), and no successful scan has completed since this week's Monday 9:30 ET.
- A manual refresh fires whenever the `stockpicks_refresh` row's `requestedAt` is newer than the `stockpicks` row's `stockpicks_v1.updatedAt` (or no successful scan has ever completed).
- On failure (of any kind), nothing is pushed and no state is recorded as "handled" — the same due-check fires again next cycle. No retry cap.
- Overlap protection: a lock file at `~/.oden-dashboard-signals-watcher.lock` holding the running PID; a lock is treated as live only if that PID still exists, otherwise as stale (safe to proceed).
- `launchd` install target: a **LaunchAgent** at `~/Library/LaunchAgents/com.odendashboard.signals-watcher.plist` (per-user, no sudo) — not a LaunchDaemon.
- New Supabase `app_state` row: `key: 'stockpicks_refresh'`, `data: {'stockpicks_refresh_v1': {'requestedAt': ISOString}}` — same table, same public/publishable credentials already in `sync.js`/`weekly_signals.py`.
- The Finance page's "Refresh now" status line shows "Still waiting — is your Mac on and awake?" once **20 minutes** have passed since a still-unfulfilled request.
- `weekly_signals.py`'s push payload must be wrapped as `{'stockpicks_v1': {...}}` — `sync.js`'s `applyRemote()` only copies keys from the Supabase row's `data` field that match a page's registered `syncedKeys` (`finance.html` registers `syncedKeys: ['stockpicks_v1']`), so an unwrapped push is silently never applied to localStorage.

---

### Task 1: Fix `weekly_signals.py`'s push payload wrapping

**Files:**
- Modify: `scripts/weekly_signals.py` (`main()`)
- Modify: `tests/test_weekly_signals.py` (two existing tests need updating to assert the corrected shape)

**Interfaces:**
- Consumes: nothing new (fixes existing `main()`/`push_to_supabase()`)
- Produces: `weekly_signals.py`'s Supabase push now shaped `{'stockpicks_v1': {updatedAt, regime, signals}}` — this is what `signals_watcher.py` (Task 2/3) will read back via `get_app_state_row('stockpicks')`

This is a standalone bug fix, independent of the rest of this plan, but directly relevant: `signals_watcher.py`'s due-check logic (Task 2) reads the `stockpicks` row expecting this corrected wrapped shape.

- [ ] **Step 1: Update `main()` to wrap the payload before pushing/printing**

In `scripts/weekly_signals.py`, find this exact block:

```python
        print('Parsing output...')
        parsed = parse_scan_output(stdout)
        payload = {
            'updatedAt': datetime.now(timezone.utc).isoformat(),
            'regime': parsed['regime'],
            'signals': parsed['signals'],
        }

        if parsed_args.dry_run:
            print(json.dumps(payload, indent=2))
        else:
            print('Pushing to Supabase...')
            push_to_supabase(payload)
            print('Done.')
        return 0
```

Replace it with:

```python
        print('Parsing output...')
        parsed = parse_scan_output(stdout)
        payload = {
            'updatedAt': datetime.now(timezone.utc).isoformat(),
            'regime': parsed['regime'],
            'signals': parsed['signals'],
        }
        # sync.js's client-side apply logic only copies keys from the
        # Supabase row's `data` field that match a page's registered
        # syncedKeys — finance.html registers syncedKeys: ['stockpicks_v1'],
        # so the pushed data must be wrapped under that exact key or the
        # Finance page will never see it.
        wrapped = {'stockpicks_v1': payload}

        if parsed_args.dry_run:
            print(json.dumps(wrapped, indent=2))
        else:
            print('Pushing to Supabase...')
            push_to_supabase(wrapped)
            print('Done.')
        return 0
```

- [ ] **Step 2: Update the two tests that assert on the pushed/printed shape**

In `tests/test_weekly_signals.py`, find this exact block:

```python
    exit_code = weekly_signals.main(['--dry-run'])

    assert exit_code == 0
    assert pushed == []
    out = capsys.readouterr().out
    assert '"regime": "BULL"' in out
    assert '"ticker": "HD"' in out
```

Replace it with:

```python
    exit_code = weekly_signals.main(['--dry-run'])

    assert exit_code == 0
    assert pushed == []
    out = capsys.readouterr().out
    assert '"stockpicks_v1"' in out
    assert '"regime": "BULL"' in out
    assert '"ticker": "HD"' in out
```

In `tests/test_weekly_signals.py`, find this exact block:

```python
    exit_code = weekly_signals.main([])

    assert exit_code == 0
    assert len(pushed) == 1
    assert pushed[0]['regime'] == 'NEUTRAL'
    assert pushed[0]['signals'] == []
    assert 'updatedAt' in pushed[0]
```

Replace it with:

```python
    exit_code = weekly_signals.main([])

    assert exit_code == 0
    assert len(pushed) == 1
    assert list(pushed[0].keys()) == ['stockpicks_v1']
    assert pushed[0]['stockpicks_v1']['regime'] == 'NEUTRAL'
    assert pushed[0]['stockpicks_v1']['signals'] == []
    assert 'updatedAt' in pushed[0]['stockpicks_v1']
```

- [ ] **Step 3: Run the full test suite to verify the fix and confirm nothing else regressed**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 -m pytest tests/test_weekly_signals.py -v`
Expected: `16 passed`, no failures, no warnings.

- [ ] **Step 4: Manually verify with `--dry-run`**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 scripts/weekly_signals.py --dry-run`

This will attempt the real clone→scan→parse pipeline (the same one that currently fails on this machine due to the Python 3.9-vs-3.10 issue documented in `docs/superpowers/plans/2026-07-08-weekly-signals-script.md`). If it fails for that same environment reason, that's expected and not a regression from this task — confirm instead by reading the script's own dry-run branch: since the pipeline never reaches the `if parsed_args.dry_run:` line when the scan itself fails, this step cannot be verified end-to-end on this machine right now. In that case, verify Step 3's test output is sufficient evidence and note in your report that the real dry-run remains blocked by the pre-existing Python version issue, not by this task's change. If the scan does succeed (e.g. because a compatible Python is available), confirm the printed JSON's top-level key is `"stockpicks_v1"`.

- [ ] **Step 5: Commit**

```bash
git add scripts/weekly_signals.py tests/test_weekly_signals.py
git commit -m "$(cat <<'EOF'
Fix weekly_signals.py to wrap its push payload under stockpicks_v1

sync.js's client-side apply logic only copies keys from a Supabase
row's data field that match a page's registered syncedKeys.
finance.html registers syncedKeys: ['stockpicks_v1'], but this script
was pushing the signals payload unwrapped at the top level of data —
so a successful push would update Supabase correctly but the Finance
page would never actually see it, since applyRemote() would find no
matching key to copy into localStorage. Wraps the payload so it
matches the same shape sync.js itself would produce.
EOF
)"
```

---

### Task 2: `signals_watcher.py` — pure due-check logic

**Files:**
- Create: `scripts/signals_watcher.py` (pure section only — `extract_updated_at`, `extract_requested_at`, `this_weeks_monday_open`, `is_weekly_due`, `is_manual_due`)
- Create: `tests/test_signals_watcher.py`

**Interfaces:**
- Consumes: nothing (first task for this file)
- Produces (for Task 3 to use verbatim):
  - `extract_updated_at(state) -> datetime | None` — `state` is the parsed `stockpicks` row's `data` field (or `None`)
  - `extract_requested_at(refresh_state) -> datetime | None` — `refresh_state` is the parsed `stockpicks_refresh` row's `data` field (or `None`)
  - `this_weeks_monday_open(now_et: datetime) -> datetime` — `now_et` must be timezone-aware in `America/New_York`
  - `is_weekly_due(state, now_et: datetime) -> bool`
  - `is_manual_due(state, refresh_state) -> bool`

- [ ] **Step 1: Write the failing tests**

Create `/Users/odenransom/Oden-Dashboard/tests/test_signals_watcher.py`:

```python
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.signals_watcher import (
    extract_updated_at,
    extract_requested_at,
    this_weeks_monday_open,
    is_weekly_due,
    is_manual_due,
)

ET = ZoneInfo('America/New_York')


def test_extract_updated_at_missing_state_returns_none():
    assert extract_updated_at(None) is None
    assert extract_updated_at({}) is None


def test_extract_updated_at_missing_inner_key_returns_none():
    assert extract_updated_at({'someOtherKey': {}}) is None


def test_extract_updated_at_parses_iso_string():
    state = {'stockpicks_v1': {'updatedAt': '2026-07-06T13:04:00.000Z', 'regime': 'BULL', 'signals': []}}
    result = extract_updated_at(state)
    assert result is not None
    assert result.year == 2026 and result.month == 7 and result.day == 6


def test_extract_requested_at_missing_returns_none():
    assert extract_requested_at(None) is None
    assert extract_requested_at({}) is None


def test_extract_requested_at_parses_iso_string():
    refresh_state = {'stockpicks_refresh_v1': {'requestedAt': '2026-07-13T14:32:00.000Z'}}
    result = extract_requested_at(refresh_state)
    assert result is not None
    assert result.year == 2026 and result.month == 7 and result.day == 13


def test_this_weeks_monday_open_from_monday_itself():
    now_et = datetime(2026, 7, 13, 10, 0, tzinfo=ET)  # a Monday
    monday_open = this_weeks_monday_open(now_et)
    assert monday_open == datetime(2026, 7, 13, 9, 30, tzinfo=ET)


def test_this_weeks_monday_open_from_later_in_week():
    now_et = datetime(2026, 7, 16, 15, 0, tzinfo=ET)  # a Thursday
    monday_open = this_weeks_monday_open(now_et)
    assert monday_open == datetime(2026, 7, 13, 9, 30, tzinfo=ET)


def test_is_weekly_due_false_on_non_monday():
    now_et = datetime(2026, 7, 14, 9, 35, tzinfo=ET)  # Tuesday
    assert is_weekly_due(None, now_et) is False


def test_is_weekly_due_false_before_window():
    now_et = datetime(2026, 7, 13, 9, 15, tzinfo=ET)  # Monday, before 9:30
    assert is_weekly_due(None, now_et) is False


def test_is_weekly_due_false_after_window():
    now_et = datetime(2026, 7, 13, 10, 0, tzinfo=ET)  # Monday, after 9:45
    assert is_weekly_due(None, now_et) is False


def test_is_weekly_due_true_in_window_with_no_prior_scan():
    now_et = datetime(2026, 7, 13, 9, 35, tzinfo=ET)  # Monday, in window
    assert is_weekly_due(None, now_et) is True


def test_is_weekly_due_true_in_window_with_stale_prior_scan():
    now_et = datetime(2026, 7, 13, 9, 35, tzinfo=ET)
    state = {'stockpicks_v1': {'updatedAt': '2026-07-06T13:04:00.000Z', 'regime': 'BULL', 'signals': []}}
    assert is_weekly_due(state, now_et) is True


def test_is_weekly_due_false_in_window_if_already_ran_this_week():
    now_et = datetime(2026, 7, 13, 9, 40, tzinfo=ET)
    # 13:31 UTC == 9:31 ET (EDT, UTC-4) on 2026-07-13 — just after this
    # week's 9:30 ET window opened.
    state = {'stockpicks_v1': {'updatedAt': '2026-07-13T13:31:00.000Z', 'regime': 'BULL', 'signals': []}}
    assert is_weekly_due(state, now_et) is False


def test_is_manual_due_false_with_no_request():
    assert is_manual_due(None, None) is False
    assert is_manual_due(None, {}) is False


def test_is_manual_due_true_with_request_and_no_prior_scan():
    refresh_state = {'stockpicks_refresh_v1': {'requestedAt': '2026-07-13T14:32:00.000Z'}}
    assert is_manual_due(None, refresh_state) is True


def test_is_manual_due_true_when_request_newer_than_last_scan():
    state = {'stockpicks_v1': {'updatedAt': '2026-07-13T09:31:00.000Z', 'regime': 'BULL', 'signals': []}}
    refresh_state = {'stockpicks_refresh_v1': {'requestedAt': '2026-07-13T14:32:00.000Z'}}
    assert is_manual_due(state, refresh_state) is True


def test_is_manual_due_false_when_request_already_fulfilled():
    state = {'stockpicks_v1': {'updatedAt': '2026-07-13T14:35:00.000Z', 'regime': 'BULL', 'signals': []}}
    refresh_state = {'stockpicks_refresh_v1': {'requestedAt': '2026-07-13T14:32:00.000Z'}}
    assert is_manual_due(state, refresh_state) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 -m pytest tests/test_signals_watcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.signals_watcher'` (or similar — the file doesn't exist yet)

- [ ] **Step 3: Write the pure due-check implementation**

Create `/Users/odenransom/Oden-Dashboard/scripts/signals_watcher.py`:

```python
"""
Signals watcher: invoked periodically by launchd (see --install) to decide
whether the weekly options-signals scan is due, either on a Monday-morning
schedule or because the Finance page's "Refresh now" button was tapped.
Delegates the actual scan to weekly_signals.py as a subprocess.

Usage:
    python3 signals_watcher.py              # one check-and-maybe-run cycle
    python3 signals_watcher.py --install    # install as a launchd LaunchAgent
    python3 signals_watcher.py --uninstall  # remove the launchd LaunchAgent
"""
from datetime import datetime, timedelta


def extract_updated_at(state):
    """Given the parsed `stockpicks` app_state row's data field (or None),
    return the datetime.fromisoformat of stockpicks_v1.updatedAt, or None
    if missing/malformed."""
    if not state or not isinstance(state, dict):
        return None
    inner = state.get('stockpicks_v1')
    if not isinstance(inner, dict):
        return None
    updated_at = inner.get('updatedAt')
    if not updated_at:
        return None
    try:
        return datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def extract_requested_at(refresh_state):
    """Given the parsed `stockpicks_refresh` app_state row's data field (or
    None), return the datetime.fromisoformat of stockpicks_refresh_v1's
    requestedAt, or None if missing/malformed."""
    if not refresh_state or not isinstance(refresh_state, dict):
        return None
    inner = refresh_state.get('stockpicks_refresh_v1')
    if not isinstance(inner, dict):
        return None
    requested_at = inner.get('requestedAt')
    if not requested_at:
        return None
    try:
        return datetime.fromisoformat(requested_at.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def this_weeks_monday_open(now_et):
    """Return this week's Monday at 9:30 ET (as a datetime in now_et's
    timezone), for the week containing now_et."""
    monday_date = now_et.date() - timedelta(days=now_et.weekday())
    return now_et.replace(
        year=monday_date.year, month=monday_date.month, day=monday_date.day,
        hour=9, minute=30, second=0, microsecond=0,
    )


def is_weekly_due(state, now_et):
    """True if now_et falls in the Monday 9:30-9:45 ET window and this
    week's scan hasn't already completed."""
    if now_et.weekday() != 0:
        return False
    window_start = this_weeks_monday_open(now_et)
    window_end = window_start + timedelta(minutes=15)
    if not (window_start <= now_et < window_end):
        return False
    updated_at = extract_updated_at(state)
    if updated_at is None:
        return True
    return updated_at < window_start


def is_manual_due(state, refresh_state):
    """True if a refresh was requested more recently than the last
    successful scan (or no scan has ever succeeded)."""
    requested_at = extract_requested_at(refresh_state)
    if requested_at is None:
        return False
    updated_at = extract_updated_at(state)
    if updated_at is None:
        return True
    return requested_at > updated_at
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 -m pytest tests/test_signals_watcher.py -v`
Expected: `17 passed`, no warnings, no errors.

- [ ] **Step 5: Commit**

```bash
git add scripts/signals_watcher.py tests/test_signals_watcher.py
git commit -m "$(cat <<'EOF'
Add pure due-check logic for the signals watcher

Phase (b)/(c) task 1: extract_updated_at/extract_requested_at parse
the two relevant Supabase rows; is_weekly_due gates the scan to the
Monday 9:30-9:45 ET window (using zoneinfo, independent of system
timezone); is_manual_due compares a pending refresh request against
the last successful scan. All pure, all unit-tested. Orchestration
(Supabase reads, locking, subprocess, launchd install) follows in
task 2.
EOF
)"
```

---

### Task 3: `signals_watcher.py` — orchestration (Supabase reads, locking, subprocess, launchd)

**Files:**
- Modify: `scripts/signals_watcher.py` (add orchestration functions, `main()`, below the pure section)
- Modify: `tests/test_signals_watcher.py` (add orchestration tests using mocks — no real network/subprocess/filesystem escape, except deliberate `tmp_path`-scoped lock-file tests)

**Interfaces:**
- Consumes from Task 2: `is_weekly_due(state, now_et)`, `is_manual_due(state, refresh_state)`
- Consumes from `weekly_signals.py` (already shipped): `SUPABASE_URL`, `SUPABASE_KEY` constants (imported, not duplicated)
- Produces: nothing consumed elsewhere (last task for this file)

- [ ] **Step 1: Write the failing orchestration tests**

In `/Users/odenransom/Oden-Dashboard/tests/test_signals_watcher.py`, find this exact block (the end of the file, Task 2's last test):

```python
def test_is_manual_due_false_when_request_already_fulfilled():
    state = {'stockpicks_v1': {'updatedAt': '2026-07-13T14:35:00.000Z', 'regime': 'BULL', 'signals': []}}
    refresh_state = {'stockpicks_refresh_v1': {'requestedAt': '2026-07-13T14:32:00.000Z'}}
    assert is_manual_due(state, refresh_state) is False
```

Replace it with:

```python
def test_is_manual_due_false_when_request_already_fulfilled():
    state = {'stockpicks_v1': {'updatedAt': '2026-07-13T14:35:00.000Z', 'regime': 'BULL', 'signals': []}}
    refresh_state = {'stockpicks_refresh_v1': {'requestedAt': '2026-07-13T14:32:00.000Z'}}
    assert is_manual_due(state, refresh_state) is False


import json
import os as _os
import scripts.signals_watcher as signals_watcher


class _FakeHttpResponse:
    def __init__(self, payload_bytes):
        self._payload = payload_bytes

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._payload


def test_get_app_state_row_returns_data_when_present(monkeypatch):
    body = json.dumps([{'data': {'stockpicks_v1': {'regime': 'BULL'}}}]).encode('utf-8')
    monkeypatch.setattr(
        signals_watcher.urllib.request, 'urlopen',
        lambda req, timeout=30: _FakeHttpResponse(body),
    )
    result = signals_watcher.get_app_state_row('stockpicks')
    assert result == {'stockpicks_v1': {'regime': 'BULL'}}


def test_get_app_state_row_returns_none_when_missing(monkeypatch):
    body = json.dumps([]).encode('utf-8')
    monkeypatch.setattr(
        signals_watcher.urllib.request, 'urlopen',
        lambda req, timeout=30: _FakeHttpResponse(body),
    )
    result = signals_watcher.get_app_state_row('stockpicks')
    assert result is None


def test_is_lock_stale_or_absent_true_when_no_lock_file(tmp_path, monkeypatch):
    monkeypatch.setattr(signals_watcher, 'LOCK_PATH', str(tmp_path / 'nope.lock'))
    assert signals_watcher.is_lock_stale_or_absent() is True


def test_is_lock_stale_or_absent_false_when_pid_alive(tmp_path, monkeypatch):
    lock_path = str(tmp_path / 'test.lock')
    monkeypatch.setattr(signals_watcher, 'LOCK_PATH', lock_path)
    with open(lock_path, 'w') as f:
        f.write('12345')
    monkeypatch.setattr(signals_watcher.os, 'kill', lambda pid, sig: None)
    assert signals_watcher.is_lock_stale_or_absent() is False


def test_is_lock_stale_or_absent_true_when_pid_dead(tmp_path, monkeypatch):
    lock_path = str(tmp_path / 'test.lock')
    monkeypatch.setattr(signals_watcher, 'LOCK_PATH', lock_path)
    with open(lock_path, 'w') as f:
        f.write('12345')

    def fake_kill(pid, sig):
        raise ProcessLookupError()

    monkeypatch.setattr(signals_watcher.os, 'kill', fake_kill)
    assert signals_watcher.is_lock_stale_or_absent() is True


def test_acquire_and_release_lock(tmp_path, monkeypatch):
    lock_path = str(tmp_path / 'test.lock')
    monkeypatch.setattr(signals_watcher, 'LOCK_PATH', lock_path)
    signals_watcher.acquire_lock()
    assert _os.path.exists(lock_path)
    with open(lock_path) as f:
        assert f.read().strip() == str(_os.getpid())
    signals_watcher.release_lock()
    assert not _os.path.exists(lock_path)


def test_check_and_run_skips_when_not_due(monkeypatch):
    monkeypatch.setattr(signals_watcher, 'get_app_state_row', lambda key: None)
    monkeypatch.setattr(signals_watcher, 'is_weekly_due', lambda state, now: False)
    monkeypatch.setattr(signals_watcher, 'is_manual_due', lambda state, refresh: False)
    ran = []
    monkeypatch.setattr(signals_watcher, 'run_weekly_signals_script', lambda: ran.append(True))
    signals_watcher.check_and_run()
    assert ran == []


def test_check_and_run_runs_when_manual_due(monkeypatch, tmp_path):
    monkeypatch.setattr(signals_watcher, 'LOCK_PATH', str(tmp_path / 'test.lock'))
    monkeypatch.setattr(signals_watcher, 'get_app_state_row', lambda key: None)
    monkeypatch.setattr(signals_watcher, 'is_weekly_due', lambda state, now: False)
    monkeypatch.setattr(signals_watcher, 'is_manual_due', lambda state, refresh: True)
    ran = []
    monkeypatch.setattr(signals_watcher, 'run_weekly_signals_script', lambda: ran.append(True))
    signals_watcher.check_and_run()
    assert ran == [True]


def test_check_and_run_skips_when_lock_is_live(monkeypatch, tmp_path):
    lock_path = str(tmp_path / 'test.lock')
    monkeypatch.setattr(signals_watcher, 'LOCK_PATH', lock_path)
    with open(lock_path, 'w') as f:
        f.write(str(_os.getpid()))  # own PID — guaranteed alive
    monkeypatch.setattr(signals_watcher, 'get_app_state_row', lambda key: None)
    monkeypatch.setattr(signals_watcher, 'is_weekly_due', lambda state, now: True)
    monkeypatch.setattr(signals_watcher, 'is_manual_due', lambda state, refresh: False)
    ran = []
    monkeypatch.setattr(signals_watcher, 'run_weekly_signals_script', lambda: ran.append(True))
    signals_watcher.check_and_run()
    assert ran == []
    _os.remove(lock_path)


def test_check_and_run_releases_lock_after_run(monkeypatch, tmp_path):
    lock_path = str(tmp_path / 'test.lock')
    monkeypatch.setattr(signals_watcher, 'LOCK_PATH', lock_path)
    monkeypatch.setattr(signals_watcher, 'get_app_state_row', lambda key: None)
    monkeypatch.setattr(signals_watcher, 'is_weekly_due', lambda state, now: True)
    monkeypatch.setattr(signals_watcher, 'is_manual_due', lambda state, refresh: False)
    monkeypatch.setattr(signals_watcher, 'run_weekly_signals_script', lambda: None)
    signals_watcher.check_and_run()
    assert not _os.path.exists(lock_path)


def test_install_writes_plist_and_loads(monkeypatch, tmp_path):
    plist_path = str(tmp_path / 'test.plist')
    log_dir = str(tmp_path / 'Logs')
    monkeypatch.setattr(signals_watcher, 'PLIST_PATH', plist_path)
    monkeypatch.setattr(signals_watcher, 'LOG_DIR', log_dir)
    calls = []
    monkeypatch.setattr(signals_watcher.subprocess, 'run', lambda args, **kw: calls.append(args))
    signals_watcher.install()
    assert _os.path.exists(plist_path)
    with open(plist_path) as f:
        content = f.read()
    assert signals_watcher.PLIST_LABEL in content
    assert calls == [['launchctl', 'load', plist_path]]


def test_uninstall_unloads_and_removes(monkeypatch, tmp_path):
    plist_path = str(tmp_path / 'test.plist')
    with open(plist_path, 'w') as f:
        f.write('fake plist')
    monkeypatch.setattr(signals_watcher, 'PLIST_PATH', plist_path)
    calls = []
    monkeypatch.setattr(signals_watcher.subprocess, 'run', lambda args, **kw: calls.append(args))
    signals_watcher.uninstall()
    assert not _os.path.exists(plist_path)
    assert calls == [['launchctl', 'unload', plist_path]]
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 -m pytest tests/test_signals_watcher.py -v`
Expected: the 17 Task-2 tests still PASS; the new orchestration tests FAIL with `AttributeError: module 'scripts.signals_watcher' has no attribute 'get_app_state_row'` (or similar — the orchestration functions don't exist yet)

- [ ] **Step 3: Write the orchestration implementation**

In `/Users/odenransom/Oden-Dashboard/scripts/signals_watcher.py`, find this exact block (the end of the file — `is_manual_due`'s closing lines):

```python
def is_manual_due(state, refresh_state):
    """True if a refresh was requested more recently than the last
    successful scan (or no scan has ever succeeded)."""
    requested_at = extract_requested_at(refresh_state)
    if requested_at is None:
        return False
    updated_at = extract_updated_at(state)
    if updated_at is None:
        return True
    return requested_at > updated_at
```

Replace it with:

```python
def is_manual_due(state, refresh_state):
    """True if a refresh was requested more recently than the last
    successful scan (or no scan has ever succeeded)."""
    requested_at = extract_requested_at(refresh_state)
    if requested_at is None:
        return False
    updated_at = extract_updated_at(state)
    if updated_at is None:
        return True
    return requested_at > updated_at


# ============================================================
# Orchestration — Supabase reads, lock handling, subprocess
# invocation of weekly_signals.py, and launchd install/uninstall.
# Everything above this line is pure and unit-tested directly;
# everything below is I/O and is tested via mocks (see
# tests/test_signals_watcher.py).
# ============================================================
import argparse
import json
import os
import subprocess
import sys
import urllib.request
from zoneinfo import ZoneInfo

from scripts.weekly_signals import SUPABASE_URL, SUPABASE_KEY

LOCK_PATH = os.path.expanduser('~/.oden-dashboard-signals-watcher.lock')
PLIST_LABEL = 'com.odendashboard.signals-watcher'
PLIST_PATH = os.path.expanduser('~/Library/LaunchAgents/%s.plist' % PLIST_LABEL)
LOG_DIR = os.path.expanduser('~/Library/Logs')
WEEKLY_SIGNALS_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weekly_signals.py')


def get_app_state_row(key):
    """GET the `data` field of the given app_state row, or None if the row
    doesn't exist."""
    req = urllib.request.Request(
        SUPABASE_URL + '/rest/v1/app_state?key=eq.' + key + '&select=data',
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': 'Bearer ' + SUPABASE_KEY,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        rows = json.loads(resp.read().decode('utf-8'))
    return rows[0]['data'] if rows else None


def is_lock_stale_or_absent():
    """True if no scan appears to currently be running (no lock file, or
    the PID it names is no longer alive)."""
    if not os.path.exists(LOCK_PATH):
        return True
    try:
        with open(LOCK_PATH) as f:
            pid = int(f.read().strip())
    except (ValueError, OSError):
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def acquire_lock():
    with open(LOCK_PATH, 'w') as f:
        f.write(str(os.getpid()))


def release_lock():
    try:
        os.remove(LOCK_PATH)
    except OSError:
        pass


def run_weekly_signals_script():
    subprocess.run([sys.executable, WEEKLY_SIGNALS_SCRIPT], check=False)


def check_and_run():
    now_et = datetime.now(ZoneInfo('America/New_York'))
    state = get_app_state_row('stockpicks')
    refresh_state = get_app_state_row('stockpicks_refresh')

    if not (is_weekly_due(state, now_et) or is_manual_due(state, refresh_state)):
        print('Not due; nothing to do.')
        return

    if not is_lock_stale_or_absent():
        print('A scan already appears to be running; skipping this cycle.')
        return

    acquire_lock()
    try:
        print('Running weekly_signals.py...')
        run_weekly_signals_script()
    finally:
        release_lock()


PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{script}</string>
    </array>
    <key>StartInterval</key>
    <integer>900</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_out}</string>
    <key>StandardErrorPath</key>
    <string>{log_err}</string>
</dict>
</plist>
"""


def install():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
    plist = PLIST_TEMPLATE.format(
        label=PLIST_LABEL,
        python=sys.executable,
        script=os.path.abspath(__file__),
        log_out=os.path.join(LOG_DIR, 'oden-dashboard-signals-watcher.out.log'),
        log_err=os.path.join(LOG_DIR, 'oden-dashboard-signals-watcher.err.log'),
    )
    with open(PLIST_PATH, 'w') as f:
        f.write(plist)
    subprocess.run(['launchctl', 'load', PLIST_PATH], check=True)
    print('Installed and loaded: %s' % PLIST_PATH)


def uninstall():
    subprocess.run(['launchctl', 'unload', PLIST_PATH], check=False)
    try:
        os.remove(PLIST_PATH)
        print('Removed: %s' % PLIST_PATH)
    except FileNotFoundError:
        print('Nothing to remove (plist not found).')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args(argv)

    if args.install:
        install()
        return 0
    if args.uninstall:
        uninstall()
        return 0

    check_and_run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

Note: `datetime` and `timedelta` are already imported at the top of this file from Task 2 (`from datetime import datetime, timedelta`) — do not add a duplicate import.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 -m pytest tests/test_signals_watcher.py -v`
Expected: `29 passed` (17 from Task 2 + 12 new orchestration tests), no warnings, no errors, no real network/subprocess escape (the lock-file tests use `tmp_path`, a real temp directory, but that's expected local filesystem use in a test, not an escape to production paths).

- [ ] **Step 5: Manually verify `--install` / `--uninstall` and a real check cycle**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 scripts/signals_watcher.py --install`
Expected: prints `Installed and loaded: /Users/<you>/Library/LaunchAgents/com.odendashboard.signals-watcher.plist`, no errors. Confirm with `launchctl list | grep odendashboard` — should show the label loaded.

Run: `cd /Users/odenransom/Oden-Dashboard && python3 scripts/signals_watcher.py`
Expected: prints either `Not due; nothing to do.` (the normal case, since it's very unlikely to coincidentally be Monday 9:30-9:45 ET with no pending refresh request) or, if it happens to be due, attempts to run `weekly_signals.py` (which may hit the same pre-existing Python-version issue documented earlier — that's not a regression from this task).

Run: `cd /Users/odenransom/Oden-Dashboard && python3 scripts/signals_watcher.py --uninstall`
Expected: prints `Removed: ...plist`. Confirm with `launchctl list | grep odendashboard` — should show nothing.

If Playwright or any browser tool seems relevant here: it is not — this is a pure CLI/Python verification step, no browser involved.

- [ ] **Step 6: Commit**

```bash
git add scripts/signals_watcher.py tests/test_signals_watcher.py
git commit -m "$(cat <<'EOF'
Add orchestration to the signals watcher

Phase (b)/(c) task 2 (final for this file): reads the stockpicks and
stockpicks_refresh Supabase rows, gates on the pure due-check logic
from task 1, guards against overlapping runs with a PID lock file,
shells out to weekly_signals.py when a scan is due, and provides
--install/--uninstall for a launchd LaunchAgent (per-user, no sudo,
checks in every 15 minutes).
EOF
)"
```

---

### Task 4: "Refresh now" button and status line on the Finance page

**Files:**
- Modify: `finance.html` (CSS: new row + status classes; HTML: button + status line in the Stock Signals section; JS: `renderRefreshStatus()`, click handler, two `initCloudSync` registrations)

**Interfaces:**
- Consumes: `storeGet`/`storeSet` (existing localStorage helpers, already in scope within this file's IIFE), `initCloudSync` (from `sync.js`, already loaded on this page)
- Produces: nothing consumed elsewhere (last task in this plan). Writes `localStorage['stockpicks_refresh_v1'] = {requestedAt: ISOString}`, which `signals_watcher.py` (Task 3) reads back via Supabase as the `stockpicks_refresh` row's `data.stockpicks_refresh_v1.requestedAt`.

- [ ] **Step 1: Add the button/status-row CSS**

In `finance.html`, find this exact block:

```css
.sig-regime-badge.bull { background: rgba(107,227,164,0.14); color: var(--success); }
.sig-regime-badge.bear { background: rgba(255,107,107,0.14); color: var(--danger); }
.sig-regime-badge.neutral { background: rgba(255,255,255,0.06); color: var(--text-tertiary); }
```

Replace it with:

```css
.sig-regime-badge.bull { background: rgba(107,227,164,0.14); color: var(--success); }
.sig-regime-badge.bear { background: rgba(255,107,107,0.14); color: var(--danger); }
.sig-regime-badge.neutral { background: rgba(255,255,255,0.06); color: var(--text-tertiary); }
.sig-refresh-row {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 14px; flex-wrap: wrap;
}
.sig-refresh-status {
  font-size: 11px; color: var(--text-tertiary);
}
.sig-refresh-status.stuck { color: var(--warning); }
```

- [ ] **Step 2: Add the button and status line HTML**

In `finance.html`, find this exact block:

```html
  <div class="sig-meta-row">
    <span class="sig-meta-updated" id="sigUpdated">—</span>
    <span class="sig-regime-badge" id="sigRegime" style="display:none"></span>
  </div>

  <div id="sigList"></div>
```

Replace it with:

```html
  <div class="sig-meta-row">
    <span class="sig-meta-updated" id="sigUpdated">—</span>
    <span class="sig-regime-badge" id="sigRegime" style="display:none"></span>
  </div>

  <div class="sig-refresh-row">
    <button class="quick-add-btn" id="sigRefreshBtn" type="button">Refresh now</button>
    <span class="sig-refresh-status" id="sigRefreshStatus"></span>
  </div>

  <div id="sigList"></div>
```

- [ ] **Step 3: Add `renderRefreshStatus()`, the click handler, and wire up the initial render**

In `finance.html`, find this exact block:

```javascript
  renderSignals();
  window.renderSignals = renderSignals;

})();
</script>
```

Replace it with:

```javascript
  const SIG_REFRESH_STUCK_MS = 20 * 60 * 1000; // 20 minutes

  function renderRefreshStatus() {
    const btn = document.getElementById('sigRefreshBtn');
    const statusEl = document.getElementById('sigRefreshStatus');
    if (!btn || !statusEl) return;

    const state = storeGet('stockpicks_v1');
    const refresh = storeGet('stockpicks_refresh_v1');
    const updatedAt = state && state.updatedAt ? new Date(state.updatedAt).getTime() : null;
    const requestedAt = refresh && refresh.requestedAt ? new Date(refresh.requestedAt).getTime() : null;

    const pending = requestedAt != null && (updatedAt == null || requestedAt > updatedAt);
    if (!pending) {
      btn.disabled = false;
      btn.textContent = 'Refresh now';
      statusEl.textContent = '';
      statusEl.classList.remove('stuck');
      return;
    }

    const stuck = (Date.now() - requestedAt) > SIG_REFRESH_STUCK_MS;
    if (stuck) {
      btn.disabled = false;
      btn.textContent = 'Refresh now';
      statusEl.textContent = 'Still waiting — is your Mac on and awake?';
      statusEl.classList.add('stuck');
    } else {
      btn.disabled = true;
      btn.textContent = 'Refreshing...';
      statusEl.textContent = 'Refresh requested — waiting for your Mac...';
      statusEl.classList.remove('stuck');
    }
  }

  const sigRefreshBtnEl = document.getElementById('sigRefreshBtn');
  if (sigRefreshBtnEl) {
    sigRefreshBtnEl.addEventListener('click', function () {
      storeSet('stockpicks_refresh_v1', { requestedAt: new Date().toISOString() });
      renderRefreshStatus();
    });
  }

  renderSignals();
  renderRefreshStatus();
  window.renderSignals = renderSignals;
  window.renderRefreshStatus = renderRefreshStatus;
  setInterval(renderRefreshStatus, 30000);

})();
</script>
```

- [ ] **Step 4: Update the existing `stockpicks` sync registration and add a new `stockpicks_refresh` one**

In `finance.html`, find this exact block:

```html
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

</body>
</html>
```

Replace it with:

```html
<script>
document.addEventListener('DOMContentLoaded', function () {
  if (typeof initCloudSync !== 'function') return;
  initCloudSync({
    appKey: 'stockpicks',
    syncedKeys: ['stockpicks_v1'],
    onApplied: function () {
      if (window.renderSignals) window.renderSignals();
      if (window.renderRefreshStatus) window.renderRefreshStatus();
    }
  });
});
</script>

<script>
document.addEventListener('DOMContentLoaded', function () {
  if (typeof initCloudSync !== 'function') return;
  initCloudSync({
    appKey: 'stockpicks_refresh',
    syncedKeys: ['stockpicks_refresh_v1'],
    onApplied: function () {
      if (window.renderRefreshStatus) window.renderRefreshStatus();
    }
  });
});
</script>

</body>
</html>
```

- [ ] **Step 5: Verify the file is well-formed**

Run:
```bash
cd /Users/odenransom/Oden-Dashboard
node -e "
var fs = require('fs');
var s = fs.readFileSync('finance.html', 'utf8');
var re = /<script>([\s\S]*?)<\/script>/g;
var m, count = 0;
while ((m = re.exec(s))) { new Function(m[1]); count++; }
console.log('checked', count, 'inline script blocks OK');
"
```
Expected: prints a count with no syntax errors thrown.

- [ ] **Step 6: Manually verify in a browser**

Serve the directory (`python3 -m http.server 8123` from the repo root) and use Playwright MCP tools to navigate to `http://localhost:8123/finance.html`. If Playwright's Chromium binary is unavailable in this environment (a known recurring issue throughout this project), fall back to curl-fetching the served HTML plus manual code tracing, and report `DONE_WITH_CONCERNS` noting the fallback was used.

Confirm, using the browser's devtools console (or `browser_evaluate` if using Playwright) to manipulate `localStorage` directly:
- With no `stockpicks_refresh_v1` in localStorage: the button reads "Refresh now" and is enabled, no status text is shown.
- Click the button: `localStorage.getItem('stockpicks_refresh_v1')` now contains a `requestedAt` ISO timestamp; the button becomes disabled and reads "Refreshing...", the status line reads "Refresh requested — waiting for your Mac...".
- Manually run `localStorage.setItem('stockpicks_v1', JSON.stringify({updatedAt: new Date().toISOString(), regime: 'BULL', signals: []}))` then call `window.renderRefreshStatus()` (or `window.renderSignals()` if you want to see the list update too) — the button returns to "Refresh now" (enabled), status text clears.
- Manually run `localStorage.setItem('stockpicks_refresh_v1', JSON.stringify({requestedAt: new Date(Date.now() - 21*60*1000).toISOString()}))` (21 minutes ago) with no newer `stockpicks_v1.updatedAt`, then call `window.renderRefreshStatus()` — the status line reads "Still waiting — is your Mac on and awake?" and the button is re-enabled.

- [ ] **Step 7: Commit**

```bash
git add finance.html
git commit -m "$(cat <<'EOF'
Add a Refresh-now button to the Finance page's Stock Signals section

Phase (c) (final task of this plan): the button writes a requestedAt
timestamp to the stockpicks_refresh Supabase row via the existing
cloud-sync mechanism (no new backend code) — signals_watcher.py picks
it up on its next 15-minute check. A status line reflects pending
("waiting for your Mac...") vs. stuck (20+ min with no new data,
"is your Mac on and awake?") vs. idle states.
EOF
)"
```
