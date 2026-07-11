# Weekly Signals Scan Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scripts/weekly_signals.py`, a standalone CLI script that clones the upstream `mcmc-cuda-model` repo, runs its options scanner, parses the console output into structured data, and pushes it to Supabase as the Finance page's `stockpicks` data.

**Architecture:** One Python file with two clearly separated layers: pure parsing functions (no I/O, fully unit-testable) at the top, and I/O-heavy orchestration functions (venv setup, git clone, subprocess execution, HTTP push, CLI entry point) below, wired together in `main()`. This is the first Python code in this repo — no existing test infrastructure to integrate with, so this plan also creates `tests/` and confirms `pytest` (already present on this machine, confirmed) runs it.

**Tech Stack:** Python 3 standard library only for the script itself (`subprocess`, `tempfile`, `shutil`, `urllib.request`, `argparse`, `json`, `re`, `datetime`) — no third-party dependencies for `weekly_signals.py` itself. The dependencies it installs into a separate venv (`numpy`, `pandas`, `yfinance`, `scipy`, `pytz`, `pyyaml`) are for the *cloned upstream repo's* scanner, not for this script. `pytest` (already installed on this machine — confirmed via `python3 -m pytest --version` → `pytest 8.4.2`) for tests.

## Global Constraints

- Upstream repo: `https://github.com/adv-andrew/mcmc-cuda-model.git`, cloned fresh (`--depth 1`) into a new temp directory on every run, never cached/reused, always deleted afterward regardless of success/failure.
- Dedicated venv at `~/.oden-dashboard-signals-venv`, created once and reused across runs, containing exactly: `numpy`, `pandas`, `yfinance`, `scipy`, `pytz`, `pyyaml`. Never install `cupy-cuda12x`, `torch`, `streamlit`, or `optuna` — none are imported by the actual code path this script runs (`options_now.py`), and `cupy-cuda12x` would likely fail to install on a non-GPU machine anyway.
- Run `options_now.py` with no CLI args, no env vars — it needs neither.
- Parse exactly these upstream output formats (verbatim from the upstream source, not guessed): `REGIME:\s*(.+)` for the market regime; `^#(\d+)\s+(\S+)\s+(CALL|PUT)\s+\|\s+Confidence:\s+(\d+)/100` for each signal's rank/ticker/direction/confidence; `Strike:\s*\$(\d+)\s+ATM\s+\|\s+Exp:\s*~(\w{3}\s+\d+)` for that signal's strike and no-year expiration date.
- Expiration year inference: parse "Mon DD" against the current year; if that date is strictly before today, it means next year instead (expirations are always in the future).
- Zero parsed signals in a run is valid, not an error — still push `{regime, signals: []}`.
- A run only pushes to Supabase if the scan subprocess exits 0 AND a `REGIME:` line was found. Any failure prints to stderr, exits non-zero, and pushes nothing (preserves the last successful data already in Supabase).
- Supabase push target: `POST {SUPABASE_URL}/rest/v1/app_state?on_conflict=key` with `apikey`/`Authorization: Bearer {SUPABASE_KEY}`/`Content-Type: application/json`/`Prefer: resolution=merge-duplicates` headers and body `{"key": "stockpicks", "data": <payload>, "updated_at": <ISO now>}` — `SUPABASE_URL = 'https://srajryooffirbroltjmg.supabase.co'`, `SUPABASE_KEY = 'sb_publishable_5142ZwTLF_DkSVRzciNuRA_bHwRAu4c'` (same public/publishable credentials already embedded client-side in this repo's `sync.js` — not a new secret).
- `stockpicks` payload shape: `{"updatedAt": ISOString, "regime": "BULL"|"BEAR"|"NEUTRAL", "signals": [{"rank": int, "ticker": str, "direction": "CALL"|"PUT", "confidence": int, "strike": int|null, "expiration": "YYYY-MM-DD"|null}]}`.
- `--dry-run` CLI flag: runs the full pipeline but prints the payload instead of pushing it.

## File Structure

- `scripts/weekly_signals.py` — the script (new file, new directory)
- `tests/test_weekly_signals.py` — unit tests (new file, new directory)

---

### Task 1: Pure parsing functions

**Files:**
- Create: `scripts/weekly_signals.py` (parsing section only — `normalize_regime`, `infer_expiration_year`, `parse_scan_output`, plus the module-level regex constants)
- Test: `tests/test_weekly_signals.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces (for Task 2 to use verbatim):
  - `normalize_regime(raw: str) -> str` — returns `"BULL"`, `"BEAR"`, or `"NEUTRAL"`
  - `infer_expiration_year(month_day: str, today: date) -> str` — returns `"YYYY-MM-DD"`
  - `parse_scan_output(stdout: str, today: date = None) -> dict` — returns `{"regime": str, "signals": [{"rank": int, "ticker": str, "direction": str, "confidence": int, "strike": int|None, "expiration": str|None}]}`; raises `ValueError` if no `REGIME:` line is found

- [ ] **Step 1: Write the failing tests**

Create `/Users/odenransom/Oden-Dashboard/tests/test_weekly_signals.py`:

```python
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.weekly_signals import (
    normalize_regime,
    infer_expiration_year,
    parse_scan_output,
)


def test_normalize_regime_bull():
    assert normalize_regime('BULL MARKET') == 'BULL'


def test_normalize_regime_bear():
    assert normalize_regime('BEAR MARKET') == 'BEAR'


def test_normalize_regime_neutral_for_anything_else():
    assert normalize_regime('SIDEWAYS / CHOPPY') == 'NEUTRAL'
    assert normalize_regime('') == 'NEUTRAL'


def test_infer_expiration_year_same_year():
    today = date(2026, 7, 8)
    assert infer_expiration_year('Jul 17', today) == '2026-07-17'


def test_infer_expiration_year_wraps_to_next_year():
    today = date(2026, 12, 20)
    assert infer_expiration_year('Jan 15', today) == '2027-01-15'


def test_infer_expiration_year_today_exactly_stays_current_year():
    today = date(2026, 7, 8)
    assert infer_expiration_year('Jul 8', today) == '2026-07-08'


SAMPLE_STDOUT_ONE_SIGNAL = """OPTIONS SIGNALS - CURRENT BEST PLAYS
Date: 2026-07-06 09:03
--- MARKET STATUS ---
SPY: $612.34
vs 200 MA: ABOVE ($580.12)
vs 50 MA:  ABOVE ($605.00)
1-month:   +3.2%
5-day:     +0.8%
REGIME:    BULL MARKET

#1 HD PUT | Confidence: 72/100 (HIGH)
   Strike: $385 ATM | Exp: ~Jul 17
   Price: $402.10 | Vol: 34%
   Strength: 0.81 | Slope: +18.2
   5d: -1.2% | 20d: +2.1%
"""

SAMPLE_STDOUT_TWO_SIGNALS = """REGIME:    BEAR MARKET

#1 HD PUT | Confidence: 72/100 (HIGH)
   Strike: $385 ATM | Exp: ~Jul 17
   Price: $402.10 | Vol: 34%
#2 NVDA CALL | Confidence: 68/100 (MED)
   Strike: $140 ATM | Exp: ~Jul 24
   Price: $135.50 | Vol: 41%
"""

SAMPLE_STDOUT_ZERO_SIGNALS = """REGIME:    NEUTRAL
"""

SAMPLE_STDOUT_NO_REGIME = """OPTIONS SIGNALS - CURRENT BEST PLAYS
#1 HD PUT | Confidence: 72/100 (HIGH)
   Strike: $385 ATM | Exp: ~Jul 17
"""


def test_parse_scan_output_single_signal():
    result = parse_scan_output(SAMPLE_STDOUT_ONE_SIGNAL, today=date(2026, 7, 6))
    assert result['regime'] == 'BULL'
    assert result['signals'] == [
        {
            'rank': 1,
            'ticker': 'HD',
            'direction': 'PUT',
            'confidence': 72,
            'strike': 385,
            'expiration': '2026-07-17',
        }
    ]


def test_parse_scan_output_multiple_signals():
    result = parse_scan_output(SAMPLE_STDOUT_TWO_SIGNALS, today=date(2026, 7, 6))
    assert result['regime'] == 'BEAR'
    assert len(result['signals']) == 2
    assert result['signals'][0]['ticker'] == 'HD'
    assert result['signals'][1] == {
        'rank': 2,
        'ticker': 'NVDA',
        'direction': 'CALL',
        'confidence': 68,
        'strike': 140,
        'expiration': '2026-07-24',
    }


def test_parse_scan_output_zero_signals_is_valid():
    result = parse_scan_output(SAMPLE_STDOUT_ZERO_SIGNALS, today=date(2026, 7, 6))
    assert result['regime'] == 'NEUTRAL'
    assert result['signals'] == []


def test_parse_scan_output_missing_regime_raises():
    try:
        parse_scan_output(SAMPLE_STDOUT_NO_REGIME, today=date(2026, 7, 6))
        assert False, 'expected ValueError'
    except ValueError:
        pass
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 -m pytest tests/test_weekly_signals.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts'` (or similar — `scripts/weekly_signals.py` doesn't exist yet)

