# -*- coding: utf-8 -*-
"""Tab 3 — Time Series."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from radar._config import ORANGE, BLUE, GREEN, PURPLE, GRAY, RED
from radar.services.ui import section, safe_chart


def render(data, filtered, ctx):
    cdrs_f = filtered["cdrs"]

    section("Traffic Over Time")
    if not len(cdrs_f):
        st.info("No data for current filter.")
        return

    hourly = cdrs_f.groupby("hour").agg(
        records=("record_id", "count"),
        bytes=("bytes", "sum"),
    ).reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=hourly["hour"], y=hourly["records"],
                         name="CDR Records", marker_color=ORANGE, opacity=0.75),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=hourly["hour"], y=hourly["bytes"] / 1e6,
                             name="Data Volume (MB)", mode="lines+markers",
                             line=dict(color=BLUE, width=2.5)),
                  secondary_y=True)
    fig.update_layout(
        height=420, xaxis=dict(title="Hour of Day", dtick=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        margin=dict(l=0, r=0, t=40, b=0), hovermode="x unified",
    )
    fig.update_yaxes(title_text="Records", secondary_y=False)
    fig.update_yaxes(title_text="MB", secondary_y=True)
    safe_chart(fig)

    st.write("")
    section("Daily Trend")
    daily = cdrs_f.groupby("day").agg(
        records=("record_id", "count"),
        bytes=("bytes", "sum"),
    ).reset_index()
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
                     color_discrete_sequence=[ORANGE, BLUE, GREEN,
                                              PURPLE, GRAY, RED])
        fig.update_layout(height=380, xaxis=dict(dtick=1),
                          xaxis_title="Hour", yaxis_title="Records",
                          legend_title="Type",
                          margin=dict(l=0, r=0, t=10, b=0))
        safe_chart(fig)