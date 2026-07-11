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


def test_check_and_run_handles_supabase_read_failure_gracefully(monkeypatch, capsys):
    def failing_get(key):
        raise OSError('nodename nor servname provided, or not known')

    monkeypatch.setattr(signals_watcher, 'get_app_state_row', failing_get)
    ran = []
    monkeypatch.setattr(signals_watcher, 'run_weekly_signals_script', lambda: ran.append(True))

    # Must not raise.
    signals_watcher.check_and_run()

    assert ran == []
    err = capsys.readouterr().err
    assert 'ERROR' in err
