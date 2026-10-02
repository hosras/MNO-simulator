"""Dashboard entry point — sets page config, sidebar, KPI row, tabs.

Each tab is delegated to a view module in dashboard.views.*
"""

import os
import subprocess
import sys

import streamlit as st

from dashboard._config import DB_PATH
from dashboard.services.data import (
    apply_filters,
    get_raw_data,
    render_sidebar_filters,
)
from dashboard.services.styles import inject_css
from dashboard.services.ui import fmt_num, kpi, render_header
from dashboard.views import (
    alerts,
    attacks,
    encryption,
    network,
    osint,
    overview,
    report,
    sigint,
    signal,
    special_lines,
    subscribers,
    traffic,
    voice_messaging,
)


def main():
    st.set_page_config(
        page_title="TELECOM Network Dashboard",
        page_icon="📡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    render_header()

    # -------- SIDEBAR --------
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        if st.button("🔄 Reload Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        if st.button("▶️ Run Simulator", use_container_width=True):
            try:
                with st.spinner("Running simulator..."):
                    r = subprocess.run(
                        [sys.executable, "telecom_net_sim.py"],
                        capture_output=True,
                        text=True,
                        timeout=900,
                    )
                if r.returncode == 0:
                    st.success("Simulator finished successfully.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Error: {r.stderr[-400:]}")
            except Exception as e:
                st.error(f"Failed to run: {e}")
        st.divider()

    # -------- LOAD --------
    if not os.path.exists(DB_PATH):
        st.warning(
            "⚠️ Database not found. Please run `telecom_net_sim.py` "
            "first, or click 'Run Simulator'."
        )
        st.stop()

    data = get_raw_data()

    # -------- FILTERS --------
    with st.sidebar:
        st.markdown("### 🎛️ Filters")
        sel_cities, sel_techs, date_range = render_sidebar_filters(data["cells"], data["cdrs"])
        st.divider()
        st.caption(f"🗄️ DB: `{DB_PATH}`")
        st.caption("🔒 Mode: **LOCAL-ONLY**")

    filtered = apply_filters(data, sel_cities, sel_techs, date_range)

    # -------- KPI ROW --------
    cells_f = filtered["cells"]
    cdrs_f = filtered["cdrs"]
    subs_f = filtered["subs"]

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        kpi("Cell Sites", fmt_num(len(cells_f)), f"of {len(data['cells'])} total")
    with k2:
        kpi("Core Nodes", fmt_num(len(data["cores"])), "Core Network")
    with k3:
        kpi("Subscribers", fmt_num(len(subs_f)), "Active")
    with k4:
        kpi("CDR Records", fmt_num(len(cdrs_f)), "Last 7 days")
    with k5:
        voice = int((cdrs_f["call_type"] == "voice").sum()) if len(cdrs_f) else 0
        kpi("Voice Calls", fmt_num(voice), "Total", "#60a5fa")
    with k6:
        total_gb = cdrs_f["bytes"].sum() / 1e9 if len(cdrs_f) else 0
        kpi("Data Volume", f"{total_gb:,.1f} GB", "Total traffic", "#f59e0b")
    st.write("")

    # -------- TABS --------
    tabs = st.tabs(
        [
            "🏠 Overview",
            "🗼 Network & Topology",
            "📊 Traffic",
            "📶 Signal Quality",
            "📞 Voice & Messaging",
            "🌐 OSINT",
            "🕵️ SIGINT",
            "🔑 Special Lines",
            "🔐 Encryption",
            "🚨 Alerts & SMS",
            "👥 Subscribers",
            "📄 Report",
            "🛡️ Attacks",
        ]
    )

    with tabs[0]:
        overview.render(data, filtered)
    with tabs[1]:
        network.render(data, filtered)
    with tabs[2]:
        traffic.render(data, filtered)
    with tabs[3]:
        signal.render(data, filtered)
    with tabs[4]:
        voice_messaging.render(data, filtered)
    with tabs[5]:
        osint.render(data, filtered)
    with tabs[6]:
        sigint.render(data, filtered)
    with tabs[7]:
        special_lines.render(data, filtered)
    with tabs[8]:
        encryption.render(data, filtered)
    with tabs[9]:
        alerts.render(data, filtered)
    with tabs[10]:
        subscribers.render(data, filtered)
    with tabs[11]:
        report.render(data, filtered)
    with tabs[12]:
        attacks.render(data, filtered)


if __name__ == "__main__":
    main()
