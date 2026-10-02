# -*- coding: utf-8 -*-
"""Tab 5 — OSINT Analysis."""
import streamlit as st
import plotly.express as px

from telecom_ui_common import chart as _chart, csv_download
from dashboard.services.ui import kpi, fmt_num


def render(data, filtered):
    osint_reg = data["osint_reg"]
    osint_comp = data["osint_comp"]

    st.subheader("🌐 OSINT Analysis - Public Sources")

    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        kpi("Public Registry Rows", fmt_num(len(osint_reg)), "Public Registry")
    with oc2:
        kpi("Public Complaints", fmt_num(len(osint_comp)),
            "Social Complaints", "#f59e0b")
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
    st.dataframe(osint_reg.head(200), use_container_width=True,
                 height=280, hide_index=True)
    csv_download(osint_reg, "osint_registry.csv")

    st.markdown("#### 📋 Public Complaints (Sample)")
    st.dataframe(osint_comp.head(200), use_container_width=True,
                 height=280, hide_index=True)
    csv_download(osint_comp, "osint_complaints.csv")