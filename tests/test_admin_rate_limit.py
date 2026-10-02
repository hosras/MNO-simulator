# -*- coding: utf-8 -*-
"""Unit tests for admin.services.rate_limit — patch db_one, no real DB."""
from datetime import datetime, timedelta

import pytest

import admin.services.rate_limit as rl_module
from admin._config import LOGIN_WINDOW_MIN, LOGIN_MAX_FAILS
from admin.services.rate_limit import (
    count_recent_failed_logins,
    lockout_remaining_sec,
)


# ------------------------------------------------------------------
# Fixture: replace db_one with a stub that returns a configured row
# ------------------------------------------------------------------
@pytest.fixture
def stub_db(monkeypatch):
    """Return a dict with 'row' key. Set it to control what db_one returns."""
    state = {"row": None, "raise": None}

    def fake_db_one(sql, params=()):
        if state["raise"] is not None:
            raise state["raise"]
        return state["row"]

    monkeypatch.setattr(rl_module, "db_one", fake_db_one)
    return state


def _ts(minutes_ago: float) -> str:
    return (datetime.now() - timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%d %H:%M:%S")


# ==================================================================
# count_recent_failed_logins
# ==================================================================
class TestCountRecentFailedLogins:
    def test_returns_count_from_row(self, stub_db):
        stub_db["row"] = (7,)
        assert count_recent_failed_logins() == 7

    def test_zero_count(self, stub_db):
        stub_db["row"] = (0,)
        assert count_recent_failed_logins() == 0

    def test_none_row_returns_zero(self, stub_db):
        stub_db["row"] = None
        assert count_recent_failed_logins() == 0

    def test_exception_returns_zero(self, stub_db):
        stub_db["raise"] = RuntimeError("db down")
        assert count_recent_failed_logins() == 0

    def test_custom_window(self, stub_db):
        # The window is passed to SQL; here we only check the return path.
        stub_db["row"] = (3,)
        assert count_recent_failed_logins(minutes=60) == 3


# ==================================================================
# lockout_remaining_sec
# ==================================================================
class TestLockoutRemainingSec:
    def test_recent_failure_returns_positive_seconds(self, stub_db):
        # 1 min ago → lockout expires in ~14 min
        stub_db["row"] = (_ts(minutes_ago=1),)
        sec = lockout_remaining_sec()
        # Should be close to (LOGIN_WINDOW_MIN - 1) * 60 = 840
        assert (LOGIN_WINDOW_MIN - 2) * 60 < sec <= LOGIN_WINDOW_MIN * 60

    def test_old_failure_returns_zero(self, stub_db):
        # 30 min ago → window already expired
        stub_db["row"] = (_ts(minutes_ago=LOGIN_WINDOW_MIN + 15),)
        assert lockout_remaining_sec() == 0

    def test_none_row_returns_zero(self, stub_db):
        stub_db["row"] = None
        assert lockout_remaining_sec() == 0

    def test_empty_ts_returns_zero(self, stub_db):
        stub_db["row"] = (None,)
        assert lockout_remaining_sec() == 0

    def test_empty_string_ts_returns_zero(self, stub_db):
        stub_db["row"] = ("",)
        assert lockout_remaining_sec() == 0

    def test_exception_returns_zero(self, stub_db):
        stub_db["raise"] = RuntimeError("db down")
        assert lockout_remaining_sec() == 0

    def test_malformed_timestamp_returns_zero(self, stub_db):
        stub_db["row"] = ("not-a-timestamp",)
        assert lockout_remaining_sec() == 0

    def test_returns_int(self, stub_db):
        stub_db["row"] = (_ts(minutes_ago=1),)
        assert isinstance(lockout_remaining_sec(), int)

    def test_non_negative(self, stub_db):
        stub_db["row"] = (_ts(minutes_ago=0),)
        assert lockout_remaining_sec() >= 0


# ==================================================================
# Constants sanity
# ==================================================================
class TestConstants:
    def test_window_is_positive(self):
        assert LOGIN_WINDOW_MIN > 0

    def test_max_fails_is_positive(self):
        assert LOGIN_MAX_FAILS > 0

    def test_max_fails_reasonable(self):
        assert 3 <= LOGIN_MAX_FAILS <= 20