# -*- coding: utf-8 -*-
"""Tab 3 — Signal Quality (RF layer)."""
import pandas as pd
import streamlit as st
import plotly.express as px

from telecom_ui_common import chart as _chart, csv_download


def render(data, filtered):
    cdrs = filtered["cdrs"]
    sig = data["findings"].get("SIGINT", {})
    st.subheader("Radio Signal Quality (SIGINT - RF Layer)")

    df4g = cdrs[cdrs["rsrp"].notna()]
    if not len(df4g):
        st.info("No 4G/5G signal data matches the current filter.")
        return

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