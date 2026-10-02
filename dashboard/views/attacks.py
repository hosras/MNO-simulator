# -*- coding: utf-8 -*-
"""Tab 12 — Attack Simulation Results."""
import streamlit as st
import plotly.express as px

from telecom_ui_common import chart as _chart
from dashboard.services.ui import kpi, fmt_num


def render(data, filtered):
    st.subheader("🛡️ Attack Simulation Results")
    atk_sc = data.get("attack_scenarios")
    atk_ev = data.get("attack_events")

    if atk_sc is None or atk_sc.empty:
        st.info("No attack data. Run `python telecom_attack.py` "
                "or re-run the simulator.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Scenarios", fmt_num(len(atk_sc)), "Total")
    with c2: kpi("Events", fmt_num(len(atk_ev)), "Samples")
    with c3:
        blk = int((atk_sc["status"] == "BLOCKED").sum())
        kpi("Blocked", f"{blk}/{len(atk_sc)}",
            f"{blk/max(1,len(atk_sc))*100:.0f}%", "#22c55e")
    with c4:
        suc = int((atk_sc["status"] == "SUCCESS").sum())
        kpi("Attacker Success", f"{suc}", "Unblocked", "#ef4444")

    st.write("")
    st.markdown("### Status Distribution")
    fig = px.pie(atk_sc, names="status", hole=0.55, color="status",
                 color_discrete_map={"BLOCKED": "#22c55e", "DETECTED": "#f59e0b",
                                     "SUCCESS": "#ef4444", "ONGOING": "#0ea5e9"})
    fig.update_layout(height=340)
    _chart(fig, use_container_width=True)

    st.markdown("### Attack Type Distribution")
    tc = atk_sc["attack_type"].value_counts().reset_index()
    tc.columns = ["attack_type", "count"]
    fig = px.bar(tc, x="count", y="attack_type", orientation="h",
                 color="count", color_continuous_scale="Reds")
    fig.update_layout(height=400, coloraxis_showscale=False,
                      xaxis_title="", yaxis_title="")
    _chart(fig, use_container_width=True)

    st.markdown("### Severity × Status Matrix")
    if not atk_ev.empty:
        fig = px.line(atk_ev.sort_values("ts"), x="ts", y="latency_ms",
                      color="attack_type", markers=False)
        fig.update_layout(height=380, xaxis_title="", yaxis_title="Latency (ms)")
        _chart(fig, use_container_width=True)

    st.markdown("### MTTD Distribution")
    if not atk_ev.empty and atk_ev["mttd_sec"].notna().any():
        fig = px.histogram(atk_ev.dropna(subset=["mttd_sec"]),
                           x="mttd_sec", nbins=40,
                           color_discrete_sequence=["#f59e0b"])
        fig.update_layout(height=340, xaxis_title="MTTD (sec)", yaxis_title="")
        _chart(fig, use_container_width=True)

    st.markdown("### MTTR Distribution")
    if not atk_ev.empty and atk_ev["mttr_sec"].notna().any():
        fig = px.histogram(atk_ev.dropna(subset=["mttr_sec"]),
                           x="mttr_sec", nbins=40,
                           color_discrete_sequence=["#22c55e"])
        fig.update_layout(height=340, xaxis_title="MTTR (sec)", yaxis_title="")
        _chart(fig, use_container_width=True)

    st.markdown("### Full Scenario Table")
    st.dataframe(atk_sc, use_container_width=True, hide_index=True, height=350)