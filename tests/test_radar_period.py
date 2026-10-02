"""Unit tests for radar.services.period — pure helpers."""

import pandas as pd
import pytest

from radar.services.period import delta_pct, period_stats, split_periods


def make_cdrs(n=100, call_type="voice", bytes_=1000, duration=60):
    """Build a minimal CDR DataFrame with ts + expected columns."""
    ts = pd.date_range("2026-01-01", periods=n, freq="h")
    return pd.DataFrame(
        {
            "ts": ts,
            "record_id": [f"r{i}" for i in range(n)],
            "call_type": [call_type] * n,
            "bytes": [bytes_] * n,
            "duration_sec": [duration] * n,
        }
    )


# ==================================================================
# split_periods
# ==================================================================
class TestSplitPeriods:
    def test_empty_returns_none_pair(self):
        prev, curr = split_periods(pd.DataFrame())
        assert prev is None and curr is None

    def test_none_returns_none_pair(self):
        prev, curr = split_periods(None)
        assert prev is None and curr is None

    def test_default_split_is_half(self):
        df = make_cdrs(100)
        prev, curr = split_periods(df)
        assert len(prev) == 50
        assert len(curr) == 50

    def test_custom_ratio(self):
        df = make_cdrs(100)
        prev, curr = split_periods(df, split_ratio=0.3)
        assert len(prev) == 30
        assert len(curr) == 70

    def test_split_preserves_order(self):
        df = make_cdrs(10)
        prev, curr = split_periods(df)
        assert prev["ts"].iloc[-1] < curr["ts"].iloc[0]

    def test_no_records_lost(self):
        df = make_cdrs(37)
        prev, curr = split_periods(df)
        assert len(prev) + len(curr) == 37


# ==================================================================
# period_stats
# ==================================================================
class TestPeriodStats:
    def test_empty_returns_zeros(self):
        stats = period_stats(pd.DataFrame())
        assert stats["cdr"] == 0
        assert stats["bytes"] == 0
        assert stats["voice"] == 0
        assert stats["sms"] == 0

    def test_none_returns_zeros(self):
        stats = period_stats(None)
        assert stats["cdr"] == 0

    def test_counts_by_call_type(self):
        df = pd.concat(
            [
                make_cdrs(10, call_type="voice"),
                make_cdrs(5, call_type="sms"),
                make_cdrs(3, call_type="data"),
            ]
        )
        stats = period_stats(df)
        assert stats["cdr"] == 18
        assert stats["voice"] == 10
        assert stats["sms"] == 5
        assert stats["data"] == 3
        assert stats["mms"] == 0
        assert stats["rcs"] == 0

    def test_bytes_summed(self):
        df = make_cdrs(10, bytes_=500)
        stats = period_stats(df)
        assert stats["bytes"] == 5000

    def test_minutes_only_for_voice(self):
        df = pd.concat(
            [
                make_cdrs(5, call_type="voice", duration=60),  # 5 * 60s = 5 min
                make_cdrs(5, call_type="sms", duration=0),
            ]
        )
        stats = period_stats(df)
        assert stats["minutes"] == pytest.approx(5.0)


# ==================================================================
# delta_pct
# ==================================================================
class TestDeltaPct:
    def test_increase(self):
        assert delta_pct(150, 100) == pytest.approx(50.0)

    def test_decrease(self):
        assert delta_pct(50, 100) == pytest.approx(-50.0)

    def test_no_change(self):
        assert delta_pct(100, 100) == pytest.approx(0.0)

    def test_prev_zero_curr_zero(self):
        assert delta_pct(0, 0) is None

    def test_prev_zero_curr_positive(self):
        assert delta_pct(10, 0) == 100.0

    def test_large_increase(self):
        assert delta_pct(1000, 100) == pytest.approx(900.0)
