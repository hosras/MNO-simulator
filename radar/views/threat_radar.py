# -*- coding: utf-8 -*-
"""Tab 8 — Threat Radar."""
import pandas as pd
import streamlit as st
import plotly.express as px

from radar._config import ORANGE, BLUE, GREEN, RED, GRAY
from radar.services.ui import threat_card, section, safe_chart, fmt


def render(data, filtered, ctx):
    alerts_df = data["alerts"]
    sig = ctx.get("sig", {})

    section("🚨 Threat Radar — Security Insights")

    clir_abuse = sig.get("clir_abuse", [])
    simbox = sig.get("simbox_suspects", [])
    imp_travel = sig.get("impossible_travel", [])
    imei_churn = sig.get("imei_churn_suspects", [])
    filter_byp = sig.get("filter_bypass_users", [])
    enc_fails = sig.get("encryption_failures", [])
    weak_cells = sig.get("weak_cells", [])
    mms_suspects = sig.get("mms_large_suspects", [])

    c1, c2, c3, c4 = st.columns(4)
    with c1: threat_card("CLIR Abuse", fmt(len(clir_abuse)),
                         "Unauthorized no-caller-ID")
    with c2: threat_card("SIM-Box", fmt(len(simbox)), "Bulk short calls")
    with c3: threat_card("IMEI Churn", fmt(len(imei_churn)),
                         "Multiple IMEIs per IMSI")
    with c4: threat_card("Impossible Travel", fmt(len(imp_travel)),
                         "Anomalous movement")

    c1, c2, c3, c4 = st.columns(4)
    with c1: threat_card("Filter Bypass", fmt(len(filter_byp)),
                         "Unfiltered sessions")
    with c2: threat_card("Encryption Fail", fmt(len(enc_fails)),
                         "Handshake errors")
    with c3: threat_card("Large MMS", fmt(len(mms_suspects)),
                         "Possible abuse")
    with c4: threat_card("Weak Cells", fmt(len(weak_cells)),
                         "Low quality")

    st.write("")
    section("Attack Timeline (Alert Volume by Hour)")
    if len(alerts_df):
        a = alerts_df.copy()
        a["ts"] = pd.to_datetime(a["timestamp"], errors="coerce")
        a["hour"] = a["ts"].dt.hour
        sev_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        pivot = a.pivot_table(index="hour", columns="severity",
                              values="alert_id",
                              aggfunc="count").fillna(0)
        for s in sev_order:
            if s not in pivot.columns:
                pivot[s] = 0
        pivot = pivot[sev_order]
        if not pivot.empty:
            fig = px.bar(pivot, barmode="stack",
                         color_discrete_map={"CRITICAL": RED, "HIGH": ORANGE,
                                             "MEDIUM": BLUE, "LOW": GRAY})
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
                         color_discrete_map={"CRITICAL": RED, "HIGH": ORANGE,
                                             "MEDIUM": BLUE, "LOW": GRAY})
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
        df_w = pd.DataFrame(weak_cells, columns=["cell_id", "bad_samples"])
        df_w = df_w.sort_values("bad_samples", ascending=False).head(15)
        fig = px.bar(df_w, x="bad_samples", y="cell_id", orientation="h",
                     color="bad_samples",
                     color_continuous_scale=["#fff7ed", ORANGE, RED])
        fig.update_layout(height=420, coloraxis_showscale=False,
                          xaxis_title="Bad Samples", yaxis_title="",
                          margin=dict(l=0, r=0, t=10, b=0))
        safe_chart(fig)