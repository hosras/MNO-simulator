# -*- coding: utf-8 -*-
"""
================================================================
 TELECOM-NET-SIM | Dashboard v3.0 (Streamlit)
 Management dashboard + OSINT / SIGINT analysis
 + Special Lines + Encryption + Alerts & SMS
 + Voice Bearers (VoLTE/VoWiFi/VoNR/CSFB) + MMS + RCS
 Fully local | Reads from telecom_sim.db
================================================================
"""
import os, json, sqlite3
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from telecom_common import CIPHER_SUITES

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
DB_PATH = "telecom_sim_output/telecom_sim.db"
OPERATOR_DEFAULT = "TELECOM"

def main():
    from telecom_ui_common import (
        chart as _chart,
        csv_download,
        db_mtime,
        load_data,
        ORANGE, BLUE, GREEN, RED, PURPLE, GRAY, DARK,
    )
    st.set_page_config(
        page_title="TELECOM Network Dashboard",
        page_icon="📡",
        layout="wide",
        initial_sidebar_state="expanded",
    )


    # ------------------------------------------------------------------
    # Custom CSS (LTR, English)
    # ------------------------------------------------------------------
    st.markdown("""
    <style>
      html, body, [class*="css"] {
        direction: ltr;
        text-align: left;
        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
      }
      .kpi-card {
        background: linear-gradient(135deg,#1f2937 0%,#111827 100%);
        color:#e5e7eb; padding:16px 18px; border-radius:14px;
        border:1px solid #374151; box-shadow:0 4px 14px rgba(0,0,0,.35);
        text-align:left;
      }
      .kpi-card .kpi-label {font-size:13px; color:#9ca3af;}
      .kpi-card .kpi-value {font-size:26px; font-weight:700; color:#fff; margin-top:2px;}
      .kpi-card .kpi-sub   {font-size:12px; color:#10b981; margin-top:4px;}
      section.main > div {padding-top: 1rem;}
      div[data-testid="stMetricValue"] { font-size: 22px; }
    </style>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # DATA LOADER
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def kpi(label, value, sub="", color="#10b981"):
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub" style="color:{color}">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

    def fmt_num(n):
        try: return f"{int(n):,}"
        except Exception: return str(n)

    # ------------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------------
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,#0ea5e9,#1e3a8a);
                padding:18px 24px;border-radius:14px;color:#fff;
                display:flex;justify-content:space-between;align-items:center;">
      <div>
        <div style="font-size:24px;font-weight:800;">📡 {OPERATOR_DEFAULT} Network Dashboard</div>
        <div style="opacity:.85;font-size:13px;">Network Simulation + OSINT/SIGINT + Voice/Messaging + Encryption + Alerts</div>
      </div>
      <div style="text-align:right;font-size:12px;opacity:.9;">
        {datetime.now().strftime('%Y-%m-%d %H:%M')}
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.write("")

    # ------------------------------------------------------------------
    # SIDEBAR
    # ------------------------------------------------------------------
    with st.sidebar:
        st.markdown("### ⚙️ Controls")

        if st.button("🔄 Reload Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        if st.button("▶️ Run Simulator", use_container_width=True):
            try:
                import subprocess, sys
                with st.spinner("Running simulator..."):
                    r = subprocess.run([sys.executable, "telecom_net_sim.py"],
                                       capture_output=True, text=True, timeout=900)
                if r.returncode == 0:
                    st.success("Simulator finished successfully.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Error: {r.stderr[-400:]}")
            except Exception as e:
                st.error(f"Failed to run: {e}")

        st.divider()

    # ------------------------------------------------------------------
    # LOAD
    # ------------------------------------------------------------------
    if not os.path.exists(DB_PATH):
        st.warning("⚠️ Database not found. Please run `telecom_net_sim.py` first, or click 'Run Simulator'.")
        st.stop()

    data = load_data(DB_PATH, db_mtime(DB_PATH))
    cells       = data["cells"]
    cores       = data["cores"]
    subs        = data["subscribers"]
    cdrs        = data["cdrs"]
    osint_reg   = data["osint_reg"]
    osint_comp  = data["osint_comp"]
    alerts_df   = data.get("alerts", pd.DataFrame())
    sms_alerts_df = data.get("sms_alerts", pd.DataFrame())
    findings    = data["findings"]
    sig         = findings.get("SIGINT", {})
    osi         = findings.get("OSINT", {})

    # ------------------------------------------------------------------
    # FILTERS
    # ------------------------------------------------------------------
    with st.sidebar:
        st.markdown("### 🎛️ Filters")
        all_cities = sorted(cells["city"].unique())
        sel_cities = st.multiselect("Cities", all_cities, default=all_cities)

        all_techs = sorted(cells["tech"].unique())
        sel_techs = st.multiselect("Technology", all_techs, default=all_techs)

        if len(cdrs):
            min_d = cdrs["ts"].min().date()
            max_d = cdrs["ts"].max().date()
            date_range = st.date_input("Date Range", (min_d, max_d))
        else:
            date_range = None

        st.divider()
        st.caption(f"🗄️ DB: `{DB_PATH}`")
        st.caption(f"🔒 Mode: **LOCAL-ONLY**")

    mask_cells = cells["city"].isin(sel_cities) & cells["tech"].isin(sel_techs)
    cells_f = cells[mask_cells].copy()

    mask_cdr = cdrs["city"].isin(sel_cities) & cdrs["tech"].isin(sel_techs)
    if date_range and len(date_range) == 2:
        d1 = pd.to_datetime(date_range[0])
        d2 = pd.to_datetime(date_range[1]) + timedelta(days=1)
        mask_cdr &= (cdrs["ts"] >= d1) & (cdrs["ts"] < d2)
    cdrs_f = cdrs[mask_cdr].copy()

    subs_f = subs[subs["city"].isin(sel_cities)] if "city" in subs.columns else subs

    # ------------------------------------------------------------------
    # KPI ROW
    # ------------------------------------------------------------------
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1: kpi("Cell Sites",     fmt_num(len(cells_f)),      f"of {len(cells)} total")
    with k2: kpi("Core Nodes",     fmt_num(len(cores)),        "Core Network")
    with k3: kpi("Subscribers",    fmt_num(len(subs_f)),       "Active")
    with k4: kpi("CDR Records",    fmt_num(len(cdrs_f)),       "Last 7 days")
    with k5:
        voice = int((cdrs_f["call_type"] == "voice").sum()) if len(cdrs_f) else 0
        kpi("Voice Calls", fmt_num(voice), "Total", "#60a5fa")
    with k6:
        total_gb = cdrs_f["bytes"].sum() / 1e9 if len(cdrs_f) else 0
        kpi("Data Volume", f"{total_gb:,.1f} GB", "Total traffic", "#f59e0b")

    st.write("")

    # ------------------------------------------------------------------
    # TABS
    # ------------------------------------------------------------------
    tabs = st.tabs([
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
    ])

    # ==================================================================
    # TAB 0 — OVERVIEW
    # ==================================================================
    with tabs[0]:
        st.subheader("Network Overview")

        c1, c2 = st.columns([2, 1])

        with c1:
            if len(cells_f):
                fig = px.scatter_geo(
                    cells_f, lat="lat", lon="lon", color="tech",
                    hover_name="name",
                    hover_data={"cell_id": True, "band": True, "tx_dbm": True,
                                "lat": False, "lon": False},
                    color_discrete_map={"2G": "#8888ff", "3G": "#38bdf8",
                                        "4G": "#22c55e", "5G": "#ef4444", "6G": "#a855f7",
                                        "6G": "#a855f7"},
                    title="Cell Sites Distribution Map",
                )
                fig.update_geos(
                    scope="world", showcountries=True, countrycolor="#64748b",
                    showland=True, landcolor="#f1f5f9",
                    showocean=True, oceancolor="#e0f2fe",
                    projection_type="natural earth",
                    center={"lat": 33.5, "lon": 53.5}, projection_scale=3.8,
                )
                fig.update_layout(height=460, margin=dict(l=0, r=0, t=40, b=0),
                                  legend_title_text="Technology")
                _chart(fig, use_container_width=True)
            else:
                st.info("No cells match the current filter.")

        with c2:
            if len(cells_f):
                tech_count = cells_f["tech"].value_counts().reset_index()
                tech_count.columns = ["tech", "count"]
                fig = px.pie(tech_count, names="tech", values="count",
                             hole=0.55, title="Technology Share",
                             color="tech",
                             color_discrete_map={"2G": "#8888ff", "3G": "#38bdf8",
                                                 "4G": "#22c55e", "5G": "#ef4444",
                                                 "6G": "#a855f7"})
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
                _chart(fig, use_container_width=True)

            if len(cells_f):
                city_count = cells_f["city"].value_counts().head(8).reset_index()
                city_count.columns = ["city", "count"]
                fig = px.bar(city_count, x="count", y="city", orientation="h",
                             title="Cell Sites per City",
                             color="count", color_continuous_scale="Blues")
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0),
                                  yaxis_title="", xaxis_title="", coloraxis_showscale=False)
                _chart(fig, use_container_width=True)

    # ==================================================================
    # TAB 1 — NETWORK & TOPOLOGY
    # ==================================================================
    with tabs[1]:
        st.subheader("Network Topology & Core Nodes")

        cc1, cc2 = st.columns(2)

        with cc1:
            st.markdown("#### 🗼 Cell Sites")
            st.dataframe(
                cells_f[["cell_id", "name", "tech", "city", "band",
                         "azimuth", "tilt", "tx_dbm", "backhaul_gbps"]],
                use_container_width=True, height=380, hide_index=True
            )
            csv_download(cells_f, "cells.csv")

        with cc2:
            st.markdown("#### 🧠 Core Nodes")
            st.dataframe(
                cores[["node_id", "name", "role", "tech", "city", "capacity_tps"]],
                use_container_width=True, height=380, hide_index=True
            )
            csv_download(cores, "core_nodes.csv")

        st.markdown("#### 📡 Core Nodes by Role")
        if len(cores):
            role_count = cores["role"].value_counts().reset_index()
            role_count.columns = ["role", "count"]
            fig = px.bar(role_count, x="role", y="count", color="count",
                         color_continuous_scale="Teal")
            fig.update_layout(height=320, coloraxis_showscale=False,
                              xaxis_title="", yaxis_title="")
            _chart(fig, use_container_width=True)

    # ==================================================================
    # TAB 2 — TRAFFIC
    # ==================================================================
    with tabs[2]:
        st.subheader("Traffic Analysis (CDR)")

        if not len(cdrs_f):
            st.info("No records match the current filter.")
        else:
            a1, a2 = st.columns([2, 1])

            with a1:
                by_hour = cdrs_f.groupby("hour").size().reset_index(name="count")
                fig = px.area(by_hour, x="hour", y="count",
                              title="Traffic Distribution by Hour",
                              markers=True)
                fig.update_traces(line_color="#0ea5e9", fillcolor="rgba(14,165,233,0.25)")
                fig.update_layout(height=320, xaxis=dict(dtick=1),
                                  xaxis_title="Hour", yaxis_title="Records")
                _chart(fig, use_container_width=True)

            with a2:
                type_count = cdrs_f["call_type"].value_counts().reset_index()
                type_count.columns = ["call_type", "count"]
                fig = px.pie(type_count, names="call_type", values="count",
                             hole=0.5, title="Traffic Mix by Type")
                fig.update_layout(height=320, margin=dict(l=0, r=0, t=40, b=0))
                _chart(fig, use_container_width=True)

            st.markdown("#### 🔥 Traffic Heatmap (City x Hour)")
            pivot = cdrs_f.pivot_table(index="city", columns="hour",
                                       values="record_id", aggfunc="count").fillna(0)
            if not pivot.empty:
                fig = px.imshow(pivot, aspect="auto", color_continuous_scale="YlOrRd",
                                labels=dict(x="Hour", y="City", color="Volume"))
                fig.update_layout(height=420)
                _chart(fig, use_container_width=True)

            b1, b2 = st.columns(2)
            with b1:
                by_tech = cdrs_f.groupby("tech").size().reset_index(name="count")
                fig = px.bar(by_tech, x="tech", y="count", color="tech",
                             title="Traffic Volume by Technology",
                             color_discrete_map={"2G": "#8888ff", "3G": "#38bdf8",
                                                 "4G": "#22c55e", "5G": "#ef4444",
                                                 "6G": "#a855f7"})
                fig.update_layout(height=320, showlegend=False,
                                  xaxis_title="", yaxis_title="")
                _chart(fig, use_container_width=True)

            with b2:
                by_city = (cdrs_f.groupby("city").size()
                           .reset_index(name="count").sort_values("count", ascending=True))
                fig = px.bar(by_city, x="count", y="city", orientation="h",
                             title="Traffic Volume by City",
                             color="count", color_continuous_scale="Purples")
                fig.update_layout(height=320, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="")
                _chart(fig, use_container_width=True)

            st.markdown("#### 📋 CDR Sample Records")
            st.dataframe(cdrs_f.head(500), use_container_width=True, height=300)
            csv_download(cdrs_f, "cdrs_filtered.csv", "Download All Filtered CDRs")

    # ==================================================================
    # TAB 3 — SIGNAL QUALITY
    # ==================================================================
    with tabs[3]:
        st.subheader("Radio Signal Quality (SIGINT - RF Layer)")

        df4g = cdrs_f[cdrs_f["rsrp"].notna()]
        if not len(df4g):
            st.info("No 4G/5G signal data matches the current filter.")
        else:
            s1, s2 = st.columns(2)
            with s1:
                fig = px.histogram(df4g, x="rsrp", nbins=50,
                                   title="RSRP Distribution (4G/5G)",
                                   color_discrete_sequence=["#22c55e"])
                fig.add_vline(x=-110, line_dash="dash", line_color="red",
                              annotation_text="Weak Threshold", annotation_position="top")
                fig.update_layout(height=340, xaxis_title="RSRP (dBm)", yaxis_title="Count")
                _chart(fig, use_container_width=True)

            with s2:
                sinr_df = df4g[df4g["sinr"].notna()]
                fig = px.histogram(sinr_df, x="sinr", nbins=50,
                                   title="SINR Distribution (4G/5G)",
                                   color_discrete_sequence=["#0ea5e9"])
                fig.add_vline(x=0, line_dash="dash", line_color="red")
                fig.update_layout(height=340, xaxis_title="SINR (dB)", yaxis_title="Count")
                _chart(fig, use_container_width=True)

            fig = px.box(df4g, x="tech", y="rsrp", color="tech",
                         title="RSRP Comparison by Technology",
                         color_discrete_map={"4G": "#22c55e", "5G": "#ef4444"})
            fig.update_layout(height=340, showlegend=False,
                              xaxis_title="", yaxis_title="RSRP (dBm)")
            _chart(fig, use_container_width=True)

            st.markdown("#### ⚠️ Weak Cells")
            weak = sig.get("weak_cells", [])
            if weak:
                weak_df = pd.DataFrame(weak, columns=["cell_id", "bad_samples"])
                weak_df = weak_df.sort_values("bad_samples", ascending=False).head(20)
                st.dataframe(weak_df, use_container_width=True, hide_index=True)
                csv_download(weak_df, "weak_cells.csv")
            else:
                st.success("No weak cells detected.")

    # ==================================================================
    # TAB 4 — VOICE & MESSAGING
    # ==================================================================
    with tabs[4]:
        st.subheader("📞 Voice Bearers & Messaging (VoLTE / VoWiFi / VoNR / MMS / RCS)")

        voice_df = cdrs_f[cdrs_f["call_type"] == "voice"]
        mms_df   = cdrs_f[cdrs_f["call_type"] == "mms"]
        rcs_df   = cdrs_f[cdrs_f["call_type"] == "rcs"]

        if not len(voice_df) and not len(mms_df) and not len(rcs_df):
            st.info("No voice or messaging records match the current filter.")
        else:
            # ---------- KPIs ----------
            v1, v2, v3, v4, v5 = st.columns(5)
            with v1:
                kpi("Voice Calls", fmt_num(len(voice_df)), "Total", "#60a5fa")
            with v2:
                volte = int((voice_df["voice_bearer"] == "VoLTE").sum()) if len(voice_df) else 0
                kpi("VoLTE Calls", fmt_num(volte), "Voice over LTE", "#22c55e")
            with v3:
                vonr = int((voice_df["voice_bearer"] == "VoNR").sum()) if len(voice_df) else 0
                kpi("VoNR Calls", fmt_num(vonr), "Voice over NR (5G)", "#ef4444")
            with v4:
                kpi("MMS", fmt_num(len(mms_df)), "Multimedia messages", "#8b5cf6")
            with v5:
                kpi("RCS", fmt_num(len(rcs_df)), "Rich communication", "#0ea5e9")

            st.write("")

            # ================= VOICE =================
            st.markdown("### 📞 Voice Bearer Analysis")

            if len(voice_df):
                vb = voice_df["voice_bearer"].value_counts().reset_index()
                vb.columns = ["bearer", "count"]

                vc1, vc2 = st.columns(2)

                with vc1:
                    fig = px.pie(vb, names="bearer", values="count", hole=0.55,
                                 title="Voice Bearer Mix",
                                 color="bearer",
                                 color_discrete_map={
                                     "VoLTE":"#22c55e","VoNR":"#ef4444","Vo6G":"#a855f7",
                                     "VoWiFi":"#0ea5e9","CSFB":"#94a3b8"})
                    fig.update_layout(height=360)
                    _chart(fig, use_container_width=True)

                with vc2:
                    codec = voice_df["voice_codec"].value_counts().reset_index()
                    codec.columns = ["codec", "count"]
                    fig = px.bar(codec, x="codec", y="count",
                                 title="Voice Codec Distribution",
                                 color="count", color_continuous_scale="Viridis")
                    fig.update_layout(height=360, coloraxis_showscale=False,
                                      xaxis_title="", yaxis_title="Calls")
                    _chart(fig, use_container_width=True)

                # QCI distribution
                st.markdown("#### 📊 QCI (QoS Class Identifier) Distribution")
                qci = voice_df["voice_qci"].value_counts().sort_index().reset_index()
                qci.columns = ["qci", "count"]
                fig = px.bar(qci, x="qci", y="count",
                             title="Voice QCI Distribution (QCI=1 for VoLTE/VoNR/VoWiFi, 0=CSFB)",
                             color="count", color_continuous_scale="Turbo")
                fig.update_layout(height=320, coloraxis_showscale=False,
                                  xaxis=dict(dtick=1),
                                  xaxis_title="QCI", yaxis_title="Calls")
                _chart(fig, use_container_width=True)

                # Bearer × Technology matrix
                st.markdown("#### 📊 Voice Bearer Distribution by Technology")
                if "tech" in voice_df.columns:
                    pivot = voice_df.pivot_table(
                        index="tech", columns="voice_bearer",
                        values="record_id", aggfunc="count").fillna(0)
                    if not pivot.empty:
                        fig = px.imshow(pivot, aspect="auto",
                                        color_continuous_scale="Greens",
                                        labels=dict(x="Bearer", y="Technology",
                                                    color="Calls"))
                        fig.update_layout(height=360)
                        _chart(fig, use_container_width=True)

                # VoLTE fallback detection
                st.markdown("#### ⚠️ VoLTE Fallback (4G/5G cells using CSFB)")
                fb = sig.get("volte_fallback", [])
                if fb:
                    df_fb = pd.DataFrame(fb)
                    by_cell = df_fb.groupby("cell_id").size().reset_index(name="count")
                    by_cell = by_cell.sort_values("count", ascending=False).head(15)
                    fig = px.bar(by_cell, x="count", y="cell_id", orientation="h",
                                 title="Top Cells with VoLTE Fallback to CSFB",
                                 color="count", color_continuous_scale="Reds")
                    fig.update_layout(height=360, coloraxis_showscale=False,
                                      xaxis_title="", yaxis_title="")
                    _chart(fig, use_container_width=True)
                    st.dataframe(df_fb.head(100), use_container_width=True,
                                 hide_index=True, height=250)
                    csv_download(df_fb, "volte_fallback.csv")
                else:
                    st.success("No VoLTE fallback detected.")

            st.divider()

            # ================= MMS =================
            st.markdown("### 📸 MMS Analysis")

            if len(mms_df):
                m1, m2 = st.columns(2)

                with m1:
                    cts = mms_df["mms_content_type"].value_counts().reset_index()
                    cts.columns = ["content", "count"]
                    fig = px.pie(cts, names="content", values="count", hole=0.55,
                                 title="MMS by Content Type")
                    fig.update_layout(height=360)
                    _chart(fig, use_container_width=True)

                with m2:
                    deliv = mms_df["mms_delivery"].value_counts().reset_index()
                    deliv.columns = ["status", "count"]
                    fig = px.bar(deliv, x="status", y="count",
                                 title="MMS Delivery Status",
                                 color="status",
                                 color_discrete_map={
                                     "DELIVERED":"#22c55e","EXPIRED":"#f59e0b",
                                     "REJECTED":"#ef4444","PENDING":"#94a3b8"})
                    fig.update_layout(height=360, showlegend=False,
                                      xaxis_title="", yaxis_title="")
                    _chart(fig, use_container_width=True)

                fig = px.histogram(mms_df, x="mms_size_bytes", nbins=50,
                                   title="MMS Size Distribution (bytes)",
                                   color_discrete_sequence=["#8b5cf6"])
                fig.update_layout(height=340, xaxis_title="Size (bytes)",
                                  yaxis_title="Count")
                _chart(fig, use_container_width=True)

                total_mb = mms_df["mms_size_bytes"].sum() / 1e6
                st.markdown(f"**Total MMS volume:** `{total_mb:,.2f} MB` "
                            f"across `{len(mms_df):,}` messages")

                st.markdown("#### ⚠️ Large MMS from Normal Lines (possible abuse)")
                lm = sig.get("mms_large_suspects", [])
                if lm:
                    df_lm = pd.DataFrame(lm)
                    st.dataframe(df_lm, use_container_width=True,
                                 hide_index=True, height=250)
                    csv_download(df_lm, "mms_large_suspects.csv")
                else:
                    st.success("No large MMS abuse detected.")

                st.dataframe(mms_df.head(300), use_container_width=True,
                             hide_index=True, height=250)
                csv_download(mms_df, "mms_records.csv")
            else:
                st.info("No MMS records match the current filter.")

            st.divider()

            # ================= RCS =================
            st.markdown("### 💬 RCS Analysis")
            if len(rcs_df):
                r1, r2 = st.columns([1, 2])

                with r1:
                    rt = rcs_df["rcs_type"].value_counts().reset_index()
                    rt.columns = ["rcs_type", "count"]
                    fig = px.pie(rt, names="rcs_type", values="count", hole=0.5,
                                 title="RCS by Type")
                    fig.update_layout(height=340)
                    _chart(fig, use_container_width=True)

                with r2:
                    fig = px.histogram(rcs_df, x="bytes", nbins=50,
                                       title="RCS Message Size Distribution",
                                       color_discrete_sequence=["#0ea5e9"])
                    fig.update_layout(height=340, xaxis_title="Bytes",
                                      yaxis_title="Count")
                    _chart(fig, use_container_width=True)

                st.dataframe(rcs_df.head(300), use_container_width=True,
                             hide_index=True, height=250)
                csv_download(rcs_df, "rcs_records.csv")
            else:
                st.info("No RCS records match the current filter.")

            st.divider()

            # ================= COMBINED CDR =================
            st.markdown("### 📋 Combined Voice + Messaging CDR Sample")
            vm = cdrs_f[cdrs_f["call_type"].isin(["voice","sms","mms","rcs"])].copy()
            cols_show = ["record_id","timestamp","msisdn","call_type",
                         "duration_sec","bytes","voice_bearer","voice_codec",
                         "mms_content_type","mms_delivery","rcs_type",
                         "cell_id","tech","city"]
            cols_show = [c for c in cols_show if c in vm.columns]
            st.dataframe(vm[cols_show].head(500),
                         use_container_width=True, hide_index=True, height=400)
            csv_download(vm, "voice_messaging_cdr.csv")

    # ==================================================================
    # TAB 5 — OSINT
    # ==================================================================
    with tabs[5]:
        st.subheader("🌐 OSINT Analysis - Public Sources")

        oc1, oc2, oc3 = st.columns(3)
        with oc1: kpi("Public Registry Rows", fmt_num(len(osint_reg)), "Public Registry")
        with oc2: kpi("Public Complaints", fmt_num(len(osint_comp)), "Social Complaints", "#f59e0b")
        with oc3:
            neg = int((osint_comp["sentiment"] == "negative").sum()) if len(osint_comp) else 0
            kpi("Negative Sentiment", fmt_num(neg),
                f"{neg/max(1,len(osint_comp))*100:.0f}% of total", "#ef4444")

        st.write("")

        o1, o2 = st.columns(2)
        with o1:
            if len(osint_comp):
                topic_count = osint_comp["topic"].value_counts().reset_index()
                topic_count.columns = ["topic", "count"]
                fig = px.bar(topic_count, x="count", y="topic", orientation="h",
                             title="Public Complaint Topics",
                             color="count", color_continuous_scale="Reds")
                fig.update_layout(height=380, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="")
                _chart(fig, use_container_width=True)

        with o2:
            if len(osint_comp):
                sent = osint_comp["sentiment"].value_counts().reset_index()
                sent.columns = ["sentiment", "count"]
                fig = px.pie(sent, names="sentiment", values="count",
                             hole=0.55, title="Sentiment Analysis",
                             color="sentiment",
                             color_discrete_map={"negative": "#ef4444",
                                                 "neutral": "#f59e0b",
                                                 "positive": "#22c55e"})
                fig.update_layout(height=380)
                _chart(fig, use_container_width=True)

        o3, o4 = st.columns(2)
        with o3:
            if len(osint_comp):
                city_comp = osint_comp["city"].value_counts().reset_index()
                city_comp.columns = ["city", "count"]
                fig = px.bar(city_comp, x="city", y="count",
                             title="Complaints by City",
                             color="count", color_continuous_scale="Oranges")
                fig.update_layout(height=320, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="")
                _chart(fig, use_container_width=True)

        with o4:
            if len(osint_comp):
                src = osint_comp["source"].value_counts().reset_index()
                src.columns = ["source", "count"]
                fig = px.pie(src, names="source", values="count",
                             title="Public Sources of Complaints")
                fig.update_layout(height=320)
                _chart(fig, use_container_width=True)

        st.markdown("#### 📋 Public Cell Registry (Sample)")
        st.dataframe(osint_reg.head(200), use_container_width=True, height=280,
                     hide_index=True)
        csv_download(osint_reg, "osint_registry.csv")

        st.markdown("#### 📋 Public Complaints (Sample)")
        st.dataframe(osint_comp.head(200), use_container_width=True, height=280,
                     hide_index=True)
        csv_download(osint_comp, "osint_complaints.csv")

    # ==================================================================
    # TAB 6 — SIGINT
    # ==================================================================
    with tabs[6]:
        st.subheader("🕵️ SIGINT Analysis - Signal & Metadata")

        s1, s2, s3, s4 = st.columns(4)
        with s1: kpi("IMEI Churn", fmt_num(len(sig.get("imei_churn_suspects", []))),
                     "Possible SIM clone", "#ef4444")
        with s2: kpi("SIM-Box", fmt_num(len(sig.get("simbox_suspects", []))),
                     "Suspicious traffic", "#f59e0b")
        with s3: kpi("Impossible Travel", fmt_num(len(sig.get("impossible_travel", []))),
                     "Anomalous movement", "#a855f7")
        with s4: kpi("Weak Cells", fmt_num(len(sig.get("weak_cells", []))),
                     "Low quality", "#0ea5e9")

        st.write("")

        st.markdown("### 🔴 IMEI Churn - Multiple IMEIs per IMSI")
        imei_churn = sig.get("imei_churn_suspects", [])
        if imei_churn:
            df_churn = pd.DataFrame(imei_churn, columns=["imsi", "distinct_imeis"])
            fig = px.bar(df_churn.head(15), x="imsi", y="distinct_imeis",
                         title="IMSIs with Most Distinct IMEIs",
                         color="distinct_imeis", color_continuous_scale="Reds")
            fig.update_layout(height=340, coloraxis_showscale=False,
                              xaxis_title="IMSI", yaxis_title="Distinct IMEIs")
            _chart(fig, use_container_width=True)
            st.dataframe(df_churn, use_container_width=True, hide_index=True, height=200)
            csv_download(df_churn, "sigint_imei_churn.csv")
        else:
            st.success("No suspects found.")

        st.divider()

        st.markdown("### 🟠 SIM-Box - Bulk Short Calls")
        simbox = sig.get("simbox_suspects", [])
        if simbox:
            df_sb = pd.DataFrame(simbox)
            c1, c2 = st.columns(2)
            with c1:
                fig = px.scatter(df_sb, x="out_calls", y="unique_targets",
                                 size="short_call_ratio", color="short_call_ratio",
                                 hover_data=["msisdn"],
                                 title="SIM-Box Suspects Distribution",
                                 color_continuous_scale="OrRd")
                fig.update_layout(height=340)
                _chart(fig, use_container_width=True)
            with c2:
                st.dataframe(df_sb, use_container_width=True, height=340, hide_index=True)
            csv_download(df_sb, "sigint_simbox.csv")
        else:
            st.success("No suspects found.")

        st.divider()

        st.markdown("### 🟣 Impossible Travel - Anomalous Movement")
        imp = sig.get("impossible_travel", [])
        if imp:
            df_imp = pd.DataFrame(imp)
            fig = px.scatter(df_imp, x="km", y="speed_kmh",
                             size="dt_sec", color="speed_kmh",
                             hover_data=["msisdn", "from", "to", "dt_sec"],
                             title="Impossible Travel Events (speed > 900 km/h)",
                             color_continuous_scale="Purples")
            fig.update_layout(height=380, xaxis_title="Distance (km)",
                              yaxis_title="Speed (km/h)")
            _chart(fig, use_container_width=True)
            st.dataframe(df_imp, use_container_width=True, hide_index=True, height=220)
            csv_download(df_imp, "sigint_impossible_travel.csv")
        else:
            st.success("No suspects found.")

        st.divider()

        st.markdown("### 🔵 Weak Cells")
        weak = sig.get("weak_cells", [])
        if weak:
            df_w = pd.DataFrame(weak, columns=["cell_id", "bad_samples"])
            st.dataframe(df_w.head(20), use_container_width=True,
                         hide_index=True, height=250)
            csv_download(df_w, "sigint_weak_cells.csv")
        else:
            st.success("No weak cells found.")

    # ==================================================================
    # TAB 7 — SPECIAL LINES
    # ==================================================================
    with tabs[7]:
        st.subheader("🔑 Special Lines & Privileged Access")

        if "line_class" not in subs_f.columns:
            st.warning("Database does not contain special-line fields. Please re-run the simulator.")
        else:
            sp = subs_f[subs_f["line_class"] != "Normal"]
            g1, g2, g3, g4, g5 = st.columns(5)
            with g1: kpi("Special Lines",   fmt_num(len(sp)), "Non-Normal class", "#22c55e")
            with g2: kpi("Filter Bypass",
                         fmt_num(int(subs_f["filter_bypass"].sum())),
                         "Unfiltered intl internet", "#f59e0b")
            with g3: kpi("CLIR Enabled",
                         fmt_num(int(subs_f["clir_enabled"].sum())),
                         "No Caller ID", "#0ea5e9")
            with g4: kpi("CLIR Override",
                         fmt_num(int(subs_f["clir_override"].sum())),
                         "Can spoof caller ID", "#ef4444")
            with g5: kpi("Lawful Intercept",
                         fmt_num(int(subs_f["lawful_intercept"].sum())),
                         "LI-flagged", "#a855f7")

            st.write("")

            c1, c2 = st.columns(2)

            with c1:
                lc = subs_f["line_class"].value_counts().reset_index()
                lc.columns = ["line_class", "count"]
                fig = px.pie(lc, names="line_class", values="count", hole=0.55,
                             title="Subscriber Distribution by Line Class",
                             color="line_class",
                             color_discrete_map={
                                 "Normal":"#94a3b8", "VIP":"#22c55e",
                                 "Government":"#ef4444", "Corporate":"#0ea5e9",
                                 "Emergency":"#f59e0b", "Test":"#a855f7"})
                fig.update_layout(height=350)
                _chart(fig, use_container_width=True)

            with c2:
                qos = subs_f["priority_qos"].value_counts().sort_index().reset_index()
                qos.columns = ["qos", "count"]
                fig = px.bar(qos, x="qos", y="count",
                             title="Priority QoS Distribution (0=lowest, 9=highest)",
                             color="count", color_continuous_scale="Turbo")
                fig.update_layout(height=350, coloraxis_showscale=False,
                                  xaxis=dict(dtick=1),
                                  xaxis_title="QoS Class", yaxis_title="Subscribers")
                _chart(fig, use_container_width=True)

            st.markdown("#### 📊 Capabilities Matrix by Line Class")
            cap = subs_f.groupby("line_class").agg(
                count=("msisdn", "count"),
                intl_access=("international_access", "sum"),
                filter_bypass=("filter_bypass", "sum"),
                clir=("clir_enabled", "sum"),
                clir_override=("clir_override", "sum"),
                lawful=("lawful_intercept", "sum"),
                direct=("direct_routing", "sum"),
                avg_qos=("priority_qos", "mean"),
            ).round(2).reset_index()
            st.dataframe(cap, use_container_width=True, hide_index=True)
            csv_download(cap, "special_lines_matrix.csv")

            st.divider()

            st.markdown("### 📡 Special-Line Traffic (from CDR)")

            if "line_class" in cdrs_f.columns and len(cdrs_f):
                clir_used = cdrs_f[cdrs_f["clir_used"] == 1]
                t1, t2 = st.columns(2)

                with t1:
                    if len(clir_used):
                        cl = clir_used.groupby("line_class").size().reset_index(name="count")
                        fig = px.bar(cl, x="line_class", y="count",
                                     title="CLIR (No-Caller-ID) Usage by Line Class",
                                     color="count", color_continuous_scale="Blues")
                        fig.update_layout(height=340, coloraxis_showscale=False,
                                          xaxis_title="", yaxis_title="Calls")
                        _chart(fig, use_container_width=True)
                    else:
                        st.info("No CLIR usage found.")

                with t2:
                    rt = cdrs_f["routing_class"].value_counts().reset_index()
                    rt.columns = ["routing_class", "count"]
                    fig = px.pie(rt, names="routing_class", values="count", hole=0.5,
                                 title="Routing Class Mix",
                                 color="routing_class",
                                 color_discrete_map={
                                     "Normal":"#94a3b8", "Priority":"#22c55e",
                                     "Direct":"#ef4444", "International":"#0ea5e9"})
                    fig.update_layout(height=340)
                    _chart(fig, use_container_width=True)

                intl = cdrs_f[cdrs_f["international"] == 1]
                if len(intl):
                    intl_h = intl.groupby("hour").size().reset_index(name="count")
                    fig = px.line(intl_h, x="hour", y="count", markers=True,
                                  title="International Traffic by Hour (whitelisted / bypass)")
                    fig.update_traces(line_color="#0ea5e9")
                    fig.update_layout(height=320, xaxis=dict(dtick=1),
                                      xaxis_title="Hour", yaxis_title="Sessions")
                    _chart(fig, use_container_width=True)

                fv = cdrs_f.groupby(["filter_applied", "international"]).size().reset_index(name="count")
                fv["label"] = fv.apply(
                    lambda r: ("Filtered" if r["filter_applied"] else "Unfiltered") +
                              (" / Intl" if r["international"] else " / Domestic"), axis=1)
                fig = px.bar(fv, x="label", y="count",
                             title="Filtered vs Unfiltered Traffic",
                             color="label")
                fig.update_layout(height=340, showlegend=False,
                                  xaxis_title="", yaxis_title="Records")
                _chart(fig, use_container_width=True)

            st.divider()

            st.markdown("### 🕵️ Special-Line SIGINT Findings")

            f1, f2, f3 = st.columns(3)
            with f1:
                abuse = sig.get("clir_abuse", [])
                kpi("CLIR Abuse Events", fmt_num(len(abuse)),
                    "Unauthorized no-caller-ID", "#ef4444")
            with f2:
                bypass = sig.get("filter_bypass_users", [])
                kpi("Top Bypass Users", fmt_num(len(bypass)),
                    "Heavy unfiltered traffic", "#f59e0b")
            with f3:
                prio = sig.get("priority_by_class", {})
                kpi("Priority Classes", fmt_num(len(prio)),
                    "Active priority users", "#22c55e")

            st.write("")

            st.markdown("#### ⚠️ Unauthorized CLIR Usage")
            abuse = sig.get("clir_abuse", [])
            if abuse:
                df_ab = pd.DataFrame(abuse)
                st.dataframe(df_ab, use_container_width=True, hide_index=True, height=250)
                csv_download(df_ab, "clir_abuse.csv")
            else:
                st.success("No CLIR abuse detected.")

            st.markdown("#### ⚠️ Top Filter-Bypass Users (Unfiltered International)")
            bypass = sig.get("filter_bypass_users", [])
            if bypass:
                df_by = pd.DataFrame(bypass, columns=["msisdn", "unfiltered_sessions"])
                fig = px.bar(df_by, x="msisdn", y="unfiltered_sessions",
                             title="Top MSISDNs by Unfiltered International Sessions",
                             color="unfiltered_sessions",
                             color_continuous_scale="OrRd")
                fig.update_layout(height=340, coloraxis_showscale=False,
                                  xaxis_title="MSISDN", yaxis_title="Sessions")
                _chart(fig, use_container_width=True)
                st.dataframe(df_by, use_container_width=True, hide_index=True)
                csv_download(df_by, "filter_bypass_users.csv")
            else:
                st.info("No filter-bypass traffic recorded.")

            st.markdown("#### 🌍 Top International Traffic Users")
            intl_users = sig.get("top_intl_users", [])
            if intl_users:
                df_iu = pd.DataFrame(intl_users, columns=["msisdn", "intl_sessions"])
                st.dataframe(df_iu, use_container_width=True, hide_index=True)
                csv_download(df_iu, "top_intl_users.csv")

            st.markdown("#### 📋 Full Special Line Subscriber List")
            sp_full = subs_f[subs_f["line_class"] != "Normal"].copy()
            st.dataframe(sp_full, use_container_width=True, hide_index=True, height=350)
            csv_download(sp_full, "special_lines_full.csv")

    # ==================================================================
    # TAB 8 — ENCRYPTION
    # ==================================================================
    with tabs[8]:
        st.subheader("🔐 End-to-End Encryption (Special Lines)")

        if "e2e_enabled" not in subs_f.columns:
            st.warning("Encryption fields not found. Re-run the simulator.")
        else:
            enc_subs = subs_f[subs_f["e2e_enabled"] == 1]
            cov = sig.get("encryption_coverage", {})
            fails = sig.get("encryption_failures", [])

            e1, e2, e3, e4 = st.columns(4)
            with e1: kpi("E2E-Enabled Lines", fmt_num(len(enc_subs)),
                         "Encrypted subscribers", "#22c55e")
            with e2: kpi("Mandatory Lines",
                         fmt_num(int(subs_f["encryption_required"].sum())),
                         "Gov / Emergency", "#ef4444")
            with e3: kpi("Cipher Suites",
                         fmt_num(len(sig.get("cipher_usage", {}))),
                         "Active algorithms", "#0ea5e9")
            with e4: kpi("Encryption Failures", fmt_num(len(fails)),
                         "Handshake errors", "#f59e0b")

            st.write("")

            c1, c2 = st.columns(2)

            with c1:
                if cov:
                    cov_df = pd.DataFrame([
                        {"line_class": k, **v} for k, v in cov.items()
                    ])
                    fig = px.bar(cov_df, x="line_class", y="coverage_pct",
                                 title="Encryption Coverage by Line Class (%)",
                                 color="coverage_pct", color_continuous_scale="Greens",
                                 text="coverage_pct")
                    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                    fig.update_layout(height=350, coloraxis_showscale=False,
                                      yaxis_range=[0, 105],
                                      xaxis_title="", yaxis_title="Coverage %")
                    _chart(fig, use_container_width=True)

            with c2:
                cu = sig.get("cipher_usage", {})
                if cu:
                    cu_df = pd.DataFrame(list(cu.items()), columns=["cipher", "count"])
                    fig = px.pie(cu_df, names="cipher", values="count",
                                 hole=0.55, title="Cipher Suite Usage")
                    fig.update_layout(height=350)
                    _chart(fig, use_container_width=True)

            st.markdown("#### 🔑 Cipher Suite Details")
            cipher_info = pd.DataFrame([
                {"cipher_suite": k, "key_strength": v["strength"],
                 "quantum_safe": v["quantum_safe"]}
                for k, v in CIPHER_SUITES.items()
            ])
            st.dataframe(cipher_info, use_container_width=True, hide_index=True)
            csv_download(cipher_info, "cipher_suites.csv")

            st.markdown("#### 🔄 Key Distribution (Top 20)")
            ku = sig.get("key_usage", {})
            if ku:
                ku_df = pd.DataFrame(list(ku.items()), columns=["key_id", "usage"])
                st.dataframe(ku_df, use_container_width=True, hide_index=True, height=250)
                csv_download(ku_df, "key_usage.csv")

            st.markdown("#### ⚠️ Encryption Failures")
            if fails:
                df_f = pd.DataFrame(fails)
                fig = px.bar(df_f.groupby("line_class").size().reset_index(name="count"),
                             x="line_class", y="count",
                             title="Encryption Failures by Line Class",
                             color="count", color_continuous_scale="Reds")
                fig.update_layout(height=320, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="")
                _chart(fig, use_container_width=True)
                st.dataframe(df_f, use_container_width=True, hide_index=True, height=250)
                csv_download(df_f, "encryption_failures.csv")
            else:
                st.success("No encryption failures detected.")

            st.markdown("#### 📋 E2E-Enabled Subscribers")
            if len(enc_subs):
                st.dataframe(
                    enc_subs[["msisdn", "imsi", "line_class", "cipher_suite",
                              "key_id", "key_rotation_days"]],
                    use_container_width=True, hide_index=True, height=300)
                csv_download(enc_subs, "e2e_subscribers.csv")

    # ==================================================================
    # TAB 9 — ALERTS & SMS
    # ==================================================================
    with tabs[9]:
        st.subheader("🚨 Alert Engine & SMS Notifications")

        if alerts_df.empty:
            st.info("No alerts recorded. Run the simulator.")
        else:
            fa1, fa2, fa3 = st.columns(3)
            with fa1:
                sev_filter = st.multiselect(
                    "Severity",
                    ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    default=["CRITICAL", "HIGH", "MEDIUM", "LOW"])
            with fa2:
                type_filter = st.multiselect(
                    "Alert Type",
                    sorted(alerts_df["alert_type"].unique()),
                    default=sorted(alerts_df["alert_type"].unique()))
            with fa3:
                only_unack = st.checkbox("Only Unacknowledged", value=False)

            adf = alerts_df[
                alerts_df["severity"].isin(sev_filter) &
                alerts_df["alert_type"].isin(type_filter)
            ]
            if only_unack:
                adf = adf[adf["ack"] == 0]

            a1, a2, a3, a4, a5 = st.columns(5)
            with a1: kpi("Total Alerts", fmt_num(len(alerts_df)), "All time", "#0ea5e9")
            with a2:
                cr = int((alerts_df["severity"] == "CRITICAL").sum())
                kpi("CRITICAL", fmt_num(cr), "Immediate action", "#ef4444")
            with a3:
                hi = int((alerts_df["severity"] == "HIGH").sum())
                kpi("HIGH", fmt_num(hi), "Attention needed", "#f59e0b")
            with a4:
                kpi("SMS Sent", fmt_num(int(alerts_df["sms_sent"].sum())),
                    "Dispatched to SOC", "#22c55e")
            with a5:
                unack = int((alerts_df["ack"] == 0).sum())
                kpi("Unacknowledged", fmt_num(unack), "Pending review", "#a855f7")

            st.write("")

            ch1, ch2 = st.columns(2)
            with ch1:
                sv = alerts_df["severity"].value_counts().reset_index()
                sv.columns = ["severity", "count"]
                fig = px.pie(sv, names="severity", values="count", hole=0.55,
                             title="Alerts by Severity",
                             color="severity",
                             color_discrete_map={
                                 "CRITICAL":"#ef4444","HIGH":"#f59e0b",
                                 "MEDIUM":"#0ea5e9","LOW":"#94a3b8"})
                fig.update_layout(height=340)
                _chart(fig, use_container_width=True)
            with ch2:
                tp = alerts_df["alert_type"].value_counts().reset_index()
                tp.columns = ["alert_type", "count"]
                fig = px.bar(tp, x="count", y="alert_type", orientation="h",
                             title="Alerts by Type",
                             color="count", color_continuous_scale="Reds")
                fig.update_layout(height=340, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="")
                _chart(fig, use_container_width=True)

            alerts_df["ts"] = pd.to_datetime(alerts_df["timestamp"], errors="coerce")
            timeline = alerts_df.set_index("ts").resample("h").size().reset_index(name="count")
            if len(timeline):
                fig = px.bar(timeline, x="ts", y="count",
                             title="Alert Timeline (hourly)",
                             color="count", color_continuous_scale="OrRd")
                fig.update_layout(height=300, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="Alerts")
                _chart(fig, use_container_width=True)

            st.markdown("#### 📋 Alert Log")
            st.dataframe(
                adf[["alert_id","timestamp","severity","alert_type",
                     "msisdn","description","sms_sent","sms_to","ack"]],
                use_container_width=True, hide_index=True, height=400)
            csv_download(adf, "alerts_filtered.csv")

            st.divider()

            st.markdown("### 📲 SMS Delivery Log")
            if not sms_alerts_df.empty:
                sms_filtered = sms_alerts_df[
                    sms_alerts_df["alert_id"].isin(adf["alert_id"])]
                st.dataframe(sms_filtered, use_container_width=True,
                             hide_index=True, height=300)
                csv_download(sms_filtered, "sms_log.csv")

                rp = sms_alerts_df.groupby("recipient").size().reset_index(name="count")
                fig = px.bar(rp, x="recipient", y="count",
                             title="SMS Dispatched per SOC Recipient",
                             color="count", color_continuous_scale="Greens")
                fig.update_layout(height=320, coloraxis_showscale=False,
                                  xaxis_title="Recipient MSISDN", yaxis_title="SMS")
                _chart(fig, use_container_width=True)
            else:
                st.info("No SMS delivered yet.")

            st.divider()

            st.markdown("### 📱 SMS Preview (Latest 5)")
            for _, row in adf.head(5).iterrows():
                sev = row["severity"]
                color = {"CRITICAL":"#ef4444","HIGH":"#f59e0b",
                         "MEDIUM":"#0ea5e9","LOW":"#94a3b8"}.get(sev, "#94a3b8")
                st.markdown(f"""
                <div style="border-left:4px solid {color};
                            background:#f8fafc; padding:12px 16px;
                            border-radius:10px; margin-bottom:10px;">
                  <div style="font-size:12px;color:#64748b;">
                    TO: <b>{row['sms_to']}</b> | {row['timestamp']}
                  </div>
                  <div style="font-size:14px;color:#0f172a;margin-top:6px;">
                    {row['sms_body']}
                  </div>
                </div>
                """, unsafe_allow_html=True)

    # ==================================================================
    # TAB 10 — SUBSCRIBERS
    # ==================================================================
    with tabs[10]:
        st.subheader("Subscriber Analytics")

        if not len(subs_f):
            st.info("No subscriber data available.")
        else:
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                plan_count = subs_f["plan"].value_counts().reset_index()
                plan_count.columns = ["plan", "count"]
                fig = px.bar(plan_count, x="count", y="plan", orientation="h",
                             title="Plan Distribution",
                             color="count", color_continuous_scale="Blues")
                fig.update_layout(height=340, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="")
                _chart(fig, use_container_width=True)
            with sc2:
                fig = px.histogram(subs_f, x="risk_score", nbins=40,
                                   title="Risk Score Distribution",
                                   color_discrete_sequence=["#f59e0b"])
                fig.update_layout(height=340, xaxis_title="Risk Score", yaxis_title="Count")
                _chart(fig, use_container_width=True)
            with sc3:
                roam = subs_f["roaming_enabled"].value_counts().reset_index()
                roam.columns = ["roaming", "count"]
                roam["label"] = roam["roaming"].map({0: "Disabled", 1: "Enabled"})
                fig = px.pie(roam, names="label", values="count", hole=0.55,
                             title="Roaming Status",
                             color="label",
                             color_discrete_map={"Enabled": "#22c55e",
                                                 "Disabled": "#94a3b8"})
                fig.update_layout(height=340)
                _chart(fig, use_container_width=True)

            st.markdown("#### 📋 Subscriber Sample List")
            st.dataframe(subs_f.head(500), use_container_width=True,
                         height=350, hide_index=True)
            csv_download(subs_f, "subscribers_filtered.csv")

    # ==================================================================
    # TAB 11 — REPORT
    # ==================================================================
    with tabs[11]:
        st.subheader("📄 Management Report")

        report_path = os.path.join(os.path.dirname(DB_PATH), "report.txt")
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report_text = f.read()
            st.text_area("Report Content (report.txt)", report_text, height=600)
            st.download_button("⬇️ Download Text Report", report_text.encode("utf-8"),
                               "report.txt", "text/plain")
        else:
            st.info("report.txt not found. Please run the simulator.")

        st.divider()
        st.markdown("#### 📦 SIGINT Findings (JSON Summary)")
        st.json(sig, expanded=False)

        st.markdown("#### 📦 OSINT Findings (JSON Summary)")
        st.json(osi, expanded=False)


    # ==================================================================
    # TAB 12 — ATTACK SIMULATION (PATCH-02)
    # ==================================================================
    with tabs[12]:
        st.subheader("🛡️ Attack Simulation Results")
        _atk_sc = data.get("attack_scenarios", pd.DataFrame())
        _atk_ev = data.get("attack_events", pd.DataFrame())
        if _atk_sc is None or _atk_sc.empty:
            st.info("No attack data. Run `python telecom_attack.py` "
                    "or re-run the simulator.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1: kpi("Scenarios",   fmt_num(len(_atk_sc)), "Total")
            with c2: kpi("Events",      fmt_num(len(_atk_ev)), "Samples")
            with c3:
                blk = int((_atk_sc["status"] == "BLOCKED").sum())
                kpi("Blocked", f"{blk}/{len(_atk_sc)}",
                    f"{blk/max(1,len(_atk_sc))*100:.0f}%", "#22c55e")
            with c4:
                suc = int((_atk_sc["status"] == "SUCCESS").sum())
                kpi("Attacker Success", f"{suc}", "Unblocked", "#ef4444")

            st.write("")
            st.markdown("### Status Distribution")
            fig = px.pie(_atk_sc, names="status", hole=0.55,
                         color="status",
                         color_discrete_map={"BLOCKED":"#22c55e","DETECTED":"#f59e0b",
                                             "SUCCESS":"#ef4444","ONGOING":"#0ea5e9"})
            fig.update_layout(height=340)
            _chart(fig, use_container_width=True)

            st.markdown("### Attack Type Distribution")
            tc = _atk_sc["attack_type"].value_counts().reset_index()
            tc.columns = ["attack_type", "count"]
            fig = px.bar(tc, x="count", y="attack_type", orientation="h",
                         color="count", color_continuous_scale="Reds")
            fig.update_layout(height=400, coloraxis_showscale=False,
                              xaxis_title="", yaxis_title="")
            _chart(fig, use_container_width=True)

            st.markdown("### Severity × Status Matrix")
            if not _atk_ev.empty:
                fig = px.line(_atk_ev.sort_values("ts"), x="ts", y="latency_ms",
                              color="attack_type", markers=False)
                fig.update_layout(height=380, xaxis_title="", yaxis_title="Latency (ms)")
                _chart(fig, use_container_width=True)

            st.markdown("### MTTD Distribution")
            if not _atk_ev.empty and _atk_ev["mttd_sec"].notna().any():
                fig = px.histogram(_atk_ev.dropna(subset=["mttd_sec"]),
                                   x="mttd_sec", nbins=40,
                                   color_discrete_sequence=["#f59e0b"])
                fig.update_layout(height=340, xaxis_title="MTTD (sec)", yaxis_title="")
                _chart(fig, use_container_width=True)

            st.markdown("### MTTR Distribution")
            if not _atk_ev.empty and _atk_ev["mttr_sec"].notna().any():
                fig = px.histogram(_atk_ev.dropna(subset=["mttr_sec"]),
                                   x="mttr_sec", nbins=40,
                                   color_discrete_sequence=["#22c55e"])
                fig.update_layout(height=340, xaxis_title="MTTR (sec)", yaxis_title="")
                _chart(fig, use_container_width=True)

            st.markdown("### Full Scenario Table")
            st.dataframe(_atk_sc, use_container_width=True,
                         hide_index=True, height=350)




# ------------------------------------------------------------------
# Entry point — runs under `streamlit run`
# ------------------------------------------------------------------
if __name__ == "__main__":
    main()
