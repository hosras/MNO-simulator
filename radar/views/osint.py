"""Tab 12 — OSINT Radar."""

import plotly.express as px
import streamlit as st

from radar._config import BLUE, GREEN, ORANGE, PURPLE, RED
from radar.services.ui import fmt, safe_chart, section, stat_card


def render(data, filtered, ctx):
    osint_comp = data["osint_comp"]

    section("🌐 OSINT Radar — Public Insights")
    if not len(osint_comp):
        st.info("No OSINT data.")
        return

    total = len(osint_comp)
    neg = int((osint_comp["sentiment"] == "negative").sum())
    neu = int((osint_comp["sentiment"] == "neutral").sum())
    pos = int((osint_comp["sentiment"] == "positive").sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Complaints", fmt(total), sub="Public sources")
    with c2:
        stat_card("Negative", fmt(neg), sub=f"{neg/total*100:.0f}%")
    with c3:
        stat_card("Neutral", fmt(neu), sub=f"{neu/total*100:.0f}%")
    with c4:
        stat_card("Positive", fmt(pos), sub=f"{pos/total*100:.0f}%")

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        section("Top Complaint Topics")
        tc = osint_comp["topic"].value_counts().reset_index()
        tc.columns = ["Topic", "Count"]
        fig = px.bar(
            tc,
            x="Count",
            y="Topic",
            orientation="h",
            color="Count",
            color_continuous_scale=["#fef2f2", RED],
        )
        fig.update_layout(
            height=400,
            coloraxis_showscale=False,
            xaxis_title="",
            yaxis_title="",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        safe_chart(fig)
    with c2:
        section("Sentiment Mix")
        sm = osint_comp["sentiment"].value_counts().reset_index()
        sm.columns = ["Sentiment", "Count"]
        fig = px.pie(
            sm,
            names="Sentiment",
            values="Count",
            hole=0.55,
            color="Sentiment",
            color_discrete_map={"negative": RED, "neutral": ORANGE, "positive": GREEN},
        )
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
        safe_chart(fig)

    st.write("")
    section("Complaints by City")
    cc = osint_comp["city"].value_counts().reset_index()
    cc.columns = ["City", "Count"]
    fig = px.bar(cc, x="City", y="Count", color="Count", color_continuous_scale=["#fff7ed", ORANGE])
    fig.update_layout(
        height=340,
        coloraxis_showscale=False,
        xaxis_title="",
        yaxis_title="Complaints",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    safe_chart(fig)

    st.write("")
    section("Complaint Source Distribution")
    sc = osint_comp["source"].value_counts().reset_index()
    sc.columns = ["Source", "Count"]
    fig = px.pie(
        sc,
        names="Source",
        values="Count",
        hole=0.5,
        color_discrete_sequence=[ORANGE, BLUE, GREEN, PURPLE, RED],
    )
    fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0))
    safe_chart(fig)
