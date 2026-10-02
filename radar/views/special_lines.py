# -*- coding: utf-8 -*-
"""Tab 10 — Special Lines Analytics."""
import pandas as pd
import streamlit as st
import plotly.express as px

from radar._config import ORANGE, BLUE, GREEN, RED, PURPLE, GRAY
from radar.services.ui import stat_card, section, safe_chart, fmt


def render(data, filtered, ctx):
    sig = ctx.get("sig", {})
    subs_f = filtered["subs"]

    section("🔑 Special Lines Analytics")
    sl = sig.get("special_line_traffic", {})
    if not sl:
        st.info("No special lines data.")
        return

    total = sum(sl.values())
    special = total - sl.get("Normal", 0)
    special_pct = special / total * 100 if total else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: stat_card("Total Events", fmt(total), sub="All classes")
    with c2: stat_card("Special Events", fmt(special),
                       sub=f"{special_pct:.1f}% of total")
    with c3: stat_card("Line Classes", fmt(len(sl)), sub="Active classes")
    with c4:
        top_class = max(sl.items(), key=lambda x: x[1])[0] if sl else "—"
        stat_card("Top Class", top_class,
                  sub=f"{fmt(sl[top_class])} events" if top_class != "—" else "")

    st.write("")
    section("Traffic Distribution by Line Class")
    sl_df = pd.DataFrame(list(sl.items()), columns=["Class", "Events"])
    sl_df = sl_df.sort_values("Events", ascending=False)
    fig = px.bar(sl_df, x="Class", y="Events", color="Class",
                 color_discrete_map={"Normal": GRAY, "VIP": GREEN,
                                     "Government": RED, "Corporate": BLUE,
                                     "Emergency": ORANGE, "Test": PURPLE},
                 text="Events")
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(height=400, showlegend=False,
                      xaxis_title="", yaxis_title="Events",
                      margin=dict(l=0, r=0, t=10, b=0))
    safe_chart(fig)

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        section("Filter-Bypass Heavy Users")
        fb = sig.get("filter_bypass_users", [])
        if fb:
            fb_df = pd.DataFrame(fb, columns=["MSISDN", "Sessions"])
            fb_df = fb_df.sort_values("Sessions", ascending=False).head(15)
            fig = px.bar(fb_df, x="Sessions", y="MSISDN", orientation="h",
                         color="Sessions",
                         color_continuous_scale=["#fef2f2", ORANGE, RED])
            fig.update_layout(height=380, coloraxis_showscale=False,
                              xaxis_title="Sessions", yaxis_title="",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)
        else:
            st.info("No filter-bypass activity.")
    with c2:
        section("Priority QoS Distribution")
        if "priority_qos" in subs_f.columns:
            qos = (subs_f["priority_qos"].value_counts().sort_index()
                   .reset_index())
            qos.columns = ["QoS", "Subscribers"]
            fig = px.bar(qos, x="QoS", y="Subscribers", color="Subscribers",
                         color_continuous_scale=["#fef3c7", ORANGE, RED])
            fig.update_layout(height=380, coloraxis_showscale=False,
                              xaxis=dict(dtick=1),
                              xaxis_title="QoS Class", yaxis_title="",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)