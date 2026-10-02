# -*- coding: utf-8 -*-
"""Tab 5 — Technology Distribution."""
import streamlit as st
import plotly.express as px

from radar._config import ORANGE
from radar.services.ui import section, safe_chart


TECH_COLORS = {
    "2G": "#8888ff", "3G": "#38bdf8", "4G": "#22c55e",
    "5G": ORANGE, "6G": "#a855f7",
}


def render(data, filtered, ctx):
    cells_f = filtered["cells"]
    cdrs_f = filtered["cdrs"]

    section("Technology Distribution")
    if not len(cells_f):
        st.info("No cells match filter.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        tc = cells_f["tech"].value_counts().reset_index()
        tc.columns = ["Tech", "Count"]
        fig = px.pie(tc, names="Tech", values="Count", hole=0.55,
                     color="Tech", color_discrete_map=TECH_COLORS)
        fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
        safe_chart(fig)
    with c2:
        if len(cdrs_f):
            td = cdrs_f["tech"].value_counts().reset_index()
            td.columns = ["Tech", "CDRs"]
            fig = px.bar(td, x="Tech", y="CDRs", color="Tech",
                         color_discrete_map=TECH_COLORS)
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
                                   values="record_id",
                                   aggfunc="count").fillna(0)
        if not pivot.empty:
            fig = px.bar(pivot, barmode="stack",
                         color_discrete_map=TECH_COLORS)
            fig.update_layout(height=380, xaxis_title="", yaxis_title="Records",
                              legend_title="Tech",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

    st.write("")
    section("Signal Quality by Technology")
    if len(cdrs_f) and cdrs_f["rsrp"].notna().any():
        df = cdrs_f[cdrs_f["rsrp"].notna()]
        fig = px.violin(df, x="tech", y="rsrp", color="tech", box=True,
                        color_discrete_map=TECH_COLORS)
        fig.update_layout(height=380, showlegend=False,
                          xaxis_title="", yaxis_title="RSRP (dBm)",
                          margin=dict(l=0, r=0, t=10, b=0))
        safe_chart(fig)