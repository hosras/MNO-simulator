# -*- coding: utf-8 -*-
"""Tab 9 — Encryption Coverage."""
import pandas as pd
import streamlit as st
import plotly.express as px

from radar._config import ORANGE, BLUE, GREEN, RED
from radar.services.ui import (
    stat_card, section, safe_chart, fmt, dl_button,
)
from radar.services.pdf import build_pdf


def render(data, filtered, ctx):
    sig = ctx.get("sig", {})
    cov = sig.get("encryption_coverage", {})

    section("🔐 Encryption Coverage")
    if not cov:
        st.info("No encryption data.")
        return

    total_enc = sum(v["encrypted"] for v in cov.values())
    total_evt = sum(v["total"] for v in cov.values())
    total_fail = sum(v["failures"] for v in cov.values())
    overall = total_enc / total_evt * 100 if total_evt else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: stat_card("Overall Coverage", f"{overall:.1f}%",
                       sub=f"{fmt(total_enc)} / {fmt(total_evt)}")
    with c2: stat_card("Encrypted Events", fmt(total_enc), sub="Total")
    with c3: stat_card("Failures", fmt(total_fail),
                       sub="Handshake errors")
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
            cu_df = pd.DataFrame(list(cu.items()),
                                 columns=["Cipher", "Count"])
            fig = px.pie(cu_df, names="Cipher", values="Count", hole=0.55,
                         color_discrete_sequence=[ORANGE, BLUE, GREEN,
                                                  "#a855f7", RED])
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
        if pdf is None:
            st.caption("⚠️ Install `reportlab` to enable PDF export.")
        else:
            dl_button("📄 Export PDF", pdf, "encryption.pdf",
                      "application/pdf")