- [ ] **Step 3: Write the parsing implementation**

Create `/Users/odenransom/Oden-Dashboard/scripts/weekly_signals.py`:

```python
"""
Weekly stock-signals scan: clones adv-andrew/mcmc-cuda-model, runs its
options scanner, parses the console output, and pushes the result to
Supabase as the Finance page's `stockpicks` data.

Usage:
    python3 weekly_signals.py [--dry-run]
"""
import re
from datetime import date


REGIME_RE = re.compile(r'^REGIME:\s*(.+)$', re.MULTILINE)
SIGNAL_HEADER_RE = re.compile(
    r'^#(\d+)\s+(\S+)\s+(CALL|PUT)\s+\|\s+Confidence:\s+(\d+)/100',
    re.MULTILINE,
)
STRIKE_EXP_RE = re.compile(r'Strike:\s*\$(\d+)\s+ATM\s+\|\s+Exp:\s*~(\w{3}\s+\d+)')


def normalize_regime(raw):
    """Normalize a raw REGIME line's captured text to BULL/BEAR/NEUTRAL."""
    text = (raw or '').upper()
    if 'BULL' in text:
        return 'BULL'
    if 'BEAR' in text:
        return 'BEAR'
    return 'NEUTRAL'


def infer_expiration_year(month_day, today):
    """Given a 'Mon DD' string with no year, infer YYYY-MM-DD using `today`
    as the reference point. Option expirations are always in the future,
    so if the current-year interpretation is already in the past, it must
    mean next year's occurrence of that month/day instead."""
    from datetime import datetime as _dt
    parsed = _dt.strptime(month_day.strip(), '%b %d')
    candidate = date(today.year, parsed.month, parsed.day)
    if candidate < today:
        candidate = date(today.year + 1, parsed.month, parsed.day)
    return candidate.isoformat()


def parse_scan_output(stdout, today=None):
    """Parse options_now.py's stdout into {"regime": str, "signals": [...]}.
    Raises ValueError if no REGIME line is found."""
    if today is None:
        today = date.today()

    regime_match = REGIME_RE.search(stdout)
    if not regime_match:
        raise ValueError('No REGIME line found in scan output')
    regime = normalize_regime(regime_match.group(1))

    signals = []
    lines = stdout.splitlines()
    for i, line in enumerate(lines):
        header = SIGNAL_HEADER_RE.match(line)
        if not header:
            continue
        rank, ticker, direction, confidence = header.groups()
        strike = None
        expiration = None
        for lookahead in lines[i + 1:i + 3]:
            se = STRIKE_EXP_RE.search(lookahead)
            if se:
                strike = int(se.group(1))
                expiration = infer_expiration_year(se.group(2), today)
                break
        signals.append({
            'rank': int(rank),
            'ticker': ticker,
            'direction': direction,
            'confidence': int(confidence),
            'strike': strike,
            'expiration': expiration,
        })
    return {'regime': regime, 'signals': signals}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 -m pytest tests/test_weekly_signals.py -v`
