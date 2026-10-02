"""Tab 4 — Traffic Mix."""

import plotly.express as px
import streamlit as st

from radar._config import BLUE, GRAY, GREEN, ORANGE, PURPLE, RED
from radar.services.ui import safe_chart, section


def render(data, filtered, ctx):
    cdrs_f = filtered["cdrs"]

    section("Traffic Composition")
    if not len(cdrs_f):
        st.info("No data.")
        return

    c1, c2 = st.columns(2)
    with c1:
        tc = cdrs_f["call_type"].value_counts().reset_index()
        tc.columns = ["Type", "Count"]
        fig = px.pie(
            tc,
            names="Type",
            values="Count",
            hole=0.6,
            color_discrete_sequence=[ORANGE, BLUE, GREEN, PURPLE, GRAY, RED],
        )
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
        fig.update_traces(textposition="outside", textinfo="label+percent")
        safe_chart(fig)
    with c2:
        agg = (
            cdrs_f.groupby("call_type")
            .agg(
                avg_dur=("duration_sec", "mean"),
                avg_bytes=("bytes", "mean"),
                total=("record_id", "count"),
            )
            .round(1)
            .reset_index()
        )
        fig = px.bar(
            agg,
            x="call_type",
            y="avg_dur",
            text="avg_dur",
            color="call_type",
            color_discrete_sequence=[ORANGE, BLUE, GREEN, PURPLE, GRAY, RED],
        )
        fig.update_traces(texttemplate="%{text}s", textposition="outside")
        fig.update_layout(
            height=400,
            showlegend=False,
            xaxis_title="",
            yaxis_title="Avg Duration (sec)",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        safe_chart(fig)

    st.write("")
    section("Result Distribution (Call Outcome)")
    if "result" in cdrs_f.columns:
        rc = cdrs_f["result"].value_counts().reset_index()
        rc.columns = ["Result", "Count"]
        fig = px.bar(
            rc,
            x="Result",
            y="Count",
            color="Result",
            color_discrete_map={
                "ANSWERED": GREEN,
                "NO_ANSWER": GRAY,
                "BUSY": ORANGE,
                "FAILED": RED,
                "OK": GREEN,
                "DELIVERED": GREEN,
                "EXPIRED": ORANGE,
                "REJECTED": RED,
                "PENDING": GRAY,
            },
        )
        fig.update_layout(
            height=320,
            showlegend=False,
            xaxis_title="",
            yaxis_title="Records",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        safe_chart(fig)
