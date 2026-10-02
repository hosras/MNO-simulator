# -*- coding: utf-8 -*-
"""Tab 7 — Special Lines & Privileged Access."""
import pandas as pd
import streamlit as st
import plotly.express as px

from telecom_ui_common import chart as _chart, csv_download
from dashboard.services.ui import kpi, fmt_num


def render(data, filtered):
    subs = filtered["subs"]
    cdrs = filtered["cdrs"]
    sig = data["findings"].get("SIGINT", {})

    st.subheader("🔑 Special Lines & Privileged Access")

    if "line_class" not in subs.columns:
        st.warning("Database does not contain special-line fields. Please re-run the simulator.")
        return

    sp = subs[subs["line_class"] != "Normal"]
    g1, g2, g3, g4, g5 = st.columns(5)
    with g1: kpi("Special Lines", fmt_num(len(sp)), "Non-Normal class", "#22c55e")
    with g2: kpi("Filter Bypass", fmt_num(int(subs["filter_bypass"].sum())),
                 "Unfiltered intl internet", "#f59e0b")
    with g3: kpi("CLIR Enabled", fmt_num(int(subs["clir_enabled"].sum())),
                 "No Caller ID", "#0ea5e9")
    with g4: kpi("CLIR Override", fmt_num(int(subs["clir_override"].sum())),
                 "Can spoof caller ID", "#ef4444")
    with g5: kpi("Lawful Intercept", fmt_num(int(subs["lawful_intercept"].sum())),
                 "LI-flagged", "#a855f7")

    st.write("")

    c1, c2 = st.columns(2)
    with c1:
        lc = subs["line_class"].value_counts().reset_index()
        lc.columns = ["line_class", "count"]
        fig = px.pie(lc, names="line_class", values="count", hole=0.55,
                     title="Subscriber Distribution by Line Class",
                     color="line_class",
                     color_discrete_map={
                         "Normal": "#94a3b8", "VIP": "#22c55e",
                         "Government": "#ef4444", "Corporate": "#0ea5e9",
                         "Emergency": "#f59e0b", "Test": "#a855f7"})
        fig.update_layout(height=350)
        _chart(fig, use_container_width=True)

    with c2:
        qos = subs["priority_qos"].value_counts().sort_index().reset_index()
        qos.columns = ["qos", "count"]
        fig = px.bar(qos, x="qos", y="count",
                     title="Priority QoS Distribution (0=lowest, 9=highest)",
                     color="count", color_continuous_scale="Turbo")
        fig.update_layout(height=350, coloraxis_showscale=False,
                          xaxis=dict(dtick=1),
                          xaxis_title="QoS Class", yaxis_title="Subscribers")
        _chart(fig, use_container_width=True)

    st.markdown("#### 📊 Capabilities Matrix by Line Class")
    cap = subs.groupby("line_class").agg(
        count=("msisdn", "count"),
        intl_access=("international_access", "sum"),
        filter_bypass=("filter_bypass", "sum"),
        clir=("clir_enabled", "sum"),
        clir_override=("clir_override", "sum"),
        lawful=("lawful_intercept", "sum"),
        direct=("direct_routing", "sum"),
        avg_qos=("priority_qos", "mean"),
    ).round(2).reset_index()
    st.dataframe(cap, use_container_width=True, hide_index=True)
    csv_download(cap, "special_lines_matrix.csv")

    st.divider()
    st.markdown("### 📡 Special-Line Traffic (from CDR)")

    if "line_class" in cdrs.columns and len(cdrs):
        clir_used = cdrs[cdrs["clir_used"] == 1]
        t1, t2 = st.columns(2)

        with t1:
            if len(clir_used):
                cl = clir_used.groupby("line_class").size().reset_index(name="count")
                fig = px.bar(cl, x="line_class", y="count",
                             title="CLIR (No-Caller-ID) Usage by Line Class",
                             color="count", color_continuous_scale="Blues")
                fig.update_layout(height=340, coloraxis_showscale=False,
                                  xaxis_title="", yaxis_title="Calls")
                _chart(fig, use_container_width=True)
            else:
                st.info("No CLIR usage found.")

        with t2:
            rt = cdrs["routing_class"].value_counts().reset_index()
            rt.columns = ["routing_class", "count"]
            fig = px.pie(rt, names="routing_class", values="count", hole=0.5,
                         title="Routing Class Mix",
                         color="routing_class",
                         color_discrete_map={
                             "Normal": "#94a3b8", "Priority": "#22c55e",
                             "Direct": "#ef4444", "International": "#0ea5e9"})
            fig.update_layout(height=340)
            _chart(fig, use_container_width=True)

        intl = cdrs[cdrs["international"] == 1]
        if len(intl):
            intl_h = intl.groupby("hour").size().reset_index(name="count")
            fig = px.line(intl_h, x="hour", y="count", markers=True,
                          title="International Traffic by Hour (whitelisted / bypass)")
            fig.update_traces(line_color="#0ea5e9")
            fig.update_layout(height=320, xaxis=dict(dtick=1),
                              xaxis_title="Hour", yaxis_title="Sessions")
            _chart(fig, use_container_width=True)

        fv = cdrs.groupby(["filter_applied", "international"]).size().reset_index(name="count")
        fv["label"] = fv.apply(
            lambda r: ("Filtered" if r["filter_applied"] else "Unfiltered") +
                      (" / Intl" if r["international"] else " / Domestic"), axis=1)
        fig = px.bar(fv, x="label", y="count",
                     title="Filtered vs Unfiltered Traffic", color="label")
        fig.update_layout(height=340, showlegend=False,
                          xaxis_title="", yaxis_title="Records")
        _chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### 🕵️ Special-Line SIGINT Findings")

    f1, f2, f3 = st.columns(3)
    with f1:
        abuse = sig.get("clir_abuse", [])
        kpi("CLIR Abuse Events", fmt_num(len(abuse)),
            "Unauthorized no-caller-ID", "#ef4444")
    with f2:
        bypass = sig.get("filter_bypass_users", [])
        kpi("Top Bypass Users", fmt_num(len(bypass)),
            "Heavy unfiltered traffic", "#f59e0b")
    with f3:
        prio = sig.get("priority_by_class", {})
        kpi("Priority Classes", fmt_num(len(prio)),
            "Active priority users", "#22c55e")

    st.write("")
    st.markdown("#### ⚠️ Unauthorized CLIR Usage")
    abuse = sig.get("clir_abuse", [])
    if abuse:
        df_ab = pd.DataFrame(abuse)
        st.dataframe(df_ab, use_container_width=True, hide_index=True, height=250)
        csv_download(df_ab, "clir_abuse.csv")
    else:
        st.success("No CLIR abuse detected.")

    st.markdown("#### ⚠️ Top Filter-Bypass Users (Unfiltered International)")
    bypass = sig.get("filter_bypass_users", [])
    if bypass:
        df_by = pd.DataFrame(bypass, columns=["msisdn", "unfiltered_sessions"])
        fig = px.bar(df_by, x="msisdn", y="unfiltered_sessions",
                     title="Top MSISDNs by Unfiltered International Sessions",
                     color="unfiltered_sessions", color_continuous_scale="OrRd")
        fig.update_layout(height=340, coloraxis_showscale=False,
                          xaxis_title="MSISDN", yaxis_title="Sessions")
        _chart(fig, use_container_width=True)
        st.dataframe(df_by, use_container_width=True, hide_index=True)
        csv_download(df_by, "filter_bypass_users.csv")
    else:
        st.info("No filter-bypass traffic recorded.")

    st.markdown("#### 🌍 Top International Traffic Users")
    intl_users = sig.get("top_intl_users", [])
    if intl_users:
        df_iu = pd.DataFrame(intl_users, columns=["msisdn", "intl_sessions"])
        st.dataframe(df_iu, use_container_width=True, hide_index=True)
        csv_download(df_iu, "top_intl_users.csv")

    st.markdown("#### 📋 Full Special Line Subscriber List")
    sp_full = subs[subs["line_class"] != "Normal"].copy()
    st.dataframe(sp_full, use_container_width=True, hide_index=True, height=350)
    csv_download(sp_full, "special_lines_full.csv")