Expected: `10 passed` (the 10 tests written in Step 1), no warnings, no errors

- [ ] **Step 5: Commit**

```bash
git add scripts/weekly_signals.py tests/test_weekly_signals.py
git commit -m "$(cat <<'EOF'
Add pure parsing functions for the weekly signals scan script

Phase (a) task 1: regime normalization, expiration-year inference,
and console-output parsing — all pure functions with unit tests,
no I/O yet. Orchestration (clone, venv, subprocess, Supabase push)
follows in task 2.
EOF
)"
```

---

### Task 2: Orchestration — venv, clone, run, push, CLI

**Files:**
- Modify: `scripts/weekly_signals.py` (add orchestration functions and `main()` below the existing parsing functions)
- Modify: `tests/test_weekly_signals.py` (add orchestration tests using mocks — no real network/subprocess/filesystem calls)

**Interfaces:**
- Consumes from Task 1: `parse_scan_output(stdout, today=None)` (called by `main()`, not otherwise wrapped)
- Produces: nothing consumed elsewhere (last task in this plan)

- [ ] **Step 1: Write the failing orchestration tests**

In `/Users/odenransom/Oden-Dashboard/tests/test_weekly_signals.py`, find this block (the end of the file, Task 1's last test):

```python
def test_parse_scan_output_missing_regime_raises():
    try:
        parse_scan_output(SAMPLE_STDOUT_NO_REGIME, today=date(2026, 7, 6))
        assert False, 'expected ValueError'
    except ValueError:
        pass
```

Replace it with:

```python
def test_parse_scan_output_missing_regime_raises():
    try:
        parse_scan_output(SAMPLE_STDOUT_NO_REGIME, today=date(2026, 7, 6))
        assert False, 'expected ValueError'
    except ValueError:
        pass


import scripts.weekly_signals as weekly_signals


def test_main_dry_run_prints_payload_without_pushing(monkeypatch, capsys):
    monkeypatch.setattr(weekly_signals, 'clone_repo', lambda dest: None)
    monkeypatch.setattr(weekly_signals, 'ensure_venv', lambda: '/fake/python')
    monkeypatch.setattr(
        weekly_signals, 'run_scan',
        lambda py, d: SAMPLE_STDOUT_ONE_SIGNAL,
    )
    pushed = []
    monkeypatch.setattr(
        weekly_signals, 'push_to_supabase',
        lambda payload: pushed.append(payload),
    )

    exit_code = weekly_signals.main(['--dry-run'])

    assert exit_code == 0
    assert pushed == []
    out = capsys.readouterr().out
    assert '"regime": "BULL"' in out
    assert '"ticker": "HD"' in out


def test_main_pushes_regime_and_empty_signals_on_success(monkeypatch):
    monkeypatch.setattr(weekly_signals, 'clone_repo', lambda dest: None)
    monkeypatch.setattr(weekly_signals, 'ensure_venv', lambda: '/fake/python')
    monkeypatch.setattr(
        weekly_signals, 'run_scan',
        lambda py, d: SAMPLE_STDOUT_ZERO_SIGNALS,
    )
    pushed = []
    monkeypatch.setattr(
        weekly_signals, 'push_to_supabase',
        lambda payload: pushed.append(payload),
    )

    exit_code = weekly_signals.main([])

    assert exit_code == 0
    assert len(pushed) == 1
    assert pushed[0]['regime'] == 'NEUTRAL'
    assert pushed[0]['signals'] == []
    assert 'updatedAt' in pushed[0]


def test_main_does_not_push_when_scan_fails(monkeypatch):
    monkeypatch.setattr(weekly_signals, 'clone_repo', lambda dest: None)
    monkeypatch.setattr(weekly_signals, 'ensure_venv', lambda: '/fake/python')

    def failing_scan(py, d):
        raise RuntimeError('options_now.py exited with code 1')

    monkeypatch.setattr(weekly_signals, 'run_scan', failing_scan)
    pushed = []
    monkeypatch.setattr(
        weekly_signals, 'push_to_supabase',
        lambda payload: pushed.append(payload),
    )

    exit_code = weekly_signals.main([])

    assert exit_code == 1
    assert pushed == []


def test_main_does_not_push_when_clone_fails(monkeypatch):
    def failing_clone(dest):
        raise RuntimeError('git clone failed')

    monkeypatch.setattr(weekly_signals, 'clone_repo', failing_clone)
    pushed = []
    monkeypatch.setattr(
        weekly_signals, 'push_to_supabase',
        lambda payload: pushed.append(payload),
    )

    exit_code = weekly_signals.main([])

    assert exit_code == 1
    assert pushed == []


def test_main_cleans_up_clone_dir_even_on_failure(monkeypatch, tmp_path):
    fake_dir = str(tmp_path / 'clone')
    import os as _os
    _os.makedirs(fake_dir)
    monkeypatch.setattr(
        weekly_signals.tempfile, 'mkdtemp',
        lambda prefix=None: fake_dir,
    )
    monkeypatch.setattr(weekly_signals, 'clone_repo', lambda dest: None)
    monkeypatch.setattr(weekly_signals, 'ensure_venv', lambda: '/fake/python')

    def failing_scan(py, d):
        raise RuntimeError('boom')

    monkeypatch.setattr(weekly_signals, 'run_scan', failing_scan)

    weekly_signals.main([])

    assert not _os.path.exists(fake_dir)
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 -m pytest tests/test_weekly_signals.py -v`
Expected: the 10 Task-1 tests still PASS; the new orchestration tests FAIL with `AttributeError: module 'scripts.weekly_signals' has no attribute 'clone_repo'` (or similar — the orchestration functions don't exist yet)

- [ ] **Step 3: Write the orchestration implementation**

In `/Users/odenransom/Oden-Dashboard/scripts/weekly_signals.py`, find this block (the end of the file — `parse_scan_output`'s closing lines):

```python
        signals.append({
            'rank': int(rank),
            'ticker': ticker,
            'direction': direction,
            'confidence': int(confidence),
            'strike': strike,
            'expiration': expiration,
        })
    return {'regime': regime, 'signals': signals}
```

Replace it with:

```python
        signals.append({
            'rank': int(rank),
            'ticker': ticker,
            'direction': direction,
            'confidence': int(confidence),
            'strike': strike,
            'expiration': expiration,
        })
    return {'regime': regime, 'signals': signals}


# ============================================================
# Orchestration — venv setup, clone, subprocess run, Supabase
# push, and the CLI entry point. Everything above this line is
# pure and unit-tested directly; everything below is I/O and is
# tested via mocks (see tests/test_weekly_signals.py).
# ============================================================
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone

REPO_URL = 'https://github.com/adv-andrew/mcmc-cuda-model.git'
VENV_DIR = os.path.expanduser('~/.oden-dashboard-signals-venv')
VENV_DEPS = ['numpy', 'pandas', 'yfinance', 'scipy', 'pytz', 'pyyaml']
SUPABASE_URL = 'https://srajryooffirbroltjmg.supabase.co'
SUPABASE_KEY = 'sb_publishable_5142ZwTLF_DkSVRzciNuRA_bHwRAu4c'


def ensure_venv():
    """Create the dedicated venv if it doesn't exist yet, and make sure the
    required CPU-only dependencies are installed (fast/idempotent when
    already satisfied). Returns the path to the venv's python executable."""
    venv_python = os.path.join(VENV_DIR, 'bin', 'python3')
    if not os.path.exists(venv_python):
        subprocess.run([sys.executable, '-m', 'venv', VENV_DIR], check=True)
    subprocess.run(
        [venv_python, '-m', 'pip', 'install', '-q'] + VENV_DEPS,
        check=True,
    )
    return venv_python


def clone_repo(dest_dir):
    subprocess.run(
        ['git', 'clone', '--depth', '1', REPO_URL, dest_dir],
        check=True, capture_output=True, text=True,
    )


def run_scan(venv_python, repo_dir):
    result = subprocess.run(
        [venv_python, 'scripts/options_now.py'],
        cwd=repo_dir, capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            'options_now.py exited with code %d\nstderr:\n%s'
            % (result.returncode, result.stderr)
        )
    return result.stdout


def push_to_supabase(payload):
    body = json.dumps({
        'key': 'stockpicks',
        'data': payload,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }).encode('utf-8')
    req = urllib.request.Request(
        SUPABASE_URL + '/rest/v1/app_state?on_conflict=key',
        data=body,
        method='POST',
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': 'Bearer ' + SUPABASE_KEY,
            'Content-Type': 'application/json',
            'Prefer': 'resolution=merge-duplicates',
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status >= 300:
            raise RuntimeError('Supabase push failed with status %d' % resp.status)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parsed_args = parser.parse_args(argv)

    clone_dir = tempfile.mkdtemp(prefix='mcmc-cuda-model-')
    try:
        print('Cloning %s...' % REPO_URL)
        clone_repo(clone_dir)

        print('Ensuring venv is ready...')
        venv_python = ensure_venv()

        print('Running options_now.py...')
        stdout = run_scan(venv_python, clone_dir)

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
    except Exception as e:
        print('ERROR: %s' % e, file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(clone_dir, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 -m pytest tests/test_weekly_signals.py -v`
Expected: `15 passed` (10 from Task 1 + 5 new orchestration tests), no warnings, no errors, no real network/subprocess calls made (all mocked)

- [ ] **Step 5: Manually verify `--dry-run` against the real upstream repo**

Run: `cd /Users/odenransom/Oden-Dashboard && python3 scripts/weekly_signals.py --dry-run`

Expected: the script prints progress lines (`Cloning...`, `Ensuring venv is ready...`, `Running options_now.py...`, `Parsing output...`) followed by a JSON payload with `updatedAt`, `regime` (one of `BULL`/`BEAR`/`NEUTRAL`), and a `signals` array (possibly empty) — no errors, no traceback. This run will take a minute or two (git clone, first-time venv creation and package installation, then the actual scan). Confirm the printed `regime` and any signal `ticker`/`confidence`/`expiration` values look sane by comparing against what the script's own stdout showed during the run (the "Running options_now.py..." step's underlying subprocess output isn't printed directly by `weekly_signals.py`, so this is really about the JSON payload being internally consistent and well-formed, not literally cross-checking terminal output — if this is the first-ever run and something about the upstream repo's actual output format has drifted from what's documented in this plan, the script will raise a parsing-related error rather than silently produce nonsense, since `REGIME_RE.search` failing raises `ValueError`).

If Playwright or any browser tool seems relevant here: it is not — this is a pure CLI/Python verification step, no browser involved.

- [ ] **Step 6: Commit**

```bash
git add scripts/weekly_signals.py tests/test_weekly_signals.py
git commit -m "$(cat <<'EOF'
Add orchestration to the weekly signals scan script

Phase (a) task 2 (final): venv setup, git clone, subprocess execution
of the upstream scanner, Supabase push, and the --dry-run CLI. Only
pushes when the scan succeeds and a REGIME line was found; a clone or
scan failure prints to stderr, exits non-zero, and pushes nothing.
Completes phase (a) of the stock-signals automation project — the
local helper server and scheduled trigger are separate, later phases.
EOF
)"
```
