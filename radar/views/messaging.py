"""Tab 7 — Messaging Analytics."""

import pandas as pd
import plotly.express as px
import streamlit as st

from radar._config import BLUE, GRAY, GREEN, ORANGE, PURPLE, RED
from radar.services.ui import fmt, safe_chart, section, stat_card


def render(data, filtered, ctx):
    cdrs_f = filtered["cdrs"]

    section("Messaging Analytics")
    msg = cdrs_f[cdrs_f["call_type"].isin(["sms", "mms", "rcs"])] if len(cdrs_f) else pd.DataFrame()
    if not len(msg):
        st.info("No messaging records match filter.")
        return

    c1, c2, c3, c4 = st.columns(4)
    sms = msg[msg["call_type"] == "sms"]
    mms = msg[msg["call_type"] == "mms"]
    rcs = msg[msg["call_type"] == "rcs"]
    with c1:
        stat_card("SMS", fmt(len(sms)), sub="Messages")
    with c2:
        stat_card(
            "MMS",
            fmt(len(mms)),
            sub=(f"{mms['mms_size_bytes'].sum()/1e6:.1f} MB" if len(mms) else "0 MB"),
        )
    with c3:
        stat_card("RCS", fmt(len(rcs)), sub="Rich messages")
    with c4:
        if len(mms):
            succ = (mms["mms_delivery"] == "DELIVERED").mean() * 100
            stat_card("MMS Success", f"{succ:.1f}%", sub="Delivery rate")
        else:
            stat_card("MMS Success", "—", sub="No data")

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        section("MMS Content Types")
        if len(mms):
            ct = mms["mms_content_type"].value_counts().reset_index()
            ct.columns = ["Type", "Count"]
            fig = px.bar(
                ct,
                x="Count",
                y="Type",
                orientation="h",
                color="Count",
                color_continuous_scale=["#f5f3ff", PURPLE],
            )
            fig.update_layout(
                height=380,
                coloraxis_showscale=False,
                xaxis_title="",
                yaxis_title="",
                margin=dict(l=0, r=0, t=10, b=0),
            )
            safe_chart(fig)
    with c2:
        section("MMS Delivery Status")
        if len(mms):
            st_d = mms["mms_delivery"].value_counts().reset_index()
            st_d.columns = ["Status", "Count"]
            fig = px.pie(
                st_d,
                names="Status",
                values="Count",
                hole=0.5,
                color="Status",
                color_discrete_map={
                    "DELIVERED": GREEN,
                    "EXPIRED": ORANGE,
                    "REJECTED": RED,
                    "PENDING": GRAY,
                },
            )
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

    st.write("")
    section("RCS by Type")
    if len(rcs):
        rt = rcs["rcs_type"].value_counts().reset_index()
        rt.columns = ["Type", "Count"]
        fig = px.bar(
            rt,
            x="Type",
            y="Count",
            color="Type",
            color_discrete_sequence=[ORANGE, BLUE, GREEN, PURPLE, GRAY],
        )
        fig.update_layout(
            height=340,
            showlegend=False,
            xaxis_title="",
            yaxis_title="Messages",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        safe_chart(fig)

    st.write("")
    section("MMS Size Distribution")
    if len(mms):
        fig = px.histogram(mms, x="mms_size_bytes", nbins=50, color_discrete_sequence=[PURPLE])
        fig.update_layout(
            height=320,
            xaxis_title="Size (bytes)",
            yaxis_title="Messages",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        safe_chart(fig)
