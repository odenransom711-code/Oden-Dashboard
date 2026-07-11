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
