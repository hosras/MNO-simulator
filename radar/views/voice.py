"""Tab 6 — Voice Analytics."""

import pandas as pd
import plotly.express as px
import streamlit as st

from radar._config import BLUE, GRAY, GREEN, ORANGE
from radar.services.ui import fmt, safe_chart, section, stat_card


def render(data, filtered, ctx):
    cdrs_f = filtered["cdrs"]

    section("Voice Analytics")
    v = cdrs_f[cdrs_f["call_type"] == "voice"] if len(cdrs_f) else pd.DataFrame()
    if not len(v):
        st.info("No voice records match filter.")
        return

    total_calls = len(v)
    answered = int((v["result"] == "ANSWERED").sum())
    asr = answered / total_calls * 100 if total_calls else 0
    avg_dur = v["duration_sec"].mean()
    total_min = v["duration_sec"].sum() / 60

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Total Calls", fmt(total_calls), sub="Voice only")
    with c2:
        stat_card("Answer Rate", f"{asr:.1f}%", sub=f"{fmt(answered)} answered")
    with c3:
        stat_card("Avg Duration", f"{avg_dur:.0f}s", sub="Per call")
    with c4:
        stat_card("Total Minutes", fmt(total_min), sub="Talk time")

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        section("Voice Bearer Mix")
        if "voice_bearer" in v.columns:
            bm = v["voice_bearer"].value_counts().reset_index()
            bm.columns = ["Bearer", "Count"]
            fig = px.pie(
                bm,
                names="Bearer",
                values="Count",
                hole=0.55,
                color="Bearer",
                color_discrete_map={"VoLTE": GREEN, "VoNR": ORANGE, "VoWiFi": BLUE, "CSFB": GRAY},
            )
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)
    with c2:
        section("Codec Distribution")
        if "voice_codec" in v.columns:
            cd = v["voice_codec"].value_counts().reset_index()
            cd.columns = ["Codec", "Count"]
            fig = px.bar(
                cd, x="Codec", y="Count", color="Count", color_continuous_scale=["#eff6ff", BLUE]
            )
            fig.update_layout(
                height=380,
                coloraxis_showscale=False,
                xaxis_title="",
                yaxis_title="Calls",
                margin=dict(l=0, r=0, t=10, b=0),
            )
            safe_chart(fig)

    st.write("")
    section("Voice Bearer by Technology")
    if "voice_bearer" in v.columns:
        pivot = v.pivot_table(
            index="tech", columns="voice_bearer", values="record_id", aggfunc="count"
        ).fillna(0)
        if not pivot.empty:
            fig = px.imshow(
                pivot,
                aspect="auto",
                text_auto=True,
                color_continuous_scale=["#f0fdf4", "#22c55e", "#15803d"],
            )
            fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

    st.write("")
    section("Average Call Duration by Bearer")
    if "voice_bearer" in v.columns:
        dur = v.groupby("voice_bearer")["duration_sec"].mean().reset_index()
        dur.columns = ["Bearer", "AvgSec"]
        dur = dur.sort_values("AvgSec", ascending=False)
        fig = px.bar(
            dur,
            x="Bearer",
            y="AvgSec",
            text="AvgSec",
            color="Bearer",
            color_discrete_map={"VoLTE": GREEN, "VoNR": ORANGE, "VoWiFi": BLUE, "CSFB": GRAY},
        )
        fig.update_traces(texttemplate="%{text:.0f}s", textposition="outside")
        fig.update_layout(
            height=340,
            showlegend=False,
            xaxis_title="",
            yaxis_title="Avg Duration (sec)",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        safe_chart(fig)
