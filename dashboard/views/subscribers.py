"""Tab 10 — Subscriber Analytics."""

import plotly.express as px
import streamlit as st

from telecom_ui_common import chart as _chart
from telecom_ui_common import csv_download


def render(data, filtered):
    subs = filtered["subs"]
    st.subheader("Subscriber Analytics")

    if not len(subs):
        st.info("No subscriber data available.")
        return

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        plan_count = subs["plan"].value_counts().reset_index()
        plan_count.columns = ["plan", "count"]
        fig = px.bar(
            plan_count,
            x="count",
            y="plan",
            orientation="h",
            title="Plan Distribution",
            color="count",
            color_continuous_scale="Blues",
        )
        fig.update_layout(height=340, coloraxis_showscale=False, xaxis_title="", yaxis_title="")
        _chart(fig, use_container_width=True)
    with sc2:
        fig = px.histogram(
            subs,
            x="risk_score",
            nbins=40,
            title="Risk Score Distribution",
            color_discrete_sequence=["#f59e0b"],
        )
        fig.update_layout(height=340, xaxis_title="Risk Score", yaxis_title="Count")
        _chart(fig, use_container_width=True)
    with sc3:
        roam = subs["roaming_enabled"].value_counts().reset_index()
        roam.columns = ["roaming", "count"]
        roam["label"] = roam["roaming"].map({0: "Disabled", 1: "Enabled"})
        fig = px.pie(
            roam,
            names="label",
            values="count",
            hole=0.55,
            title="Roaming Status",
            color="label",
            color_discrete_map={"Enabled": "#22c55e", "Disabled": "#94a3b8"},
        )
        fig.update_layout(height=340)
        _chart(fig, use_container_width=True)

    st.markdown("#### 📋 Subscriber Sample List")
    st.dataframe(subs.head(500), use_container_width=True, height=350, hide_index=True)
    csv_download(subs, "subscribers_filtered.csv")
