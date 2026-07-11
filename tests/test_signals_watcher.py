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
