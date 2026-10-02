"""Tab 9 — Alert Engine & SMS Notifications."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.services.ui import fmt_num, kpi
from telecom_ui_common import chart as _chart
from telecom_ui_common import csv_download


def render(data, filtered):
    alerts_df = data["alerts"]
    sms_alerts_df = data["sms_alerts"]

    st.subheader("🚨 Alert Engine & SMS Notifications")

    if alerts_df.empty:
        st.info("No alerts recorded. Run the simulator.")
        return

    fa1, fa2, fa3 = st.columns(3)
    with fa1:
        sev_filter = st.multiselect(
            "Severity",
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            default=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        )
    with fa2:
        type_filter = st.multiselect(
            "Alert Type",
            sorted(alerts_df["alert_type"].unique()),
            default=sorted(alerts_df["alert_type"].unique()),
        )
    with fa3:
        only_unack = st.checkbox("Only Unacknowledged", value=False)

    adf = alerts_df[
        alerts_df["severity"].isin(sev_filter) & alerts_df["alert_type"].isin(type_filter)
    ]
    if only_unack:
        adf = adf[adf["ack"] == 0]

    a1, a2, a3, a4, a5 = st.columns(5)
    with a1:
        kpi("Total Alerts", fmt_num(len(alerts_df)), "All time", "#0ea5e9")
    with a2:
        cr = int((alerts_df["severity"] == "CRITICAL").sum())
        kpi("CRITICAL", fmt_num(cr), "Immediate action", "#ef4444")
    with a3:
        hi = int((alerts_df["severity"] == "HIGH").sum())
        kpi("HIGH", fmt_num(hi), "Attention needed", "#f59e0b")
    with a4:
        kpi("SMS Sent", fmt_num(int(alerts_df["sms_sent"].sum())), "Dispatched to SOC", "#22c55e")
    with a5:
        unack = int((alerts_df["ack"] == 0).sum())
        kpi("Unacknowledged", fmt_num(unack), "Pending review", "#a855f7")

    st.write("")

    ch1, ch2 = st.columns(2)
    with ch1:
        sv = alerts_df["severity"].value_counts().reset_index()
        sv.columns = ["severity", "count"]
        fig = px.pie(
            sv,
            names="severity",
            values="count",
            hole=0.55,
            title="Alerts by Severity",
            color="severity",
            color_discrete_map={
                "CRITICAL": "#ef4444",
                "HIGH": "#f59e0b",
                "MEDIUM": "#0ea5e9",
                "LOW": "#94a3b8",
            },
        )
        fig.update_layout(height=340)
        _chart(fig, use_container_width=True)
    with ch2:
        tp = alerts_df["alert_type"].value_counts().reset_index()
        tp.columns = ["alert_type", "count"]
        fig = px.bar(
            tp,
            x="count",
            y="alert_type",
            orientation="h",
            title="Alerts by Type",
            color="count",
            color_continuous_scale="Reds",
        )
        fig.update_layout(height=340, coloraxis_showscale=False, xaxis_title="", yaxis_title="")
        _chart(fig, use_container_width=True)

    alerts_df = alerts_df.copy()
    alerts_df["ts"] = pd.to_datetime(alerts_df["timestamp"], errors="coerce")
    timeline = alerts_df.set_index("ts").resample("h").size().reset_index(name="count")
    if len(timeline):
        fig = px.bar(
            timeline,
            x="ts",
            y="count",
            title="Alert Timeline (hourly)",
            color="count",
            color_continuous_scale="OrRd",
        )
        fig.update_layout(
            height=300, coloraxis_showscale=False, xaxis_title="", yaxis_title="Alerts"
        )
        _chart(fig, use_container_width=True)

    st.markdown("#### 📋 Alert Log")
    st.dataframe(
        adf[
            [
                "alert_id",
                "timestamp",
                "severity",
                "alert_type",
                "msisdn",
                "description",
                "sms_sent",
                "sms_to",
                "ack",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        height=400,
    )
    csv_download(adf, "alerts_filtered.csv")

    st.divider()
    st.markdown("### 📲 SMS Delivery Log")
    if not sms_alerts_df.empty:
        sms_filtered = sms_alerts_df[sms_alerts_df["alert_id"].isin(adf["alert_id"])]
        st.dataframe(sms_filtered, use_container_width=True, hide_index=True, height=300)
        csv_download(sms_filtered, "sms_log.csv")

        rp = sms_alerts_df.groupby("recipient").size().reset_index(name="count")
        fig = px.bar(
            rp,
            x="recipient",
            y="count",
            title="SMS Dispatched per SOC Recipient",
            color="count",
            color_continuous_scale="Greens",
        )
        fig.update_layout(
            height=320, coloraxis_showscale=False, xaxis_title="Recipient MSISDN", yaxis_title="SMS"
        )
        _chart(fig, use_container_width=True)
    else:
        st.info("No SMS delivered yet.")

    st.divider()
    st.markdown("### 📱 SMS Preview (Latest 5)")
    for _, row in adf.head(5).iterrows():
        sev = row["severity"]
        color = {
            "CRITICAL": "#ef4444",
            "HIGH": "#f59e0b",
            "MEDIUM": "#0ea5e9",
            "LOW": "#94a3b8",
        }.get(sev, "#94a3b8")
        st.markdown(
            f"""
        <div style="border-left:4px solid {color};
                    background:#f8fafc; padding:12px 16px;
                    border-radius:10px; margin-bottom:10px;">
          <div style="font-size:12px;color:#64748b;">
            TO: <b>{row['sms_to']}</b> | {row['timestamp']}
          </div>
          <div style="font-size:14px;color:#0f172a;margin-top:6px;">
            {row['sms_body']}
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
