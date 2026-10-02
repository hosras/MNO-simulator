"""Tab 2 — Traffic Analysis (CDR)."""

import plotly.express as px
import streamlit as st

from dashboard._config import TECH_COLORS
from telecom_ui_common import chart as _chart
from telecom_ui_common import csv_download


def render(data, filtered):
    cdrs = filtered["cdrs"]
    st.subheader("Traffic Analysis (CDR)")

    if not len(cdrs):
        st.info("No records match the current filter.")
        return

    a1, a2 = st.columns([2, 1])

    with a1:
        by_hour = cdrs.groupby("hour").size().reset_index(name="count")
        fig = px.area(
            by_hour, x="hour", y="count", title="Traffic Distribution by Hour", markers=True
        )
        fig.update_traces(line_color="#0ea5e9", fillcolor="rgba(14,165,233,0.25)")
        fig.update_layout(
            height=320, xaxis=dict(dtick=1), xaxis_title="Hour", yaxis_title="Records"
        )
        _chart(fig, use_container_width=True)

    with a2:
        type_count = cdrs["call_type"].value_counts().reset_index()
        type_count.columns = ["call_type", "count"]
        fig = px.pie(
            type_count, names="call_type", values="count", hole=0.5, title="Traffic Mix by Type"
        )
        fig.update_layout(height=320, margin=dict(l=0, r=0, t=40, b=0))
        _chart(fig, use_container_width=True)

    st.markdown("#### 🔥 Traffic Heatmap (City × Hour)")
    pivot = cdrs.pivot_table(
        index="city", columns="hour", values="record_id", aggfunc="count"
    ).fillna(0)
    if not pivot.empty:
        fig = px.imshow(
            pivot,
            aspect="auto",
            color_continuous_scale="YlOrRd",
            labels=dict(x="Hour", y="City", color="Volume"),
        )
        fig.update_layout(height=420)
        _chart(fig, use_container_width=True)

    b1, b2 = st.columns(2)
    with b1:
        by_tech = cdrs.groupby("tech").size().reset_index(name="count")
        fig = px.bar(
            by_tech,
            x="tech",
            y="count",
            color="tech",
            title="Traffic Volume by Technology",
            color_discrete_map=TECH_COLORS,
        )
        fig.update_layout(height=320, showlegend=False, xaxis_title="", yaxis_title="")
        _chart(fig, use_container_width=True)

    with b2:
        by_city = (
            cdrs.groupby("city")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=True)
        )
        fig = px.bar(
            by_city,
            x="count",
            y="city",
            orientation="h",
            title="Traffic Volume by City",
            color="count",
            color_continuous_scale="Purples",
        )
        fig.update_layout(height=320, coloraxis_showscale=False, xaxis_title="", yaxis_title="")
        _chart(fig, use_container_width=True)

    st.markdown("#### 📋 CDR Sample Records")
    st.dataframe(cdrs.head(500), use_container_width=True, height=300)
    csv_download(cdrs, "cdrs_filtered.csv", "Download All Filtered CDRs")
