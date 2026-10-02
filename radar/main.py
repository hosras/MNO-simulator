"""Radar entry point — orchestrates sidebar, filters, tabs.

All Streamlit rendering happens inside main(); nothing at import time.
"""

import os
from datetime import datetime, timedelta

import streamlit as st

from radar._config import (
    DB_PATH,
    OPERATOR,
    ORANGE,
)
from radar.services.anomaly import detect_anomalies
from radar.services.period import period_stats, split_periods
from radar.views import (
    anomalies as v_anomalies,
)
from radar.views import (
    attack_radar as v_attack_radar,
)
from radar.views import (
    encryption as v_encryption,
)
from radar.views import (
    geography as v_geography,
)
from radar.views import (
    messaging as v_messaging,
)
from radar.views import (
    osint as v_osint,
)
from radar.views import (
    overview as v_overview,
)
from radar.views import (
    period_compare as v_period_compare,
)
from radar.views import (
    special_lines as v_special_lines,
)
from radar.views import (
    technology as v_technology,
)
from radar.views import (
    threat_radar as v_threat_radar,
)
from radar.views import (
    time_series as v_time_series,
)
from radar.views import (
    traffic_mix as v_traffic_mix,
)
from radar.views import (
    voice as v_voice,
)
from telecom_ui_common import db_mtime, load_data

# Optional streamlit-autorefresh (imported lazily to keep import clean)
try:
    from streamlit_autorefresh import st_autorefresh

    HAS_AUTOREFRESH = True
except ImportError:
    st_autorefresh = None
    HAS_AUTOREFRESH = False


# ------------------------------------------------------------------
# CSS
# ------------------------------------------------------------------
_CSS = """
<style>
  html, body, [class*="css"] {
    direction: ltr; text-align: left;
    font-family: 'Segoe UI','Roboto','Helvetica Neue',sans-serif;
  }
  .radar-header {
    background: linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
    padding:20px 26px; border-radius:14px; color:#f8fafc;
    display:flex; justify-content:space-between; align-items:center;
    border:1px solid #334155;
    box-shadow:0 6px 20px rgba(0,0,0,.4);
  }
  .radar-header .logo {
    font-size:26px; font-weight:800;
    background:linear-gradient(90deg,#f6821f,#fb923c);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
  }
  .radar-header .sub {font-size:13px; color:#94a3b8; margin-top:2px;}
  .stat-card {
    background:#ffffff; border:1px solid #e2e8f0;
    border-radius:12px; padding:16px 18px;
    box-shadow:0 1px 3px rgba(0,0,0,.05);
    transition: all .2s;
  }
  .stat-card:hover {box-shadow:0 4px 12px rgba(0,0,0,.1); border-color:#f6821f;}
  .stat-label {font-size:12px; color:#64748b; font-weight:600;
               text-transform:uppercase; letter-spacing:.5px;}
  .stat-value {font-size:28px; font-weight:800; color:#0f172a;
               margin-top:4px; line-height:1.1;}
  .stat-delta-up   {font-size:13px; color:#22c55e; font-weight:600; margin-top:6px;}
  .stat-delta-down {font-size:13px; color:#ef4444; font-weight:600; margin-top:6px;}
  .stat-delta-flat {font-size:13px; color:#94a3b8; font-weight:600; margin-top:6px;}
  .stat-sub {font-size:12px; color:#94a3b8; margin-top:4px;}
  .section-title {
    font-size:18px; font-weight:800; color:#0f172a;
    border-left:4px solid #f6821f; padding-left:12px;
    margin: 20px 0 12px 0;
  }
  .threat-card {
    background: linear-gradient(135deg,#fef2f2 0%,#fee2e2 100%);
    border:1px solid #fecaca; border-radius:12px; padding:16px 18px;
  }
  .threat-value {font-size:26px; font-weight:800; color:#dc2626;}
  .threat-label {font-size:12px; color:#991b1b; font-weight:600;
                 text-transform:uppercase;}
  .anomaly-card {
    background: linear-gradient(135deg,#fff7ed 0%,#ffedd5 100%);
    border:1px solid #fed7aa; border-radius:12px; padding:16px 18px;
  }
  .anomaly-value {font-size:26px; font-weight:800; color:#c2410c;}
  .anomaly-label {font-size:12px; color:#9a3412; font-weight:600;
                  text-transform:uppercase;}
  .live-badge {
    display:inline-block; background:#22c55e; color:#fff;
    padding:3px 10px; border-radius:20px; font-size:11px;
    font-weight:700; animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%,100% {opacity:1;}
    50% {opacity:.5;}
  }
  .period-badge {
    display:inline-block; padding:4px 10px; border-radius:6px;
    font-size:11px; font-weight:700; margin-left:6px;
  }
  .period-current {background:#dcfce7; color:#166534;}
  .period-previous {background:#e0e7ff; color:#3730a3;}
  div[data-testid="stMetricValue"] {font-size:22px;}
</style>
"""


