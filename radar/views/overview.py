"""Tab 0 — Radar Overview."""

import plotly.express as px
import streamlit as st

from radar._config import ORANGE
from radar.services.period import delta_pct
from radar.services.ui import (
    fmt,
    safe_chart,
    section,
    stat_card,
)


def render(data, filtered, ctx):
    cells_f = filtered["cells"]
    cdrs_f = filtered["cdrs"]
    subs_f = filtered["subs"]
    sig = ctx.get("sig", {})
    alerts_df = data["alerts"]
    compare_mode = ctx.get("compare_mode", False)
    prev_stats = ctx.get("prev_stats")
    curr_stats = ctx.get("curr_stats")

    section("Global Summary")
    if compare_mode and curr_stats:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            stat_card(
                "Total CDR",
                fmt(curr_stats["cdr"]),
                curr_stats["cdr"] - prev_stats["cdr"],
                delta_pct(curr_stats["cdr"], prev_stats["cdr"]),
                "Current period",
                True,
            )
        with c2:
            stat_card(
                "Data Volume",
                f"{curr_stats['bytes']/1e9:.2f} GB",
                (curr_stats["bytes"] - prev_stats["bytes"]) / 1e9,
                delta_pct(curr_stats["bytes"], prev_stats["bytes"]),
                "Current period",
                True,
            )
        with c3:
            stat_card(
                "Voice Calls",
                fmt(curr_stats["voice"]),
                curr_stats["voice"] - prev_stats["voice"],
                delta_pct(curr_stats["voice"], prev_stats["voice"]),
                "Current period",
                True,
            )
        with c4:
            stat_card(
                "SMS",
                fmt(curr_stats["sms"]),
                curr_stats["sms"] - prev_stats["sms"],
                delta_pct(curr_stats["sms"], prev_stats["sms"]),
                "Current period",
                True,
            )
    else:
        total_cdr = len(cdrs_f)
        total_bytes = cdrs_f["bytes"].sum() if len(cdrs_f) else 0
        voice_calls = int((cdrs_f["call_type"] == "voice").sum()) if len(cdrs_f) else 0
        voice_minutes = (
            cdrs_f.loc[cdrs_f["call_type"] == "voice", "duration_sec"].sum() / 60
            if len(cdrs_f)
            else 0
        )
        sms_count = int((cdrs_f["call_type"] == "sms").sum()) if len(cdrs_f) else 0
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            stat_card("Total CDR", fmt(total_cdr), sub="Records")
        with c2:
            stat_card("Data Volume", f"{total_bytes/1e9:.2f} GB", sub="Traffic")
        with c3:
            stat_card("Voice Calls", fmt(voice_calls), sub=f"{fmt(voice_minutes)} min")
        with c4:
            stat_card("SMS", fmt(sms_count), sub="Messages")

    st.write("")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ec = sig.get("encryption_coverage", {})
        gov = ec.get("Government", {}).get("coverage_pct", 0)
        stat_card("Gov Encryption", f"{gov:.1f}%", sub="Coverage")
    with c2:
        stat_card("Cell Sites", fmt(len(cells_f)), sub=f"of {len(data['cells']):,}")
    with c3:
        stat_card("Subscribers", fmt(len(subs_f)), sub="Active")
    with c4:
        cr = int((alerts_df["severity"] == "CRITICAL").sum()) if len(alerts_df) else 0
        stat_card("CRITICAL Alerts", fmt(cr), sub=f"of {len(alerts_df)} total")

    st.write("")
    section("Traffic Heat — City × Hour")
    if len(cdrs_f):
        pivot = cdrs_f.pivot_table(
            index="city", columns="hour", values="record_id", aggfunc="count"
        ).fillna(0)
        if not pivot.empty:
            fig = px.imshow(
                pivot,
                aspect="auto",
                color_continuous_scale=["#f8fafc", "#fbbf24", ORANGE, "#dc2626"],
                labels=dict(x="Hour of Day", y="City", color="Records"),
            )
            fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

    st.write("")
    section("Top 10 Busiest Cells")
    top_cells = None
    if len(cdrs_f):
        top_cells = (
            cdrs_f.groupby("cell_id")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .head(10)
        )
        top_cells = top_cells.merge(
            data["cells"][["cell_id", "tech", "city"]],
            on="cell_id",
            how="left",
        )
        fig = px.bar(
            top_cells,
            x="count",
            y="cell_id",
            orientation="h",
            color="tech",
            color_discrete_map={
                "2G": "#8888ff",
                "3G": "#38bdf8",
                "4G": "#22c55e",
                "5G": ORANGE,
                "6G": "#a855f7",
            },
            hover_data=["city"],
        )
        fig.update_layout(
            height=380,
            yaxis=dict(autorange="reversed"),
            xaxis_title="CDR Count",
            yaxis_title="",
            legend_title="Tech",
        )
        safe_chart(fig)
