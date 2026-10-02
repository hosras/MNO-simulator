"""Shared Streamlit + Plotly helpers used by dashboard and radar.

Import this module from INSIDE main() of dashboard/radar. Do not import
it from plain Python scripts — it loads Streamlit at module level.

Public API:
    Colors   : ORANGE, BLUE, GREEN, RED, PURPLE, GRAY, DARK
    Data     : load_data, db_mtime
    UI       : chart, dl_button, csv_download
"""

import json
import os
import sqlite3

import pandas as pd
import plotly.express as px  # noqa: F401 (re-export)
import plotly.graph_objects as go  # noqa: F401 (re-export)
import streamlit as st

# ------------------------------------------------------------------
# Theme colors (shared across all dashboards)
# ------------------------------------------------------------------
ORANGE = "#f6821f"
BLUE = "#0ea5e9"
GREEN = "#22c55e"
RED = "#ef4444"
PURPLE = "#a855f7"
GRAY = "#94a3b8"
DARK = "#0f172a"


# ------------------------------------------------------------------
# DB mtime helper — pass DB_PATH explicitly
# ------------------------------------------------------------------
def db_mtime(db_path):
    """Return the DB file's mtime, or 0 if missing. Used as a cache key."""
    return os.path.getmtime(db_path) if os.path.exists(db_path) else 0


# ------------------------------------------------------------------
# Cached data loader
# ------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data(db_path, mtime):
    """Read every table into a dict. Cached by (db_path, mtime).

    The `mtime` argument is deliberately unused inside the body; it
    exists only so that Streamlit invalidates the cache when the DB
    file changes on disk.
    """
    if not os.path.exists(db_path):
        return None

    con = sqlite3.connect(db_path)

    def _tbl(name):
        r = con.execute(
            "SELECT name FROM sqlite_master " "WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        return r is not None

    data = {
        "cells": pd.read_sql("SELECT * FROM cells", con),
        "cores": pd.read_sql("SELECT * FROM cores", con),
        "subscribers": pd.read_sql("SELECT * FROM subscribers", con),
        "cdrs": pd.read_sql("SELECT * FROM cdrs", con),
        "osint_reg": pd.read_sql("SELECT * FROM osint_public_registry", con),
        "osint_comp": pd.read_sql("SELECT * FROM osint_complaints", con),
        "alerts": pd.read_sql("SELECT * FROM alerts", con),
        "sms_alerts": (
            pd.read_sql("SELECT * FROM sms_alerts", con) if _tbl("sms_alerts") else pd.DataFrame()
        ),
        "attack_scenarios": (
            pd.read_sql("SELECT * FROM attack_scenarios", con)
            if _tbl("attack_scenarios")
            else pd.DataFrame()
        ),
        "attack_events": (
            pd.read_sql("SELECT * FROM attack_events", con)
            if _tbl("attack_events")
            else pd.DataFrame()
        ),
    }

    findings = {}
    try:
        for k, v in con.execute("SELECT key, value FROM sigint_findings"):
            try:
                findings[k] = json.loads(v)
            except Exception:
                findings[k] = {}
    except Exception:
        pass
    data["findings"] = findings
    con.close()

    cdrs = data["cdrs"]
    if len(cdrs):
        cdrs["ts"] = pd.to_datetime(cdrs["timestamp"], errors="coerce")
        cdrs["hour"] = cdrs["ts"].dt.hour
        cdrs["day"] = cdrs["ts"].dt.date

    return data


# ------------------------------------------------------------------
# Auto-key chart + download helpers
# ------------------------------------------------------------------
_chart_counter = {"n": 0}
_dl_counter = {"n": 0}


def chart(fig, **kwargs):
    """st.plotly_chart with a guaranteed-unique key.

    Prevents StreamlitDuplicateElementId when two charts are configured
    identically.
    """
    _chart_counter["n"] += 1
    kwargs.setdefault("key", f"_ui_autochart_{_chart_counter['n']}")
    return st.plotly_chart(fig, **kwargs)


def dl_button(label, data=None, file_name=None, mime=None, **kwargs):
    """st.download_button with a guaranteed-unique key."""
    _dl_counter["n"] += 1
    kwargs.setdefault("key", f"_ui_autodl_{_dl_counter['n']}")
    return st.download_button(label, data=data, file_name=file_name, mime=mime, **kwargs)


def csv_download(df, filename, label="Download CSV"):
    """Download a DataFrame as UTF-8-BOM CSV."""
    return dl_button(
        label,
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
    )