# ------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------
def _render_header():
    st.markdown(
        f"""
    <div class="radar-header">
      <div>
        <div class="logo">📡 {OPERATOR} RADAR</div>
        <div class="sub">Statistical analytics + Anomaly detection + Period comparison</div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:12px;color:#94a3b8;">Generated</div>
        <div style="font-size:14px;font-weight:700;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.write("")


# ------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------
def _render_sidebar(data):
    cells = data["cells"]
    cdrs = data["cdrs"]
    subs = data["subscribers"]

    sel_cities = []
    sel_techs = []
    date_range = None
    compare_mode = False
    split_ratio = 0.5

    with st.sidebar:
        st.markdown("### 🌐 Data Controls")

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("🔄 Reload", use_container_width=True, key="btn_reload"):
                st.cache_data.clear()
                st.rerun()
        with col_r2:
            if st.button("🧹 Reset", use_container_width=True, key="btn_reset"):
                st.cache_data.clear()
                for k in list(st.session_state.keys()):
                    if k.startswith("radar_"):
                        del st.session_state[k]
                st.rerun()

        st.divider()
        st.markdown("### ⏱️ Real-time Mode")
        live_mode = st.toggle("Auto-refresh", value=False, key="radar_live")
        if live_mode:
            interval = st.select_slider(
                "Interval (seconds)",
                options=[10, 15, 30, 60, 120, 300],
                value=30,
                key="radar_interval",
            )
            if HAS_AUTOREFRESH:
                st_autorefresh(interval=interval * 1000, key="radar_autorefresh")
                st.markdown('<span class="live-badge">● LIVE</span>', unsafe_allow_html=True)
                st.caption(f"Refreshing every {interval}s")
            else:
                st.warning("Install `streamlit-autorefresh` for live mode.")

        st.divider()
        st.markdown("### 🎛️ Filters")

        all_cities = sorted(cells["city"].unique())
        sel_cities = st.multiselect("Cities", all_cities, default=all_cities, key="radar_cities")

        all_techs = sorted(cells["tech"].unique())
        sel_techs = st.multiselect("Technology", all_techs, default=all_techs, key="radar_techs")

        if len(cdrs):
            min_d = cdrs["ts"].min().date()
            max_d = cdrs["ts"].max().date()
            date_range = st.date_input("Date Range", (min_d, max_d), key="radar_dates")

        st.divider()
        st.markdown("### ⚖️ Comparison")
        compare_mode = st.toggle("Enable Period Comparison", value=False, key="radar_compare")
        if compare_mode:
            st.caption("Splits data into two halves by time")
            split_ratio = st.slider("Split ratio", 0.3, 0.7, 0.5, 0.05, key="radar_split")

        st.divider()
        st.caption(f"📊 {len(cdrs):,} CDRs")
        st.caption(f"🗼 {len(cells):,} cells")
        st.caption(f"👥 {len(subs):,} subscribers")

    return sel_cities, sel_techs, date_range, compare_mode, split_ratio


# ------------------------------------------------------------------
# FILTERS
# ------------------------------------------------------------------
def _apply_filters(data, sel_cities, sel_techs, date_range):
    cells = data["cells"]
    cdrs = data["cdrs"]
    subs = data["subscribers"]

    mask_cells = cells["city"].isin(sel_cities) & cells["tech"].isin(sel_techs)
    cells_f = cells[mask_cells].copy()

    mask_cdr = cdrs["city"].isin(sel_cities) & cdrs["tech"].isin(sel_techs)
    if date_range and len(date_range) == 2:
        import pandas as pd

        d1 = pd.to_datetime(date_range[0])
        d2 = pd.to_datetime(date_range[1]) + timedelta(days=1)
        mask_cdr &= (cdrs["ts"] >= d1) & (cdrs["ts"] < d2)
    cdrs_f = cdrs[mask_cdr].copy()

    subs_f = subs[subs["city"].isin(sel_cities)].copy() if "city" in subs.columns else subs.copy()

    return {
        "cells": cells_f,
        "cdrs": cdrs_f,
        "subs": subs_f,
        "all_cells": cells,
        "all_cdrs": cdrs,
        "all_subs": subs,
    }


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="TELECOM Radar",
        page_icon="📡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    _render_header()

    if not os.path.exists(DB_PATH):
        st.error(f"⚠️ Database not found at `{DB_PATH}`. " f"Run `telecom_net_sim.py` first.")
        st.stop()

    data = load_data(DB_PATH, db_mtime(DB_PATH))

    sel_cities, sel_techs, date_range, compare_mode, split_ratio = _render_sidebar(data)

    filtered = _apply_filters(data, sel_cities, sel_techs, date_range)

    # --- Period split ---
    prev_df, curr_df = (
        split_periods(filtered["cdrs"], split_ratio) if compare_mode else (None, None)
    )

    prev_stats = period_stats(prev_df) if compare_mode else None
    curr_stats = period_stats(curr_df) if compare_mode else None

    # --- SIGINT findings ---
    sig = data.get("findings", {}).get("SIGINT", {})

    # --- Anomalies ---
    anomalies = detect_anomalies(filtered["cdrs"], filtered["cells"], sig)

    # --- Ctx passed to every view ---
    ctx = {
        "compare_mode": compare_mode,
        "prev_df": prev_df,
        "curr_df": curr_df,
        "prev_stats": prev_stats,
        "curr_stats": curr_stats,
        "anomalies": anomalies,
        "sig": sig,
    }

    # --- TABS ---
    tabs = st.tabs(
        [
            "🎯 Overview",
            "⚖️ Period Compare",
            "🔍 Anomalies",
            "📈 Time Series",
            "📊 Traffic Mix",
            "📡 Technology",
            "📞 Voice",
            "💬 Messaging",
            "🚨 Threat Radar",
            "🔐 Encryption",
            "🔑 Special Lines",
            "🗺️ Geography",
            "🌐 OSINT",
            "🛡️ Attack Radar",
        ]
    )

    with tabs[0]:
        v_overview.render(data, filtered, ctx)
    with tabs[1]:
        v_period_compare.render(data, filtered, ctx)
    with tabs[2]:
        v_anomalies.render(data, filtered, ctx)
    with tabs[3]:
        v_time_series.render(data, filtered, ctx)
    with tabs[4]:
        v_traffic_mix.render(data, filtered, ctx)
    with tabs[5]:
        v_technology.render(data, filtered, ctx)
    with tabs[6]:
        v_voice.render(data, filtered, ctx)
    with tabs[7]:
        v_messaging.render(data, filtered, ctx)
    with tabs[8]:
        v_threat_radar.render(data, filtered, ctx)
    with tabs[9]:
        v_encryption.render(data, filtered, ctx)
    with tabs[10]:
        v_special_lines.render(data, filtered, ctx)
    with tabs[11]:
        v_geography.render(data, filtered, ctx)
    with tabs[12]:
        v_osint.render(data, filtered, ctx)
    with tabs[13]:
        v_attack_radar.render(data, filtered, ctx)

    # --- FOOTER ---
    st.write("")
    st.markdown(
        f"""
    <div style="text-align:center; padding:20px; color:#94a3b8; font-size:12px;
                border-top:1px solid #e2e8f0; margin-top:20px;">
      <b style="color:{ORANGE};">{OPERATOR} RADAR v2.0</b> — Advanced Statistical Analytics<br>
      Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • LOCAL-ONLY •
      {len(filtered['cdrs']):,} CDR records • {len(anomalies)} anomalies detected
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
