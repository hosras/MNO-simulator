"""Tab 13 — Attack Radar."""

import plotly.express as px
import streamlit as st

from radar._config import BLUE, GRAY, GREEN, ORANGE, RED
from radar.services.ui import csv_btn, fmt, safe_chart, section, stat_card


def render(data, filtered, ctx):
    section("Attack Analytics")
    asc = data.get("attack_scenarios")
    aev = data.get("attack_events")

    if asc is None or asc.empty:
        st.info("No attack data. Run `python telecom_attack.py`.")
        return

    total = len(asc)
    by_status = asc["status"].value_counts().to_dict()
    blk = by_status.get("BLOCKED", 0)
    suc = by_status.get("SUCCESS", 0)
    det = by_status.get("DETECTED", 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        stat_card("Scenarios", fmt(total), sub="Total")
    with c2:
        stat_card("Blocked", fmt(blk), sub=f"{blk/total*100:.0f}%")
    with c3:
        stat_card("Detected", fmt(det), sub=f"{det/total*100:.0f}%")
    with c4:
        stat_card("Attacker Wins", fmt(suc), sub=f"{suc/total*100:.0f}%")
    with c5:
        crit = int((asc["severity"] == "CRITICAL").sum())
        stat_card("CRITICAL", fmt(crit), sub="Severity")

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        section("Severity Distribution")
        sv = asc["severity"].value_counts().reset_index()
        sv.columns = ["severity", "count"]
        fig = px.bar(
            sv,
            x="severity",
            y="count",
            color="severity",
            color_discrete_map={"CRITICAL": RED, "HIGH": ORANGE, "MEDIUM": BLUE, "LOW": GRAY},
        )
        fig.update_layout(height=360, showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
        safe_chart(fig)
    with c2:
        section("Layer Distribution")
        lc = asc["target_layer"].value_counts().reset_index()
        lc.columns = ["layer", "count"]
        fig = px.pie(lc, names="layer", values="count", hole=0.55)
        fig.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0))
        safe_chart(fig)

    st.write("")
    section("Impact: Latency and Drop Over Time")
    if aev is not None and not aev.empty:
        fig = px.scatter(
            aev.sort_values("ts"),
            x="ts",
            y="latency_ms",
            size="drop_pct",
            color="severity",
            color_discrete_map={"CRITICAL": RED, "HIGH": ORANGE, "MEDIUM": BLUE, "LOW": GRAY},
            hover_data=["attack_type", "target_node", "pps"],
        )
        fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0))
        safe_chart(fig)

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        section("MTTD by Attack Type")
        if aev is not None and not aev.empty and aev["mttd_sec"].notna().any():
            mt = (
                aev.dropna(subset=["mttd_sec"])
                .groupby("attack_type")["mttd_sec"]
                .mean()
                .reset_index()
                .sort_values("mttd_sec")
            )
            fig = px.bar(
                mt,
                x="mttd_sec",
                y="attack_type",
                orientation="h",
                color="mttd_sec",
                color_continuous_scale=["#f0fdf4", GREEN, ORANGE, RED],
            )
            fig.update_layout(
                height=420,
                coloraxis_showscale=False,
                xaxis_title="MTTD (sec)",
                yaxis_title="",
                margin=dict(l=0, r=0, t=10, b=0),
            )
            safe_chart(fig)
    with c2:
        section("MTTR by Attack Type")
        if aev is not None and not aev.empty and aev["mttr_sec"].notna().any():
            mt = (
                aev.dropna(subset=["mttr_sec"])
                .groupby("attack_type")["mttr_sec"]
                .mean()
                .reset_index()
                .sort_values("mttr_sec")
            )
            fig = px.bar(
                mt,
                x="mttr_sec",
                y="attack_type",
                orientation="h",
                color="mttr_sec",
                color_continuous_scale=["#eff6ff", BLUE, ORANGE],
            )
            fig.update_layout(
                height=420,
                coloraxis_showscale=False,
                xaxis_title="MTTR (sec)",
                yaxis_title="",
                margin=dict(l=0, r=0, t=10, b=0),
            )
            safe_chart(fig)

    st.write("")
    section("Scenario Details")
    st.dataframe(asc, use_container_width=True, hide_index=True, height=380)
    csv_btn(asc, "attack_scenarios.csv")
