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
            if SIGNAL_HEADER_RE.match(lookahead):
                break
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
