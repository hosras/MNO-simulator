"""Period comparison helpers — free of Streamlit imports.

Given a CDR DataFrame, split it into two periods (previous vs
current) and compute summary statistics for each.

Public API:
    split_periods(cdrs_f, split_ratio=0.5) -> (prev_df, curr_df)
    period_stats(df) -> dict
    delta_pct(curr, prev) -> float | None
"""

import pandas as pd


def split_periods(cdrs_f: pd.DataFrame, split_ratio: float = 0.5):
    """Split a time-sorted CDR DataFrame into (previous, current)."""
    if cdrs_f is None or not len(cdrs_f):
        return None, None
    s = cdrs_f.sort_values("ts").reset_index(drop=True)
    idx = int(len(s) * split_ratio)
    return s.iloc[:idx], s.iloc[idx:]


def period_stats(df) -> dict:
    """Return a dict of per-period totals. Empty for empty input."""
    if df is None or not len(df):
        return {
            "cdr": 0,
            "bytes": 0,
            "voice": 0,
            "sms": 0,
            "mms": 0,
            "data": 0,
            "rcs": 0,
            "minutes": 0,
        }
    return {
        "cdr": len(df),
        "bytes": df["bytes"].sum(),
        "voice": int((df["call_type"] == "voice").sum()),
        "sms": int((df["call_type"] == "sms").sum()),
        "mms": int((df["call_type"] == "mms").sum()),
        "data": int((df["call_type"] == "data").sum()),
        "rcs": int((df["call_type"] == "rcs").sum()),
        "minutes": df.loc[df["call_type"] == "voice", "duration_sec"].sum() / 60,
    }


def delta_pct(curr: float, prev: float):
    """Percent change from prev to curr. None when undefined."""
    if prev == 0:
        return None if curr == 0 else 100.0
    return (curr - prev) / prev * 100
