"""Tab 1 — Period Comparison."""

import pandas as pd
import plotly.express as px
import streamlit as st

from radar._config import GRAY, ORANGE
from radar.services.pdf import build_pdf
from radar.services.period import delta_pct
from radar.services.ui import (
    csv_btn,
    dl_button,
    fmt,
    safe_chart,
    section,
    stat_card,
)


def render(data, filtered, ctx):
    compare_mode = ctx.get("compare_mode", False)
    prev_df = ctx.get("prev_df")
    curr_df = ctx.get("curr_df")
    prev_stats = ctx.get("prev_stats")
    curr_stats = ctx.get("curr_stats")

    section("⚖️ Period Comparison")
    if not compare_mode:
        st.info("Enable **Period Comparison** in the sidebar to see this tab.")
        return
    if prev_df is None or curr_df is None:
        st.info("No data available.")
        return

    prev_range = (
        f"{prev_df['ts'].min().strftime('%Y-%m-%d')} → "
        f"{prev_df['ts'].max().strftime('%Y-%m-%d')}"
    )
    curr_range = (
        f"{curr_df['ts'].min().strftime('%Y-%m-%d')} → "
        f"{curr_df['ts'].max().strftime('%Y-%m-%d')}"
    )
    st.markdown(
        f"""
    <span class="period-badge period-previous">PREVIOUS: {prev_range}</span>
    <span class="period-badge period-current">CURRENT: {curr_range}</span>
    """,
        unsafe_allow_html=True,
    )
    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card(
            "Total CDR",
            fmt(curr_stats["cdr"]),
            curr_stats["cdr"] - prev_stats["cdr"],
            delta_pct(curr_stats["cdr"], prev_stats["cdr"]),
            "Current vs prev",
            True,
        )
    with c2:
        stat_card(
            "Data Volume",
            f"{curr_stats['bytes']/1e9:.2f} GB",
            (curr_stats["bytes"] - prev_stats["bytes"]) / 1e9,
            delta_pct(curr_stats["bytes"], prev_stats["bytes"]),
            "Current vs prev",
            True,
        )
    with c3:
        stat_card(
            "Voice Calls",
            fmt(curr_stats["voice"]),
            curr_stats["voice"] - prev_stats["voice"],
            delta_pct(curr_stats["voice"], prev_stats["voice"]),
            "Current vs prev",
            True,
        )
    with c4:
        stat_card(
            "Talk Minutes",
            fmt(curr_stats["minutes"]),
            curr_stats["minutes"] - prev_stats["minutes"],
            delta_pct(curr_stats["minutes"], prev_stats["minutes"]),
            "Current vs prev",
            True,
        )

    st.write("")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card(
            "SMS",
            fmt(curr_stats["sms"]),
            curr_stats["sms"] - prev_stats["sms"],
            delta_pct(curr_stats["sms"], prev_stats["sms"]),
            "Current vs prev",
            True,
        )
    with c2:
        stat_card(
            "MMS",
            fmt(curr_stats["mms"]),
            curr_stats["mms"] - prev_stats["mms"],
            delta_pct(curr_stats["mms"], prev_stats["mms"]),
            "Current vs prev",
            True,
        )
    with c3:
        stat_card(
            "Data Sessions",
            fmt(curr_stats["data"]),
            curr_stats["data"] - prev_stats["data"],
            delta_pct(curr_stats["data"], prev_stats["data"]),
            "Current vs prev",
            True,
        )
    with c4:
        stat_card(
            "RCS",
            fmt(curr_stats["rcs"]),
            curr_stats["rcs"] - prev_stats["rcs"],
            delta_pct(curr_stats["rcs"], prev_stats["rcs"]),
            "Current vs prev",
            True,
        )

    st.write("")
    section("Side-by-Side Comparison")

    comp_df = pd.DataFrame(
        {
            "Metric": [
                "CDR",
                "Data (GB)",
                "Voice",
                "Talk (min)",
                "SMS",
                "MMS",
                "Data Sessions",
                "RCS",
            ],
            "Previous": [
                prev_stats["cdr"],
                round(prev_stats["bytes"] / 1e9, 2),
                prev_stats["voice"],
                round(prev_stats["minutes"]),
                prev_stats["sms"],
                prev_stats["mms"],
                prev_stats["data"],
                prev_stats["rcs"],
            ],
            "Current": [
                curr_stats["cdr"],
                round(curr_stats["bytes"] / 1e9, 2),
                curr_stats["voice"],
                round(curr_stats["minutes"]),
                curr_stats["sms"],
                curr_stats["mms"],
                curr_stats["data"],
                curr_stats["rcs"],
            ],
        }
    )
    comp_df["Delta"] = comp_df["Current"] - comp_df["Previous"]
    comp_df["Δ%"] = comp_df.apply(
        lambda r: (r["Delta"] / r["Previous"] * 100) if r["Previous"] else 0,
        axis=1,
    ).round(1)
    st.dataframe(comp_df, use_container_width=True, hide_index=True)
    csv_btn(comp_df, "period_comparison.csv")

    st.write("")
    section("Comparison Chart")
    long_df = comp_df.melt(
        id_vars="Metric", value_vars=["Previous", "Current"], var_name="Period", value_name="Value"
    )
    fig = px.bar(
        long_df,
        x="Metric",
        y="Value",
        color="Period",
        barmode="group",
        color_discrete_map={"Previous": GRAY, "Current": ORANGE},
    )
    fig.update_layout(
        height=400,
        xaxis_title="",
        yaxis_title="",
        legend_title="",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    safe_chart(fig)

    st.write("")
    if st.button("📄 Export Period Comparison PDF", key="pdf_compare"):
        sections = [
            {
                "heading": "Period Comparison",
                "text": f"Previous: {prev_range} | Current: {curr_range}",
            },
            {"heading": "Metrics", "table": comp_df},
        ]
        pdf = build_pdf("TELECOM Radar — Period Comparison", sections)
        if pdf is None:
            st.caption("⚠️ Install `reportlab` to enable PDF export.")
        else:
            dl_button("📄 Export PDF", pdf, "period_comparison.pdf", "application/pdf")
