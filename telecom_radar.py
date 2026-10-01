# -*- coding: utf-8 -*-
"""
================================================================
 TELECOM RADAR v2.0
 Statistical Analytics Dashboard (Cloudflare Radar style)
 
 Features:
 + Period comparison (current vs previous)
 + Anomaly detection (Z-score based)
 + Geographic interactive filters
 + Auto-refresh (real-time mode)
 + PDF export per tab
 + 13 analytic tabs
 Fully local | Reads from telecom_sim.db
================================================================
"""
import os, io, json, sqlite3, time, base64
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------------------------------------------------------------
# OPTIONAL IMPORTS
# ------------------------------------------------------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, PageBreak)
    HAS_PDF = True
except ImportError:
    HAS_PDF = False


# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
DB_PATH  = "telecom_sim_output/telecom_sim.db"
OPERATOR = "TELECOM"
ORANGE = "#f6821f"
BLUE   = "#0ea5e9"
GREEN  = "#22c55e"
RED    = "#ef4444"
PURPLE = "#a855f7"
GRAY   = "#94a3b8"
DARK   = "#0f172a"

def main():
    from telecom_ui_common import (
        chart as _chart,
        csv_download,
        db_mtime,
        load_data,
        ORANGE, BLUE, GREEN, RED, PURPLE, GRAY, DARK,
    )
    # Imported here so that plain `import
    # telecom_radar` stays silent (streamlit_autorefresh triggers a
    # ScriptRunContext warning at import time).
    try:
        from streamlit_autorefresh import st_autorefresh
        HAS_AUTOREFRESH = True
    except ImportError:
        st_autorefresh = None
        HAS_AUTOREFRESH = False

    st.set_page_config(
        page_title="TELECOM Radar",
        page_icon="📡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Auto-key wrapper for st.download_button
    _dl_counter = {"n": 0}
    def _dl(label, data=None, file_name=None, mime=None, **kwargs):
        _dl_counter["n"] += 1
        kwargs.setdefault("key", f"radar_dl_{_dl_counter['n']}")
        return st.download_button(label, data=data, file_name=file_name,
                                  mime=mime, **kwargs)


    # ------------------------------------------------------------------
    # CSS
    # ------------------------------------------------------------------
    st.markdown("""
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
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # DATA LOADER
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def fmt(n, decimals=0):
        try: n = float(n)
        except Exception: return str(n)
        if abs(n) >= 1e9: return f"{n/1e9:.{decimals+1}f}B"
        if abs(n) >= 1e6: return f"{n/1e6:.{decimals+1}f}M"
        if abs(n) >= 1e3: return f"{n/1e3:.{decimals+1}f}K"
        return f"{n:,.{decimals}f}"

    def stat_card(label, value, delta=None, delta_pct=None, sub="", compare_on=False):
        delta_html = ""
        if compare_on and delta is not None:
            cls = "stat-delta-up" if delta > 0 else ("stat-delta-down" if delta < 0 else "stat-delta-flat")
            arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
            pct = f" ({delta_pct:+.1f}%)" if delta_pct is not None else ""
            delta_html = f'<div class="{cls}">{arrow} {abs(delta):,.0f}{pct} vs prev</div>'
        sub_html = f'<div class="stat-sub">{sub}</div>' if sub else ""
        st.markdown(f"""
        <div class="stat-card">
          <div class="stat-label">{label}</div>
          <div class="stat-value">{value}</div>
          {delta_html}{sub_html}
        </div>
        """, unsafe_allow_html=True)

    def threat_card(label, value, sub=""):
        sub_html = f'<div style="font-size:12px;color:#7f1d1d;margin-top:4px;">{sub}</div>' if sub else ""
        st.markdown(f"""
        <div class="threat-card">
          <div class="threat-label">{label}</div>
          <div class="threat-value">{value}</div>
          {sub_html}
        </div>
        """, unsafe_allow_html=True)

    def anomaly_card(label, value, sub=""):
        sub_html = f'<div style="font-size:12px;color:#9a3412;margin-top:4px;">{sub}</div>' if sub else ""
        st.markdown(f"""
        <div class="anomaly-card">
          <div class="anomaly-label">{label}</div>
          <div class="anomaly-value">{value}</div>
          {sub_html}
        </div>
        """, unsafe_allow_html=True)

    def section(title):
        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

    def safe_chart(fig, **kwargs):
        try:
            _chart(fig, use_container_width=True, **kwargs)
        except TypeError:
            _chart(fig, **kwargs)

    def csv_btn(df, filename, label="⬇️ CSV"):
        _dl(label,
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=filename, mime="text/csv")

    # ------------------------------------------------------------------
    # ANOMALY DETECTION
    # ------------------------------------------------------------------
    def detect_anomalies(cdrs_df: pd.DataFrame,
                         cells_df: pd.DataFrame,
                         sig_findings: dict) -> List[Dict]:
        anomalies = []
        if cdrs_df is None or not len(cdrs_df):
            return anomalies

        # 1. Hourly traffic anomalies
        hourly = cdrs_df.groupby("hour").size()
        if len(hourly) > 3:
            mean, std = hourly.mean(), hourly.std()
            if std > 0:
                for hour, val in hourly.items():
                    z = (val - mean) / std
                    if abs(z) > 2.0:
                        anomalies.append({
                            "type": "Hourly Traffic",
                            "entity": f"Hour {hour:02d}:00",
                            "value": int(val),
                            "expected": int(mean),
                            "z_score": round(z, 2),
                            "severity": "HIGH" if abs(z) > 2.5 else "MEDIUM",
                            "desc": f"Traffic {z:+.2f}σ from mean ({int(mean)})"
                        })

        # 2. City traffic anomalies
        city_counts = cdrs_df.groupby("city").size()
        if len(city_counts) > 3:
            mean, std = city_counts.mean(), city_counts.std()
            if std > 0:
                for city, val in city_counts.items():
                    z = (val - mean) / std
                    if abs(z) > 2.0:
                        anomalies.append({
                            "type": "City Traffic",
                            "entity": city,
                            "value": int(val),
                            "expected": int(mean),
                            "z_score": round(z, 2),
                            "severity": "HIGH" if abs(z) > 2.5 else "MEDIUM",
                            "desc": f"Traffic {z:+.2f}σ from mean"
                        })

        # 3. Weak cells
        weak = sig_findings.get("weak_cells", [])
        if weak:
            vals = np.array([c[1] for c in weak])
            if len(vals) > 1:
                mean, std = vals.mean(), vals.std()
                if std > 0:
                    for cell_id, val in weak:
                        z = (val - mean) / std
                        if abs(z) > 2.0:
                            anomalies.append({
                                "type": "Weak Cell",
                                "entity": cell_id,
                                "value": int(val),
                                "expected": int(mean),
                                "z_score": round(z, 2),
                                "severity": "HIGH" if abs(z) > 2.5 else "MEDIUM",
                                "desc": f"Bad samples {z:+.2f}σ from mean"
                            })

        # 4. Encryption failures spike
        enc_fails = sig_findings.get("encryption_failures", [])
        if len(enc_fails) > 5:
            anomalies.append({
                "type": "Encryption Failures",
                "entity": "System-wide",
                "value": len(enc_fails),
                "expected": 5,
                "z_score": round((len(enc_fails) - 5) / 3, 2),
                "severity": "HIGH" if len(enc_fails) > 20 else "MEDIUM",
                "desc": f"Unusually high failure count ({len(enc_fails)})"
            })

        # 5. CLIR abuse spike
        clir_abuse = sig_findings.get("clir_abuse", [])
        if len(clir_abuse) > 20:
            anomalies.append({
                "type": "CLIR Abuse Spike",
                "entity": "System-wide",
                "value": len(clir_abuse),
                "expected": 10,
                "z_score": round((len(clir_abuse) - 10) / 5, 2),
                "severity": "HIGH" if len(clir_abuse) > 40 else "MEDIUM",
                "desc": f"Unauthorized CLIR events ({len(clir_abuse)})"
            })

        # 6. Voice bearer distribution anomaly
        if "voice_bearer" in cdrs_df.columns:
            v = cdrs_df[cdrs_df["call_type"] == "voice"]
            if len(v):
                dist = v["voice_bearer"].value_counts(normalize=True)
                tech_mix = cdrs_df["tech"].value_counts(normalize=True)
                modern = tech_mix.get("4G", 0) + tech_mix.get("5G", 0)
                csfb_pct = dist.get("CSFB", 0)
                if csfb_pct > 0.8 and modern > 0.5:
                    anomalies.append({
                        "type": "VoLTE Fallback",
                        "entity": "Voice routing",
                        "value": f"{csfb_pct*100:.0f}%",
                        "expected": "20-40%",
                        "z_score": 2.5,
                        "severity": "MEDIUM",
                        "desc": f"High CSFB ({csfb_pct*100:.0f}%) despite {modern*100:.0f}% modern tech"
                    })

        return anomalies

    # ------------------------------------------------------------------
    # PDF EXPORT
    # ------------------------------------------------------------------
    def build_pdf(title: str, sections: List[Dict]) -> Optional[bytes]:
        if not HAS_PDF:
            return None
        try:
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4,
                                     leftMargin=0.6*inch, rightMargin=0.6*inch,
                                     topMargin=0.6*inch, bottomMargin=0.6*inch)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("Title", parent=styles["Title"],
                                           textColor=rl_colors.HexColor("#0f172a"),
                                           fontSize=20, spaceAfter=8)
            h2_style = ParagraphStyle("H2", parent=styles["Heading2"],
                                        textColor=rl_colors.HexColor("#f6821f"),
                                        fontSize=14, spaceBefore=12, spaceAfter=6)
            body_style = styles["BodyText"]
            body_style.fontSize = 10
            body_style.textColor = rl_colors.HexColor("#334155")

            story = []
            story.append(Paragraph(title, title_style))
            story.append(Paragraph(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                f"Operator: {OPERATOR} | Mode: LOCAL-ONLY", body_style))
            story.append(Spacer(1, 12))

            for s in sections:
                if s.get("heading"):
                    story.append(Paragraph(s["heading"], h2_style))
                if s.get("text"):
                    story.append(Paragraph(s["text"], body_style))
                    story.append(Spacer(1, 6))
                if s.get("table") is not None and len(s["table"]) > 0:
                    df = s["table"].head(20)
                    data = [list(df.columns)] + df.astype(str).values.tolist()
                    t = Table(data, hAlign="LEFT")
                    t.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#f6821f")),
                        ("TEXTCOLOR",  (0, 0), (-1, 0), rl_colors.white),
                        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE",   (0, 0), (-1, -1), 8),
                        ("GRID",       (0, 0), (-1, -1), 0.25, rl_colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                         [rl_colors.white, rl_colors.HexColor("#f8fafc")]),
                        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                        ("PADDING",    (0, 0), (-1, -1), 4),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 12))

            doc.build(story)
            return buf.getvalue()
        except Exception:
            return None

    def pdf_download_button(pdf_bytes: Optional[bytes], filename: str):
        if pdf_bytes is None:
            st.caption("⚠️ Install `reportlab` to enable PDF export.")
            return
        _dl("📄 Export PDF", pdf_bytes, filename,
                            "application/pdf")

    # ------------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------------
    st.markdown(f"""
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
    """, unsafe_allow_html=True)
    st.write("")

    # ------------------------------------------------------------------
    # DATA
    # ------------------------------------------------------------------
    if not os.path.exists(DB_PATH):
        st.error(f"⚠️ Database not found at `{DB_PATH}`. Run `telecom_net_sim.py` first.")
        st.stop()

    data = load_data(DB_PATH, db_mtime(DB_PATH))
    cells       = data["cells"]
    cores       = data["cores"]
    subs        = data["subscribers"]
    cdrs        = data["cdrs"]
    osint_reg   = data["osint_reg"]
    osint_comp  = data["osint_comp"]
    alerts_df   = data["alerts"]
    sig         = data.get("findings", {}).get("SIGINT", {})
    osi         = data.get("findings", {}).get("OSINT", {})

    # ------------------------------------------------------------------
    # SIDEBAR
    # ------------------------------------------------------------------
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
                value=30, key="radar_interval")
            if HAS_AUTOREFRESH:
                st_autorefresh(interval=interval * 1000, key="radar_autorefresh")
                st.markdown('<span class="live-badge">● LIVE</span>',
                            unsafe_allow_html=True)
                st.caption(f"Refreshing every {interval}s")
            else:
                st.warning("Install `streamlit-autorefresh` for live mode.")

        st.divider()
        st.markdown("### 🎛️ Filters")

        all_cities = sorted(cells["city"].unique())
        sel_cities = st.multiselect("Cities", all_cities, default=all_cities,
                                     key="radar_cities")

        all_techs = sorted(cells["tech"].unique())
        sel_techs = st.multiselect("Technology", all_techs, default=all_techs,
                                    key="radar_techs")

        if len(cdrs):
            min_d = cdrs["ts"].min().date()
            max_d = cdrs["ts"].max().date()
            date_range = st.date_input("Date Range", (min_d, max_d),
                                        key="radar_dates")
        else:
            date_range = None

        st.divider()
        st.markdown("### ⚖️ Comparison")
        compare_mode = st.toggle("Enable Period Comparison",
                                  value=False, key="radar_compare")
        if compare_mode:
            st.caption("Splits data into two halves by time")
            split_ratio = st.slider("Split ratio", 0.3, 0.7, 0.5, 0.05,
                                     key="radar_split")
        else:
            split_ratio = 0.5

        st.divider()
        st.caption(f"📊 {len(cdrs):,} CDRs")
        st.caption(f"🗼 {len(cells):,} cells")
        st.caption(f"👥 {len(subs):,} subscribers")

    # Apply filters
    mask_cells = cells["city"].isin(sel_cities) & cells["tech"].isin(sel_techs)
    cells_f = cells[mask_cells].copy()

    mask_cdr = cdrs["city"].isin(sel_cities) & cdrs["tech"].isin(sel_techs)
    if date_range and len(date_range) == 2:
        d1 = pd.to_datetime(date_range[0])
        d2 = pd.to_datetime(date_range[1]) + timedelta(days=1)
        mask_cdr &= (cdrs["ts"] >= d1) & (cdrs["ts"] < d2)
    cdrs_f = cdrs[mask_cdr].copy()

    subs_f = subs[subs["city"].isin(sel_cities)].copy() if "city" in subs.columns else subs.copy()

    # Period split
    prev_df, curr_df = None, None
    if len(cdrs_f):
        cdrs_f_sorted = cdrs_f.sort_values("ts").reset_index(drop=True)
        split_idx = int(len(cdrs_f_sorted) * split_ratio)
        prev_df = cdrs_f_sorted.iloc[:split_idx]
        curr_df = cdrs_f_sorted.iloc[split_idx:]

    def period_stats(df):
        if df is None or not len(df):
            return {"cdr": 0, "bytes": 0, "voice": 0, "sms": 0, "mms": 0,
                    "data": 0, "rcs": 0, "minutes": 0}
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

    def delta_pct(curr, prev):
        if prev == 0:
            return None if curr == 0 else 100.0
        return (curr - prev) / prev * 100

    prev_stats = period_stats(prev_df) if compare_mode else None
    curr_stats = period_stats(curr_df) if compare_mode else None

    # Compute anomalies once
    anomalies = detect_anomalies(cdrs_f, cells_f, sig)

    # ------------------------------------------------------------------
    # TABS
    # ------------------------------------------------------------------
    tabs = st.tabs([
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
    ])

    # ==================================================================
    # TAB 0 — OVERVIEW
    # ==================================================================
    with tabs[0]:
        section("Global Summary")
        if compare_mode and curr_stats:
            c1, c2, c3, c4 = st.columns(4)
            with c1: stat_card("Total CDR", fmt(curr_stats["cdr"]),
                               curr_stats["cdr"]-prev_stats["cdr"],
                               delta_pct(curr_stats["cdr"], prev_stats["cdr"]),
                               "Current period", True)
            with c2: stat_card("Data Volume", f"{curr_stats['bytes']/1e9:.2f} GB",
                               (curr_stats["bytes"]-prev_stats["bytes"])/1e9,
                               delta_pct(curr_stats["bytes"], prev_stats["bytes"]),
                               "Current period", True)
            with c3: stat_card("Voice Calls", fmt(curr_stats["voice"]),
                               curr_stats["voice"]-prev_stats["voice"],
                               delta_pct(curr_stats["voice"], prev_stats["voice"]),
                               "Current period", True)
            with c4: stat_card("SMS", fmt(curr_stats["sms"]),
                               curr_stats["sms"]-prev_stats["sms"],
                               delta_pct(curr_stats["sms"], prev_stats["sms"]),
                               "Current period", True)
        else:
            total_cdr = len(cdrs_f)
            total_bytes = cdrs_f["bytes"].sum() if len(cdrs_f) else 0
            voice_calls = int((cdrs_f["call_type"] == "voice").sum()) if len(cdrs_f) else 0
            voice_minutes = cdrs_f.loc[cdrs_f["call_type"] == "voice", "duration_sec"].sum() / 60 if len(cdrs_f) else 0
            sms_count = int((cdrs_f["call_type"] == "sms").sum()) if len(cdrs_f) else 0
            c1, c2, c3, c4 = st.columns(4)
            with c1: stat_card("Total CDR", fmt(total_cdr), sub="Records")
            with c2: stat_card("Data Volume", f"{total_bytes/1e9:.2f} GB", sub="Traffic")
            with c3: stat_card("Voice Calls", fmt(voice_calls), sub=f"{fmt(voice_minutes)} min")
            with c4: stat_card("SMS", fmt(sms_count), sub="Messages")

        st.write("")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ec = sig.get("encryption_coverage", {})
            gov = ec.get("Government", {}).get("coverage_pct", 0)
            stat_card("Gov Encryption", f"{gov:.1f}%", sub="Coverage")
        with c2: stat_card("Cell Sites", fmt(len(cells_f)), sub=f"of {len(cells):,}")
        with c3: stat_card("Subscribers", fmt(len(subs_f)), sub="Active")
        with c4:
            cr = int((alerts_df["severity"] == "CRITICAL").sum()) if len(alerts_df) else 0
            stat_card("CRITICAL Alerts", fmt(cr), sub=f"of {len(alerts_df)} total")

        st.write("")
        section("Traffic Heat — City × Hour")
        if len(cdrs_f):
            pivot = cdrs_f.pivot_table(index="city", columns="hour",
                                        values="record_id", aggfunc="count").fillna(0)
            if not pivot.empty:
                fig = px.imshow(pivot, aspect="auto",
                                color_continuous_scale=["#f8fafc","#fbbf24","#f6821f","#dc2626"],
                                labels=dict(x="Hour of Day", y="City", color="Records"))
                fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

        st.write("")
        section("Top 10 Busiest Cells")
        top_cells = pd.DataFrame()
        if len(cdrs_f):
            top_cells = (cdrs_f.groupby("cell_id").size().reset_index(name="count")
                         .sort_values("count", ascending=False).head(10))
            top_cells = top_cells.merge(cells[["cell_id","tech","city"]], on="cell_id", how="left")
            fig = px.bar(top_cells, x="count", y="cell_id", orientation="h",
                         color="tech",
                         color_discrete_map={"2G":"#8888ff","3G":"#38bdf8",
                                             "4G":"#22c55e","5G":ORANGE,"6G":"#a855f7"},
                         hover_data=["city"])
            fig.update_layout(height=380, yaxis=dict(autorange="reversed"),
                              xaxis_title="CDR Count", yaxis_title="",
                              legend_title="Tech")
            safe_chart(fig)

        st.write("")
        if st.button("📄 Export Overview PDF", key="pdf_overview"):
            sections = [
                {"heading": "Overview Summary",
                 "text": f"Total CDRs: {len(cdrs_f):,} | "
                         f"Data: {cdrs_f['bytes'].sum()/1e9:.2f} GB | "
                         f"Cells: {len(cells_f):,} | Subscribers: {len(subs_f):,}"},
                {"heading": "Top Cells", "table": top_cells},
            ]
            pdf = build_pdf("TELECOM Radar — Overview", sections)
            pdf_download_button(pdf, "radar_overview.pdf")

    # ==================================================================
    # TAB 1 — PERIOD COMPARE
    # ==================================================================
    with tabs[1]:
        section("⚖️ Period Comparison")
        if not compare_mode:
            st.info("Enable **Period Comparison** in the sidebar to see this tab.")
        elif not len(cdrs_f):
            st.info("No data available.")
        else:
            prev_range = f"{prev_df['ts'].min().strftime('%Y-%m-%d')} → {prev_df['ts'].max().strftime('%Y-%m-%d')}"
            curr_range = f"{curr_df['ts'].min().strftime('%Y-%m-%d')} → {curr_df['ts'].max().strftime('%Y-%m-%d')}"
            st.markdown(f"""
            <span class="period-badge period-previous">PREVIOUS: {prev_range}</span>
            <span class="period-badge period-current">CURRENT: {curr_range}</span>
            """, unsafe_allow_html=True)
            st.write("")

            c1, c2, c3, c4 = st.columns(4)
            with c1: stat_card("Total CDR", fmt(curr_stats["cdr"]),
                               curr_stats["cdr"]-prev_stats["cdr"],
                               delta_pct(curr_stats["cdr"], prev_stats["cdr"]),
                               "Current vs prev", True)
            with c2: stat_card("Data Volume", f"{curr_stats['bytes']/1e9:.2f} GB",
                               (curr_stats["bytes"]-prev_stats["bytes"])/1e9,
                               delta_pct(curr_stats["bytes"], prev_stats["bytes"]),
                               "Current vs prev", True)
            with c3: stat_card("Voice Calls", fmt(curr_stats["voice"]),
                               curr_stats["voice"]-prev_stats["voice"],
                               delta_pct(curr_stats["voice"], prev_stats["voice"]),
                               "Current vs prev", True)
            with c4: stat_card("Talk Minutes", fmt(curr_stats["minutes"]),
                               curr_stats["minutes"]-prev_stats["minutes"],
                               delta_pct(curr_stats["minutes"], prev_stats["minutes"]),
                               "Current vs prev", True)

            st.write("")
            c1, c2, c3, c4 = st.columns(4)
            with c1: stat_card("SMS", fmt(curr_stats["sms"]),
                               curr_stats["sms"]-prev_stats["sms"],
                               delta_pct(curr_stats["sms"], prev_stats["sms"]),
                               "Current vs prev", True)
            with c2: stat_card("MMS", fmt(curr_stats["mms"]),
                               curr_stats["mms"]-prev_stats["mms"],
                               delta_pct(curr_stats["mms"], prev_stats["mms"]),
                               "Current vs prev", True)
            with c3: stat_card("Data Sessions", fmt(curr_stats["data"]),
                               curr_stats["data"]-prev_stats["data"],
                               delta_pct(curr_stats["data"], prev_stats["data"]),
                               "Current vs prev", True)
            with c4: stat_card("RCS", fmt(curr_stats["rcs"]),
                               curr_stats["rcs"]-prev_stats["rcs"],
                               delta_pct(curr_stats["rcs"], prev_stats["rcs"]),
                               "Current vs prev", True)

            st.write("")
            section("Side-by-Side Comparison")

            comp_df = pd.DataFrame({
                "Metric":   ["CDR", "Data (GB)", "Voice", "Talk (min)",
                             "SMS", "MMS", "Data Sessions", "RCS"],
                "Previous": [prev_stats["cdr"], round(prev_stats["bytes"]/1e9, 2),
                             prev_stats["voice"], round(prev_stats["minutes"]),
                             prev_stats["sms"], prev_stats["mms"],
                             prev_stats["data"], prev_stats["rcs"]],
                "Current":  [curr_stats["cdr"], round(curr_stats["bytes"]/1e9, 2),
                             curr_stats["voice"], round(curr_stats["minutes"]),
                             curr_stats["sms"], curr_stats["mms"],
                             curr_stats["data"], curr_stats["rcs"]],
            })
            comp_df["Delta"] = comp_df["Current"] - comp_df["Previous"]
            comp_df["Δ%"] = comp_df.apply(
                lambda r: (r["Delta"] / r["Previous"] * 100) if r["Previous"] else 0,
                axis=1).round(1)
            st.dataframe(comp_df, use_container_width=True, hide_index=True)
            csv_btn(comp_df, "period_comparison.csv")

            st.write("")
            section("Comparison Chart")
            long_df = comp_df.melt(id_vars="Metric",
                                    value_vars=["Previous", "Current"],
                                    var_name="Period", value_name="Value")
            fig = px.bar(long_df, x="Metric", y="Value", color="Period",
                         barmode="group",
                         color_discrete_map={"Previous": GRAY, "Current": ORANGE})
            fig.update_layout(height=400, xaxis_title="", yaxis_title="",
                              legend_title="",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

            st.write("")
            if st.button("📄 Export Period Comparison PDF", key="pdf_compare"):
                sections = [
                    {"heading": "Period Comparison",
                     "text": f"Previous: {prev_range} | Current: {curr_range}"},
                    {"heading": "Metrics", "table": comp_df},
                ]
                pdf = build_pdf("TELECOM Radar — Period Comparison", sections)
                pdf_download_button(pdf, "period_comparison.pdf")

    # ==================================================================
    # TAB 2 — ANOMALIES (FIXED)
    # ==================================================================
    with tabs[2]:
        section("🔍 Anomaly Detection (Z-Score Based)")

        if not anomalies:
            st.success("✅ No anomalies detected in current data.")
        else:
            high = [a for a in anomalies if a["severity"] == "HIGH"]
            med  = [a for a in anomalies if a["severity"] == "MEDIUM"]

            c1, c2, c3, c4 = st.columns(4)
            with c1: anomaly_card("Total Anomalies", fmt(len(anomalies)), "Detected events")
            with c2: anomaly_card("HIGH Severity", fmt(len(high)), "|z| > 2.5")
            with c3: anomaly_card("MEDIUM Severity", fmt(len(med)), "|z| 2.0-2.5")
            with c4:
                types_count = len(set(a["type"] for a in anomalies))
                anomaly_card("Categories", fmt(types_count), "Distinct types")

            st.write("")
            section("Detected Anomalies")
            an_df = pd.DataFrame(anomalies)
            an_df = an_df[["severity","type","entity","value","expected","z_score","desc"]]
            an_df = an_df.sort_values("z_score", key=lambda s: s.abs(), ascending=False)
            st.dataframe(an_df, use_container_width=True, hide_index=True, height=400)
            csv_btn(an_df, "anomalies.csv")

            st.write("")
            section("Z-Score Visualization")

            # FIX: use absolute value of z_score for marker size
            an_plot = an_df.copy()
            an_plot["abs_z"] = an_plot["z_score"].abs().clip(lower=0.1)

            fig = px.scatter(an_plot, x="z_score", y="entity",
                             color="severity", size="abs_z",
                             color_discrete_map={"HIGH": RED, "MEDIUM": ORANGE},
                             hover_data=["type","value","expected","desc"])
            fig.add_vline(x=2.5, line_dash="dash", line_color=RED,
                          annotation_text="HIGH threshold")
            fig.add_vline(x=-2.5, line_dash="dash", line_color=RED)
            fig.add_vline(x=2.0, line_dash="dot", line_color=ORANGE,
                          annotation_text="MEDIUM threshold")
            fig.add_vline(x=-2.0, line_dash="dot", line_color=ORANGE)
            fig.update_layout(height=max(400, len(an_plot)*25),
                              xaxis_title="Z-Score", yaxis_title="",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

            st.write("")
            section("Anomalies by Type")
            type_count = an_df.groupby("type").size().reset_index(name="Count")
            fig = px.bar(type_count, x="Count", y="type", orientation="h",
                         color="Count",
                         color_continuous_scale=["#fff7ed", ORANGE, RED])
            fig.update_layout(height=340, coloraxis_showscale=False,
                              xaxis_title="", yaxis_title="",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

            st.write("")
            if st.button("📄 Export Anomalies PDF", key="pdf_anom"):
                sections = [
                    {"heading": "Anomaly Detection Report",
                     "text": f"Total: {len(anomalies)} | HIGH: {len(high)} | MEDIUM: {len(med)}"},
                    {"heading": "Detected Anomalies", "table": an_df},
                ]
                pdf = build_pdf("TELECOM Radar — Anomalies", sections)
                pdf_download_button(pdf, "anomalies.pdf")

    # ==================================================================
    # TAB 3 — TIME SERIES
    # ==================================================================
    with tabs[3]:
        section("Traffic Over Time")
        if not len(cdrs_f):
            st.info("No data for current filter.")
        else:
            hourly = cdrs_f.groupby("hour").agg(
                records=("record_id","count"),
                bytes=("bytes","sum"),
            ).reset_index()

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=hourly["hour"], y=hourly["records"],
                                 name="CDR Records", marker_color=ORANGE, opacity=0.75),
                          secondary_y=False)
            fig.add_trace(go.Scatter(x=hourly["hour"], y=hourly["bytes"]/1e6,
                                      name="Data Volume (MB)", mode="lines+markers",
                                      line=dict(color=BLUE, width=2.5)),
                          secondary_y=True)
            fig.update_layout(
                height=420, xaxis=dict(title="Hour of Day", dtick=1),
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1),
                margin=dict(l=0, r=0, t=40, b=0), hovermode="x unified")
            fig.update_yaxes(title_text="Records", secondary_y=False)
            fig.update_yaxes(title_text="MB", secondary_y=True)
            safe_chart(fig)

            st.write("")
            section("Daily Trend")
            daily = cdrs_f.groupby("day").agg(
                records=("record_id","count"),
                bytes=("bytes","sum")).reset_index()
            fig = px.area(daily, x="day", y="records", markers=True,
                          color_discrete_sequence=[ORANGE])
            fig.update_traces(fillcolor="rgba(246,130,31,0.2)")
            fig.update_layout(height=320, xaxis_title="", yaxis_title="Records",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

            st.write("")
            section("Hourly Breakdown by Call Type")
            pivot = cdrs_f.pivot_table(index="hour", columns="call_type",
                                        values="record_id", aggfunc="count").fillna(0)
            if not pivot.empty:
                fig = px.bar(pivot, barmode="stack",
                             color_discrete_sequence=[ORANGE, BLUE, GREEN, PURPLE, GRAY, RED])
                fig.update_layout(height=380, xaxis=dict(dtick=1),
                                  xaxis_title="Hour", yaxis_title="Records",
                                  legend_title="Type",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

    # ==================================================================
    # TAB 4 — TRAFFIC MIX
    # ==================================================================
    with tabs[4]:
        section("Traffic Composition")
        if not len(cdrs_f):
            st.info("No data.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                tc = cdrs_f["call_type"].value_counts().reset_index()
                tc.columns = ["Type", "Count"]
                fig = px.pie(tc, names="Type", values="Count", hole=0.6,
                             color_discrete_sequence=[ORANGE, BLUE, GREEN, PURPLE, GRAY, RED])
                fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
                fig.update_traces(textposition="outside", textinfo="label+percent")
                safe_chart(fig)
            with c2:
                agg = cdrs_f.groupby("call_type").agg(
                    avg_dur=("duration_sec","mean"),
                    avg_bytes=("bytes","mean"),
                    total=("record_id","count")).round(1).reset_index()
                fig = px.bar(agg, x="call_type", y="avg_dur", text="avg_dur",
                             color="call_type",
                             color_discrete_sequence=[ORANGE, BLUE, GREEN, PURPLE, GRAY, RED])
                fig.update_traces(texttemplate="%{text}s", textposition="outside")
                fig.update_layout(height=400, showlegend=False,
                                  xaxis_title="", yaxis_title="Avg Duration (sec)",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

            st.write("")
            section("Result Distribution (Call Outcome)")
            if "result" in cdrs_f.columns:
                rc = cdrs_f["result"].value_counts().reset_index()
                rc.columns = ["Result", "Count"]
                fig = px.bar(rc, x="Result", y="Count", color="Result",
                             color_discrete_map={"ANSWERED":GREEN, "NO_ANSWER":GRAY,
                                                 "BUSY":ORANGE, "FAILED":RED,
                                                 "OK":GREEN, "DELIVERED":GREEN,
                                                 "EXPIRED":ORANGE, "REJECTED":RED,
                                                 "PENDING":GRAY})
                fig.update_layout(height=320, showlegend=False,
                                  xaxis_title="", yaxis_title="Records",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

    # ==================================================================
    # TAB 5 — TECHNOLOGY
    # ==================================================================
    with tabs[5]:
        section("Technology Distribution")
        if not len(cells_f):
            st.info("No cells match filter.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                tc = cells_f["tech"].value_counts().reset_index()
                tc.columns = ["Tech", "Count"]
                fig = px.pie(tc, names="Tech", values="Count", hole=0.55,
                             color="Tech",
                             color_discrete_map={"2G":"#8888ff","3G":"#38bdf8",
                                                 "4G":"#22c55e","5G":ORANGE})
                fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)
            with c2:
                if len(cdrs_f):
                    td = cdrs_f["tech"].value_counts().reset_index()
                    td.columns = ["Tech", "CDRs"]
                    fig = px.bar(td, x="Tech", y="CDRs", color="Tech",
                                 color_discrete_map={"2G":"#8888ff","3G":"#38bdf8",
                                                     "4G":"#22c55e","5G":ORANGE,"6G":"#a855f7"})
                    fig.update_layout(height=320, showlegend=False,
                                      xaxis_title="", yaxis_title="CDRs",
                                      margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)
            with c3:
                bands = cells_f["band"].value_counts().reset_index().head(10)
                bands.columns = ["Band", "Count"]
                fig = px.bar(bands, x="Count", y="Band", orientation="h",
                             color="Count",
                             color_continuous_scale=["#fff7ed", ORANGE])
                fig.update_layout(height=320, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

            st.write("")
            section("Traffic vs Technology (Stacked by City)")
            if len(cdrs_f):
                pivot = cdrs_f.pivot_table(index="city", columns="tech",
                                            values="record_id", aggfunc="count").fillna(0)
                if not pivot.empty:
                    fig = px.bar(pivot, barmode="stack",
                                 color_discrete_map={"2G":"#8888ff","3G":"#38bdf8",
                                                     "4G":"#22c55e","5G":ORANGE,"6G":"#a855f7"})
                    fig.update_layout(height=380, xaxis_title="", yaxis_title="Records",
                                      legend_title="Tech",
                                      margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)

            st.write("")
            section("Signal Quality by Technology")
            if len(cdrs_f) and cdrs_f["rsrp"].notna().any():
                df = cdrs_f[cdrs_f["rsrp"].notna()]
                fig = px.violin(df, x="tech", y="rsrp", color="tech", box=True,
                                color_discrete_map={"4G":"#22c55e","5G":ORANGE,"6G":"#a855f7"})
                fig.update_layout(height=380, showlegend=False,
                                  xaxis_title="", yaxis_title="RSRP (dBm)",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

    # ==================================================================
    # TAB 6 — VOICE
    # ==================================================================
    with tabs[6]:
        section("Voice Analytics")
        v = cdrs_f[cdrs_f["call_type"] == "voice"] if len(cdrs_f) else pd.DataFrame()
        if not len(v):
            st.info("No voice records match filter.")
        else:
            total_calls = len(v)
            answered = int((v["result"] == "ANSWERED").sum())
            asr = answered / total_calls * 100 if total_calls else 0
            avg_dur = v["duration_sec"].mean()
            total_min = v["duration_sec"].sum() / 60

            c1, c2, c3, c4 = st.columns(4)
            with c1: stat_card("Total Calls", fmt(total_calls), sub="Voice only")
            with c2: stat_card("Answer Rate", f"{asr:.1f}%", sub=f"{fmt(answered)} answered")
            with c3: stat_card("Avg Duration", f"{avg_dur:.0f}s", sub="Per call")
            with c4: stat_card("Total Minutes", fmt(total_min), sub="Talk time")

            st.write("")
            c1, c2 = st.columns(2)
            with c1:
                section("Voice Bearer Mix")
                if "voice_bearer" in v.columns:
                    bm = v["voice_bearer"].value_counts().reset_index()
                    bm.columns = ["Bearer", "Count"]
                    fig = px.pie(bm, names="Bearer", values="Count", hole=0.55,
                                 color="Bearer",
                                 color_discrete_map={"VoLTE":GREEN,"VoNR":ORANGE,
                                                     "VoWiFi":BLUE,"CSFB":GRAY})
                    fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)
            with c2:
                section("Codec Distribution")
                if "voice_codec" in v.columns:
                    cd = v["voice_codec"].value_counts().reset_index()
                    cd.columns = ["Codec", "Count"]
                    fig = px.bar(cd, x="Codec", y="Count", color="Count",
                                 color_continuous_scale=["#eff6ff", BLUE])
                    fig.update_layout(height=380, coloraxis_showscale=False,
                                      xaxis_title="", yaxis_title="Calls",
                                      margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)

            st.write("")
            section("Voice Bearer by Technology")
            if "voice_bearer" in v.columns:
                pivot = v.pivot_table(index="tech", columns="voice_bearer",
                                       values="record_id", aggfunc="count").fillna(0)
                if not pivot.empty:
                    fig = px.imshow(pivot, aspect="auto", text_auto=True,
                                    color_continuous_scale=["#f0fdf4","#22c55e","#15803d"])
                    fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)

            st.write("")
            section("Average Call Duration by Bearer")
            if "voice_bearer" in v.columns:
                dur = v.groupby("voice_bearer")["duration_sec"].mean().reset_index()
                dur.columns = ["Bearer", "AvgSec"]
                dur = dur.sort_values("AvgSec", ascending=False)
                fig = px.bar(dur, x="Bearer", y="AvgSec", text="AvgSec",
                             color="Bearer",
                             color_discrete_map={"VoLTE":GREEN,"VoNR":ORANGE,
                                                 "VoWiFi":BLUE,"CSFB":GRAY})
                fig.update_traces(texttemplate="%{text:.0f}s", textposition="outside")
                fig.update_layout(height=340, showlegend=False,
                                  xaxis_title="", yaxis_title="Avg Duration (sec)",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

    # ==================================================================
    # TAB 7 — MESSAGING
    # ==================================================================
    with tabs[7]:
        section("Messaging Analytics")
        msg = cdrs_f[cdrs_f["call_type"].isin(["sms","mms","rcs"])] if len(cdrs_f) else pd.DataFrame()
        if not len(msg):
            st.info("No messaging records match filter.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            sms = msg[msg["call_type"] == "sms"]
            mms = msg[msg["call_type"] == "mms"]
            rcs = msg[msg["call_type"] == "rcs"]
            with c1: stat_card("SMS", fmt(len(sms)), sub="Messages")
            with c2: stat_card("MMS", fmt(len(mms)),
                               sub=f"{mms['mms_size_bytes'].sum()/1e6:.1f} MB" if len(mms) else "0 MB")
            with c3: stat_card("RCS", fmt(len(rcs)), sub="Rich messages")
            with c4:
                if len(mms):
                    succ = (mms["mms_delivery"] == "DELIVERED").mean() * 100
                    stat_card("MMS Success", f"{succ:.1f}%", sub="Delivery rate")
                else:
                    stat_card("MMS Success", "—", sub="No data")

            st.write("")
            c1, c2 = st.columns(2)
            with c1:
                section("MMS Content Types")
                if len(mms):
                    ct = mms["mms_content_type"].value_counts().reset_index()
                    ct.columns = ["Type", "Count"]
                    fig = px.bar(ct, x="Count", y="Type", orientation="h",
                                 color="Count",
                                 color_continuous_scale=["#f5f3ff", PURPLE])
                    fig.update_layout(height=380, coloraxis_showscale=False,
                                      xaxis_title="", yaxis_title="",
                                      margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)
            with c2:
                section("MMS Delivery Status")
                if len(mms):
                    st_d = mms["mms_delivery"].value_counts().reset_index()
                    st_d.columns = ["Status", "Count"]
                    fig = px.pie(st_d, names="Status", values="Count", hole=0.5,
                                 color="Status",
                                 color_discrete_map={"DELIVERED":GREEN,"EXPIRED":ORANGE,
                                                     "REJECTED":RED,"PENDING":GRAY})
                    fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)

            st.write("")
            section("RCS by Type")
            if len(rcs):
                rt = rcs["rcs_type"].value_counts().reset_index()
                rt.columns = ["Type", "Count"]
                fig = px.bar(rt, x="Type", y="Count", color="Type",
                             color_discrete_sequence=[ORANGE, BLUE, GREEN, PURPLE, GRAY])
                fig.update_layout(height=340, showlegend=False,
                                  xaxis_title="", yaxis_title="Messages",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

            st.write("")
            section("MMS Size Distribution")
            if len(mms):
                fig = px.histogram(mms, x="mms_size_bytes", nbins=50,
                                   color_discrete_sequence=[PURPLE])
                fig.update_layout(height=320, xaxis_title="Size (bytes)",
                                  yaxis_title="Messages",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

    # ==================================================================
    # TAB 8 — THREAT RADAR
    # ==================================================================
    with tabs[8]:
        section("🚨 Threat Radar — Security Insights")

        clir_abuse   = sig.get("clir_abuse", [])
        simbox       = sig.get("simbox_suspects", [])
        imp_travel   = sig.get("impossible_travel", [])
        imei_churn   = sig.get("imei_churn_suspects", [])
        filter_byp   = sig.get("filter_bypass_users", [])
        enc_fails    = sig.get("encryption_failures", [])
        weak_cells   = sig.get("weak_cells", [])
        mms_suspects = sig.get("mms_large_suspects", [])

        c1, c2, c3, c4 = st.columns(4)
        with c1: threat_card("CLIR Abuse", fmt(len(clir_abuse)), "Unauthorized no-caller-ID")
        with c2: threat_card("SIM-Box", fmt(len(simbox)), "Bulk short calls")
        with c3: threat_card("IMEI Churn", fmt(len(imei_churn)), "Multiple IMEIs per IMSI")
        with c4: threat_card("Impossible Travel", fmt(len(imp_travel)), "Anomalous movement")

        c1, c2, c3, c4 = st.columns(4)
        with c1: threat_card("Filter Bypass", fmt(len(filter_byp)), "Unfiltered sessions")
        with c2: threat_card("Encryption Fail", fmt(len(enc_fails)), "Handshake errors")
        with c3: threat_card("Large MMS", fmt(len(mms_suspects)), "Possible abuse")
        with c4: threat_card("Weak Cells", fmt(len(weak_cells)), "Low quality")

        st.write("")
        section("Attack Timeline (Alert Volume by Hour)")
        if len(alerts_df):
            a = alerts_df.copy()
            a["ts"] = pd.to_datetime(a["timestamp"], errors="coerce")
            a["hour"] = a["ts"].dt.hour
            sev_order = ["CRITICAL","HIGH","MEDIUM","LOW"]
            pivot = a.pivot_table(index="hour", columns="severity",
                                   values="alert_id", aggfunc="count").fillna(0)
            for s in sev_order:
                if s not in pivot.columns:
                    pivot[s] = 0
            pivot = pivot[sev_order]
            if not pivot.empty:
                fig = px.bar(pivot, barmode="stack",
                             color_discrete_map={"CRITICAL":RED,"HIGH":ORANGE,
                                                 "MEDIUM":BLUE,"LOW":GRAY})
                fig.update_layout(height=380, xaxis=dict(dtick=1),
                                  xaxis_title="Hour", yaxis_title="Alerts",
                                  legend_title="Severity",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

        st.write("")
        c1, c2 = st.columns(2)
        with c1:
            section("Alert Severity Breakdown")
            if len(alerts_df):
                sv = alerts_df["severity"].value_counts().reset_index()
                sv.columns = ["Severity", "Count"]
                fig = px.pie(sv, names="Severity", values="Count", hole=0.55,
                             color="Severity",
                             color_discrete_map={"CRITICAL":RED,"HIGH":ORANGE,
                                                 "MEDIUM":BLUE,"LOW":GRAY})
                fig.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)
        with c2:
            section("Alert Type Distribution")
            if len(alerts_df):
                at = alerts_df["alert_type"].value_counts().reset_index()
                at.columns = ["Type", "Count"]
                fig = px.bar(at, x="Count", y="Type", orientation="h",
                             color="Count",
                             color_continuous_scale=["#fef2f2", RED])
                fig.update_layout(height=360, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

        st.write("")
        section("Top 15 Weak Cells (Low Signal Quality)")
        if weak_cells:
            df_w = pd.DataFrame(weak_cells, columns=["cell_id","bad_samples"])
            df_w = df_w.sort_values("bad_samples", ascending=False).head(15)
            fig = px.bar(df_w, x="bad_samples", y="cell_id", orientation="h",
                         color="bad_samples",
                         color_continuous_scale=["#fff7ed", ORANGE, RED])
            fig.update_layout(height=420, coloraxis_showscale=False,
                              xaxis_title="Bad Samples", yaxis_title="",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

    # ==================================================================
    # TAB 9 — ENCRYPTION
    # ==================================================================
    with tabs[9]:
        section("🔐 Encryption Coverage")
        cov = sig.get("encryption_coverage", {})
        if not cov:
            st.info("No encryption data.")
        else:
            total_enc = sum(v["encrypted"] for v in cov.values())
            total_evt = sum(v["total"] for v in cov.values())
            total_fail = sum(v["failures"] for v in cov.values())
            overall = total_enc / total_evt * 100 if total_evt else 0

            c1, c2, c3, c4 = st.columns(4)
            with c1: stat_card("Overall Coverage", f"{overall:.1f}%",
                               sub=f"{fmt(total_enc)} / {fmt(total_evt)}")
            with c2: stat_card("Encrypted Events", fmt(total_enc), sub="Total")
            with c3: stat_card("Failures", fmt(total_fail), sub="Handshake errors")
            with c4:
                gov = cov.get("Government", {}).get("coverage_pct", 0)
                stat_card("Gov Coverage", f"{gov:.1f}%", sub="Government lines")

            st.write("")
            section("Coverage by Line Class")
            cov_df = pd.DataFrame([
                {"LineClass": k, "Coverage": v["coverage_pct"],
                 "Total": v["total"], "Encrypted": v["encrypted"],
                 "Failures": v["failures"]}
                for k, v in cov.items()
            ]).sort_values("Coverage", ascending=False)
            fig = px.bar(cov_df, x="LineClass", y="Coverage", text="Coverage",
                         color="Coverage",
                         color_continuous_scale=["#fee2e2", ORANGE, GREEN])
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(height=380, coloraxis_showscale=False,
                              yaxis_range=[0, 110],
                              xaxis_title="", yaxis_title="Coverage %",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

            st.write("")
            c1, c2 = st.columns(2)
            with c1:
                section("Cipher Suite Usage")
                cu = sig.get("cipher_usage", {})
                if cu:
                    cu_df = pd.DataFrame(list(cu.items()), columns=["Cipher","Count"])
                    fig = px.pie(cu_df, names="Cipher", values="Count", hole=0.55,
                                 color_discrete_sequence=[ORANGE, BLUE, GREEN, PURPLE, RED])
                    fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)
            with c2:
                section("Encryption Failures by Class")
                if len(cov_df):
                    fig = px.bar(cov_df, x="LineClass", y="Failures",
                                 color="Failures",
                                 color_continuous_scale=["#fef2f2", RED])
                    fig.update_layout(height=400, coloraxis_showscale=False,
                                      xaxis_title="", yaxis_title="Failures",
                                      margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)

            st.write("")
            if st.button("📄 Export Encryption PDF", key="pdf_enc"):
                sections = [
                    {"heading": "Encryption Coverage",
                     "text": f"Overall: {overall:.1f}% | Failures: {total_fail}"},
                    {"heading": "By Line Class", "table": cov_df},
                ]
                pdf = build_pdf("TELECOM Radar — Encryption", sections)
                pdf_download_button(pdf, "encryption.pdf")

    # ==================================================================
    # TAB 10 — SPECIAL LINES
    # ==================================================================
    with tabs[10]:
        section("🔑 Special Lines Analytics")
        sl = sig.get("special_line_traffic", {})
        if not sl:
            st.info("No special lines data.")
        else:
            total = sum(sl.values())
            special = total - sl.get("Normal", 0)
            special_pct = special / total * 100 if total else 0

            c1, c2, c3, c4 = st.columns(4)
            with c1: stat_card("Total Events", fmt(total), sub="All classes")
            with c2: stat_card("Special Events", fmt(special), sub=f"{special_pct:.1f}% of total")
            with c3: stat_card("Line Classes", fmt(len(sl)), sub="Active classes")
            with c4:
                top_class = max(sl.items(), key=lambda x: x[1])[0] if sl else "—"
                stat_card("Top Class", top_class, sub=f"{fmt(sl[top_class])} events")

            st.write("")
            section("Traffic Distribution by Line Class")
            sl_df = pd.DataFrame(list(sl.items()), columns=["Class","Events"])
            sl_df = sl_df.sort_values("Events", ascending=False)
            fig = px.bar(sl_df, x="Class", y="Events", color="Class",
                         color_discrete_map={"Normal":GRAY,"VIP":GREEN,
                                             "Government":RED,"Corporate":BLUE,
                                             "Emergency":ORANGE,"Test":PURPLE},
                         text="Events")
            fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig.update_layout(height=400, showlegend=False,
                              xaxis_title="", yaxis_title="Events",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

            st.write("")
            c1, c2 = st.columns(2)
            with c1:
                section("Filter-Bypass Heavy Users")
                fb = sig.get("filter_bypass_users", [])
                if fb:
                    fb_df = pd.DataFrame(fb, columns=["MSISDN","Sessions"])
                    fb_df = fb_df.sort_values("Sessions", ascending=False).head(15)
                    fig = px.bar(fb_df, x="Sessions", y="MSISDN", orientation="h",
                                 color="Sessions",
                                 color_continuous_scale=["#fef2f2", ORANGE, RED])
                    fig.update_layout(height=380, coloraxis_showscale=False,
                                      xaxis_title="Sessions", yaxis_title="",
                                      margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)
                else:
                    st.info("No filter-bypass activity.")
            with c2:
                section("Priority QoS Distribution")
                if "priority_qos" in subs_f.columns:
                    qos = subs_f["priority_qos"].value_counts().sort_index().reset_index()
                    qos.columns = ["QoS", "Subscribers"]
                    fig = px.bar(qos, x="QoS", y="Subscribers", color="Subscribers",
                                 color_continuous_scale=["#fef3c7", ORANGE, RED])
                    fig.update_layout(height=380, coloraxis_showscale=False,
                                      xaxis=dict(dtick=1),
                                      xaxis_title="QoS Class", yaxis_title="",
                                      margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)

    # ==================================================================
    # TAB 11 — GEOGRAPHY
    # ==================================================================
    with tabs[11]:
        section("🗺️ Geographic Distribution")

        geo_c1, geo_c2, geo_c3, geo_c4 = st.columns(4)
        with geo_c1:
            geo_proj = st.selectbox("Projection",
                ["natural earth", "mercator", "orthographic", "equirectangular"],
                key="radar_proj")
        with geo_c2:
            geo_size = st.selectbox("Marker size",
                ["None", "tx_dbm", "backhaul_gbps"], key="radar_marker_size")
        with geo_c3:
            geo_style = st.radio("Style", ["Scatter", "Density"],
                                  horizontal=True, key="radar_style")
        with geo_c4:
            geo_zoom = st.slider("Zoom scale", 2.0, 8.0, 4.0, 0.5,
                                  key="radar_zoom")

        if not len(cells_f):
            st.info("No cells match filter.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                section("Cell Sites by City")
                gc = cells_f.groupby("city").size().reset_index(name="Cells")
                gc = gc.sort_values("Cells", ascending=True)
                fig = px.bar(gc, x="Cells", y="city", orientation="h",
                             color="Cells",
                             color_continuous_scale=["#fff7ed", ORANGE])
                fig.update_layout(height=420, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)
            with c2:
                section("Traffic by City")
                if len(cdrs_f):
                    tc = cdrs_f.groupby("city").size().reset_index(name="Records")
                    tc = tc.sort_values("Records", ascending=True)
                    fig = px.bar(tc, x="Records", y="city", orientation="h",
                                 color="Records",
                                 color_continuous_scale=["#eff6ff", BLUE])
                    fig.update_layout(height=420, coloraxis_showscale=False,
                                      xaxis_title="", yaxis_title="",
                                      margin=dict(l=0, r=0, t=10, b=0))
                    safe_chart(fig)

            st.write("")
            section("Interactive Cell Map")

            if geo_style == "Scatter":
                size_arg = geo_size if geo_size != "None" else None
                fig = px.scatter_geo(cells_f, lat="lat", lon="lon",
                                     color="tech",
                                     size=size_arg if size_arg else None,
                                     size_max=15,
                                     color_discrete_map={"2G":"#8888ff","3G":"#38bdf8",
                                                         "4G":"#22c55e","5G":ORANGE,"6G":"#a855f7"},
                                     hover_name="name",
                                     hover_data={"city":True,"band":True,"tx_dbm":True,
                                                 "lat":False,"lon":False})
                fig.update_geos(scope="world", showcountries=True,
                                countrycolor="#cbd5e1",
                                showland=True, landcolor="#f1f5f9",
                                showocean=True, oceancolor="#e0f2fe",
                                projection_type=geo_proj,
                                center={"lat":33.5,"lon":53.5},
                                projection_scale=geo_zoom)
                fig.update_layout(height=520, legend_title="Tech",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)
            else:
                density = cells_f.copy()
                density["lat_r"] = (density["lat"] * 10).round() / 10
                density["lon_r"] = (density["lon"] * 10).round() / 10
                dens = density.groupby(["lat_r","lon_r"]).size().reset_index(name="count")
                fig = px.density_mapbox(dens, lat="lat_r", lon="lon_r",
                                         z="count", radius=20,
                                         center=dict(lat=33.5, lon=53.5),
                                         zoom=geo_zoom,
                                         mapbox_style="open-street-map",
                                         color_continuous_scale=["#fff7ed", ORANGE, RED])
                fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

            st.write("")
            csv_btn(cells_f[["cell_id","name","tech","city","lat","lon","band"]],
                    "cells_geographic.csv")

    # ==================================================================
    # TAB 12 — OSINT
    # ==================================================================
    with tabs[12]:
        section("🌐 OSINT Radar — Public Insights")
        if not len(osint_comp):
            st.info("No OSINT data.")
        else:
            total = len(osint_comp)
            neg = int((osint_comp["sentiment"] == "negative").sum())
            neu = int((osint_comp["sentiment"] == "neutral").sum())
            pos = int((osint_comp["sentiment"] == "positive").sum())

            c1, c2, c3, c4 = st.columns(4)
            with c1: stat_card("Complaints", fmt(total), sub="Public sources")
            with c2: stat_card("Negative", fmt(neg), sub=f"{neg/total*100:.0f}%")
            with c3: stat_card("Neutral", fmt(neu), sub=f"{neu/total*100:.0f}%")
            with c4: stat_card("Positive", fmt(pos), sub=f"{pos/total*100:.0f}%")

            st.write("")
            c1, c2 = st.columns(2)
            with c1:
                section("Top Complaint Topics")
                tc = osint_comp["topic"].value_counts().reset_index()
                tc.columns = ["Topic","Count"]
                fig = px.bar(tc, x="Count", y="Topic", orientation="h",
                             color="Count",
                             color_continuous_scale=["#fef2f2", RED])
                fig.update_layout(height=400, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="",
                                  margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)
            with c2:
                section("Sentiment Mix")
                sm = osint_comp["sentiment"].value_counts().reset_index()
                sm.columns = ["Sentiment","Count"]
                fig = px.pie(sm, names="Sentiment", values="Count", hole=0.55,
                             color="Sentiment",
                             color_discrete_map={"negative":RED,"neutral":ORANGE,
                                                 "positive":GREEN})
                fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
                safe_chart(fig)

            st.write("")
            section("Complaints by City")
            cc = osint_comp["city"].value_counts().reset_index()
            cc.columns = ["City","Count"]
            fig = px.bar(cc, x="City", y="Count", color="Count",
                         color_continuous_scale=["#fff7ed", ORANGE])
            fig.update_layout(height=340, coloraxis_showscale=False,
                              xaxis_title="", yaxis_title="Complaints",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

            st.write("")
            section("Complaint Source Distribution")
            sc = osint_comp["source"].value_counts().reset_index()
            sc.columns = ["Source","Count"]
            fig = px.pie(sc, names="Source", values="Count", hole=0.5,
                         color_discrete_sequence=[ORANGE, BLUE, GREEN, PURPLE, RED])
            fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

    # ==================================================================
    # TAB 13 — ATTACK RADAR (PATCH)
    # ==================================================================
    with tabs[13]:
        section("Attack Analytics")
        _asc = data.get("attack_scenarios", pd.DataFrame())
        _aev = data.get("attack_events", pd.DataFrame())
        if _asc is None or _asc.empty:
            st.info("No attack data. Run `python telecom_attack.py`.")
        else:
            total = len(_asc)
            by_status = _asc["status"].value_counts().to_dict()
            blk = by_status.get("BLOCKED", 0)
            suc = by_status.get("SUCCESS", 0)
            det = by_status.get("DETECTED", 0)
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: stat_card("Scenarios", fmt(total), sub="Total")
            with c2: stat_card("Blocked", fmt(blk), sub=f"{blk/total*100:.0f}%")
            with c3: stat_card("Detected", fmt(det), sub=f"{det/total*100:.0f}%")
            with c4: stat_card("Attacker Wins", fmt(suc), sub=f"{suc/total*100:.0f}%")
            with c5:
                crit = int((_asc["severity"] == "CRITICAL").sum())
                stat_card("CRITICAL", fmt(crit), sub="Severity")

            st.write("")
            c1, c2 = st.columns(2)
            with c1:
                section("Severity Distribution")
                sv = _asc["severity"].value_counts().reset_index()
                sv.columns = ["severity", "count"]
                fig = px.bar(sv, x="severity", y="count", color="severity",
                             color_discrete_map={"CRITICAL":RED,"HIGH":ORANGE,
                                                 "MEDIUM":BLUE,"LOW":GRAY})
                fig.update_layout(height=360, showlegend=False)
                safe_chart(fig)
            with c2:
                section("Layer Distribution")
                lc = _asc["target_layer"].value_counts().reset_index()
                lc.columns = ["layer", "count"]
                fig = px.pie(lc, names="layer", values="count", hole=0.55)
                fig.update_layout(height=360)
                safe_chart(fig)

            st.write("")
            section("Impact: Latency and Drop Over Time")
            if not _aev.empty:
                fig = px.scatter(_aev.sort_values("ts"), x="ts", y="latency_ms",
                                 size="drop_pct", color="severity",
                                 color_discrete_map={"CRITICAL":RED,"HIGH":ORANGE,
                                                     "MEDIUM":BLUE,"LOW":GRAY},
                                 hover_data=["attack_type","target_node","pps"])
                fig.update_layout(height=420)
                safe_chart(fig)

            st.write("")
            c1, c2 = st.columns(2)
            with c1:
                section("MTTD by Attack Type")
                if not _aev.empty and _aev["mttd_sec"].notna().any():
                    mt = (_aev.dropna(subset=["mttd_sec"])
                           .groupby("attack_type")["mttd_sec"].mean()
                           .reset_index().sort_values("mttd_sec"))
                    fig = px.bar(mt, x="mttd_sec", y="attack_type", orientation="h",
                                 color="mttd_sec",
                                 color_continuous_scale=["#f0fdf4", GREEN, ORANGE, RED])
                    fig.update_layout(height=420, coloraxis_showscale=False,
                                      xaxis_title="MTTD (sec)", yaxis_title="")
                    safe_chart(fig)
            with c2:
                section("MTTR by Attack Type")
                if not _aev.empty and _aev["mttr_sec"].notna().any():
                    mt = (_aev.dropna(subset=["mttr_sec"])
                           .groupby("attack_type")["mttr_sec"].mean()
                           .reset_index().sort_values("mttr_sec"))
                    fig = px.bar(mt, x="mttr_sec", y="attack_type", orientation="h",
                                 color="mttr_sec",
                                 color_continuous_scale=["#eff6ff", BLUE, ORANGE])
                    fig.update_layout(height=420, coloraxis_showscale=False,
                                      xaxis_title="MTTR (sec)", yaxis_title="")
                    safe_chart(fig)

            st.write("")
            section("Scenario Details")
            st.dataframe(_asc, use_container_width=True, hide_index=True, height=380)
            csv_btn(_asc, "attack_scenarios.csv")


    # ------------------------------------------------------------------
    # FOOTER
    # ------------------------------------------------------------------
    st.write("")

    st.markdown(f"""
    <div style="text-align:center; padding:20px; color:#94a3b8; font-size:12px;
                border-top:1px solid #e2e8f0; margin-top:20px;">
      <b style="color:{ORANGE};">{OPERATOR} RADAR v2.0</b> — Advanced Statistical Analytics<br>
      Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • LOCAL-ONLY •
      {len(cdrs):,} CDR records • {len(anomalies)} anomalies detected
    </div>
    """, unsafe_allow_html=True)





if __name__ == "__main__":
    main()
