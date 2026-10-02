"""Tab 2 — Anomaly Detection."""

import pandas as pd
import plotly.express as px
import streamlit as st

from radar._config import ORANGE, RED
from radar.services.pdf import build_pdf
from radar.services.ui import (
    anomaly_card,
    csv_btn,
    dl_button,
    fmt,
    safe_chart,
    section,
)


def render(data, filtered, ctx):
    anomalies = ctx.get("anomalies", [])

    section("🔍 Anomaly Detection (Z-Score Based)")

    if not anomalies:
        st.success("✅ No anomalies detected in current data.")
        return

    high = [a for a in anomalies if a["severity"] == "HIGH"]
    med = [a for a in anomalies if a["severity"] == "MEDIUM"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        anomaly_card("Total Anomalies", fmt(len(anomalies)), "Detected events")
    with c2:
        anomaly_card("HIGH Severity", fmt(len(high)), "|z| > 2.5")
    with c3:
        anomaly_card("MEDIUM Severity", fmt(len(med)), "|z| 2.0-2.5")
    with c4:
        types_count = len({a["type"] for a in anomalies})
        anomaly_card("Categories", fmt(types_count), "Distinct types")

    st.write("")
    section("Detected Anomalies")
    an_df = pd.DataFrame(anomalies)
    an_df = an_df[["severity", "type", "entity", "value", "expected", "z_score", "desc"]]
    an_df = an_df.sort_values("z_score", key=lambda s: s.abs(), ascending=False)
    st.dataframe(an_df, use_container_width=True, hide_index=True, height=400)
    csv_btn(an_df, "anomalies.csv")

    st.write("")
    section("Z-Score Visualization")

    an_plot = an_df.copy()
    an_plot["abs_z"] = an_plot["z_score"].abs().clip(lower=0.1)

    fig = px.scatter(
        an_plot,
        x="z_score",
        y="entity",
        color="severity",
        size="abs_z",
        color_discrete_map={"HIGH": RED, "MEDIUM": ORANGE},
        hover_data=["type", "value", "expected", "desc"],
    )
    fig.add_vline(x=2.5, line_dash="dash", line_color=RED, annotation_text="HIGH threshold")
    fig.add_vline(x=-2.5, line_dash="dash", line_color=RED)
    fig.add_vline(x=2.0, line_dash="dot", line_color=ORANGE, annotation_text="MEDIUM threshold")
    fig.add_vline(x=-2.0, line_dash="dot", line_color=ORANGE)
    fig.update_layout(
        height=max(400, len(an_plot) * 25),
        xaxis_title="Z-Score",
        yaxis_title="",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    safe_chart(fig)

    st.write("")
    section("Anomalies by Type")
    type_count = an_df.groupby("type").size().reset_index(name="Count")
    fig = px.bar(
        type_count,
        x="Count",
        y="type",
        orientation="h",
        color="Count",
        color_continuous_scale=["#fff7ed", ORANGE, RED],
    )
    fig.update_layout(
        height=340,
        coloraxis_showscale=False,
        xaxis_title="",
        yaxis_title="",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    safe_chart(fig)

    st.write("")
    if st.button("📄 Export Anomalies PDF", key="pdf_anom"):
        sections = [
            {
                "heading": "Anomaly Detection Report",
                "text": (f"Total: {len(anomalies)} | " f"HIGH: {len(high)} | MEDIUM: {len(med)}"),
            },
            {"heading": "Detected Anomalies", "table": an_df},
        ]
        pdf = build_pdf("TELECOM Radar — Anomalies", sections)
        if pdf is None:
            st.caption("⚠️ Install `reportlab` to enable PDF export.")
        else:
            dl_button("📄 Export PDF", pdf, "anomalies.pdf", "application/pdf")
