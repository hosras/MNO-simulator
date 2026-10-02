# -*- coding: utf-8 -*-
"""Tab 6 — SIGINT Analysis."""
import pandas as pd
import streamlit as st
import plotly.express as px

from telecom_ui_common import chart as _chart, csv_download
from dashboard.services.ui import kpi, fmt_num


def render(data, filtered):
    sig = data["findings"].get("SIGINT", {})
    st.subheader("🕵️ SIGINT Analysis - Signal & Metadata")

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        kpi("IMEI Churn", fmt_num(len(sig.get("imei_churn_suspects", []))),
            "Possible SIM clone", "#ef4444")
    with s2:
        kpi("SIM-Box", fmt_num(len(sig.get("simbox_suspects", []))),
            "Suspicious traffic", "#f59e0b")
    with s3:
        kpi("Impossible Travel", fmt_num(len(sig.get("impossible_travel", []))),
            "Anomalous movement", "#a855f7")
    with s4:
        kpi("Weak Cells", fmt_num(len(sig.get("weak_cells", []))),
            "Low quality", "#0ea5e9")

    st.write("")

    st.markdown("### 🔴 IMEI Churn - Multiple IMEIs per IMSI")
    imei_churn = sig.get("imei_churn_suspects", [])
    if imei_churn:
        df_churn = pd.DataFrame(imei_churn, columns=["imsi", "distinct_imeis"])
        fig = px.bar(df_churn.head(15), x="imsi", y="distinct_imeis",
                     title="IMSIs with Most Distinct IMEIs",
                     color="distinct_imeis", color_continuous_scale="Reds")
        fig.update_layout(height=340, coloraxis_showscale=False,
                          xaxis_title="IMSI", yaxis_title="Distinct IMEIs")
        _chart(fig, use_container_width=True)
        st.dataframe(df_churn, use_container_width=True, hide_index=True, height=200)
        csv_download(df_churn, "sigint_imei_churn.csv")
    else:
        st.success("No suspects found.")

    st.divider()

    st.markdown("### 🟠 SIM-Box - Bulk Short Calls")
    simbox = sig.get("simbox_suspects", [])
    if simbox:
        df_sb = pd.DataFrame(simbox)
        c1, c2 = st.columns(2)
        with c1:
            fig = px.scatter(df_sb, x="out_calls", y="unique_targets",
                             size="short_call_ratio", color="short_call_ratio",
                             hover_data=["msisdn"],
                             title="SIM-Box Suspects Distribution",
                             color_continuous_scale="OrRd")
            fig.update_layout(height=340)
            _chart(fig, use_container_width=True)
        with c2:
            st.dataframe(df_sb, use_container_width=True, height=340, hide_index=True)
        csv_download(df_sb, "sigint_simbox.csv")
    else:
        st.success("No suspects found.")

    st.divider()

    st.markdown("### 🟣 Impossible Travel - Anomalous Movement")
    imp = sig.get("impossible_travel", [])
    if imp:
        df_imp = pd.DataFrame(imp)
        fig = px.scatter(df_imp, x="km", y="speed_kmh",
                         size="dt_sec", color="speed_kmh",
                         hover_data=["msisdn", "from", "to", "dt_sec"],
                         title="Impossible Travel Events (speed > 900 km/h)",
                         color_continuous_scale="Purples")
        fig.update_layout(height=380, xaxis_title="Distance (km)",
                          yaxis_title="Speed (km/h)")
        _chart(fig, use_container_width=True)
        st.dataframe(df_imp, use_container_width=True, hide_index=True, height=220)
        csv_download(df_imp, "sigint_impossible_travel.csv")
    else:
        st.success("No suspects found.")

    st.divider()

    st.markdown("### 🔵 Weak Cells")
    weak = sig.get("weak_cells", [])
    if weak:
        df_w = pd.DataFrame(weak, columns=["cell_id", "bad_samples"])
        st.dataframe(df_w.head(20), use_container_width=True,
                     hide_index=True, height=250)
        csv_download(df_w, "sigint_weak_cells.csv")
    else:
        st.success("No weak cells found.")