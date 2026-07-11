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

# Add the repo root to sys.path so we can import scripts module
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

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
    try:
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
    except Exception as e:
        print('ERROR: %s' % e, file=sys.stderr)


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
