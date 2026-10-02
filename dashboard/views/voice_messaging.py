"""Tab 4 — Voice Bearers & Messaging (VoLTE/VoWiFi/VoNR/CSFB + MMS + RCS)."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.services.ui import fmt_num, kpi
from telecom_ui_common import chart as _chart
from telecom_ui_common import csv_download


def render(data, filtered):
    cdrs = filtered["cdrs"]
    sig = data["findings"].get("SIGINT", {})

    st.subheader("📞 Voice Bearers & Messaging (VoLTE / VoWiFi / VoNR / MMS / RCS)")

    voice_df = cdrs[cdrs["call_type"] == "voice"]
    mms_df = cdrs[cdrs["call_type"] == "mms"]
    rcs_df = cdrs[cdrs["call_type"] == "rcs"]

    if not len(voice_df) and not len(mms_df) and not len(rcs_df):
        st.info("No voice or messaging records match the current filter.")
        return

    # --- KPIs ---
    v1, v2, v3, v4, v5 = st.columns(5)
    with v1:
        kpi("Voice Calls", fmt_num(len(voice_df)), "Total", "#60a5fa")
    with v2:
        volte = int((voice_df["voice_bearer"] == "VoLTE").sum()) if len(voice_df) else 0
        kpi("VoLTE Calls", fmt_num(volte), "Voice over LTE", "#22c55e")
    with v3:
        vonr = int((voice_df["voice_bearer"] == "VoNR").sum()) if len(voice_df) else 0
        kpi("VoNR Calls", fmt_num(vonr), "Voice over NR (5G)", "#ef4444")
    with v4:
        kpi("MMS", fmt_num(len(mms_df)), "Multimedia messages", "#8b5cf6")
    with v5:
        kpi("RCS", fmt_num(len(rcs_df)), "Rich communication", "#0ea5e9")

    st.write("")

    # ================= VOICE =================
    st.markdown("### 📞 Voice Bearer Analysis")
    if len(voice_df):
        vb = voice_df["voice_bearer"].value_counts().reset_index()
        vb.columns = ["bearer", "count"]

        vc1, vc2 = st.columns(2)
        with vc1:
            fig = px.pie(
                vb,
                names="bearer",
                values="count",
                hole=0.55,
                title="Voice Bearer Mix",
                color="bearer",
                color_discrete_map={
                    "VoLTE": "#22c55e",
                    "VoNR": "#ef4444",
                    "Vo6G": "#a855f7",
                    "VoWiFi": "#0ea5e9",
                    "CSFB": "#94a3b8",
                },
            )
            fig.update_layout(height=360)
            _chart(fig, use_container_width=True)

        with vc2:
            codec = voice_df["voice_codec"].value_counts().reset_index()
            codec.columns = ["codec", "count"]
            fig = px.bar(
                codec,
                x="codec",
                y="count",
                title="Voice Codec Distribution",
                color="count",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(
                height=360, coloraxis_showscale=False, xaxis_title="", yaxis_title="Calls"
            )
            _chart(fig, use_container_width=True)

        st.markdown("#### 📊 QCI Distribution")
        qci = voice_df["voice_qci"].value_counts().sort_index().reset_index()
        qci.columns = ["qci", "count"]
        fig = px.bar(
            qci,
            x="qci",
            y="count",
            title="Voice QCI Distribution (QCI=1 for VoLTE/VoNR/VoWiFi, 0=CSFB)",
            color="count",
            color_continuous_scale="Turbo",
        )
        fig.update_layout(
            height=320,
            coloraxis_showscale=False,
            xaxis=dict(dtick=1),
            xaxis_title="QCI",
            yaxis_title="Calls",
        )
        _chart(fig, use_container_width=True)

        st.markdown("#### 📊 Voice Bearer Distribution by Technology")
        if "tech" in voice_df.columns:
            pivot = voice_df.pivot_table(
                index="tech", columns="voice_bearer", values="record_id", aggfunc="count"
            ).fillna(0)
            if not pivot.empty:
                fig = px.imshow(
                    pivot,
                    aspect="auto",
                    color_continuous_scale="Greens",
                    labels=dict(x="Bearer", y="Technology", color="Calls"),
                )
                fig.update_layout(height=360)
                _chart(fig, use_container_width=True)

        st.markdown("#### ⚠️ VoLTE Fallback (4G/5G cells using CSFB)")
        fb = sig.get("volte_fallback", [])
        if fb:
            df_fb = pd.DataFrame(fb)
            by_cell = df_fb.groupby("cell_id").size().reset_index(name="count")
            by_cell = by_cell.sort_values("count", ascending=False).head(15)
            fig = px.bar(
                by_cell,
                x="count",
                y="cell_id",
                orientation="h",
                title="Top Cells with VoLTE Fallback to CSFB",
                color="count",
                color_continuous_scale="Reds",
            )
            fig.update_layout(height=360, coloraxis_showscale=False, xaxis_title="", yaxis_title="")
            _chart(fig, use_container_width=True)
            st.dataframe(df_fb.head(100), use_container_width=True, hide_index=True, height=250)
            csv_download(df_fb, "volte_fallback.csv")
        else:
            st.success("No VoLTE fallback detected.")

    st.divider()

    # ================= MMS =================
    st.markdown("### 📸 MMS Analysis")
    if len(mms_df):
        m1, m2 = st.columns(2)
        with m1:
            cts = mms_df["mms_content_type"].value_counts().reset_index()
            cts.columns = ["content", "count"]
            fig = px.pie(
                cts, names="content", values="count", hole=0.55, title="MMS by Content Type"
            )
            fig.update_layout(height=360)
            _chart(fig, use_container_width=True)
        with m2:
            deliv = mms_df["mms_delivery"].value_counts().reset_index()
            deliv.columns = ["status", "count"]
            fig = px.bar(
                deliv,
                x="status",
                y="count",
                title="MMS Delivery Status",
                color="status",
                color_discrete_map={
                    "DELIVERED": "#22c55e",
                    "EXPIRED": "#f59e0b",
                    "REJECTED": "#ef4444",
                    "PENDING": "#94a3b8",
                },
            )
            fig.update_layout(height=360, showlegend=False, xaxis_title="", yaxis_title="")
            _chart(fig, use_container_width=True)

        fig = px.histogram(
            mms_df,
            x="mms_size_bytes",
            nbins=50,
            title="MMS Size Distribution (bytes)",
            color_discrete_sequence=["#8b5cf6"],
        )
        fig.update_layout(height=340, xaxis_title="Size (bytes)", yaxis_title="Count")
        _chart(fig, use_container_width=True)

        total_mb = mms_df["mms_size_bytes"].sum() / 1e6
        st.markdown(
            f"**Total MMS volume:** `{total_mb:,.2f} MB` " f"across `{len(mms_df):,}` messages"
        )

        st.markdown("#### ⚠️ Large MMS from Normal Lines (possible abuse)")
        lm = sig.get("mms_large_suspects", [])
        if lm:
            df_lm = pd.DataFrame(lm)
            st.dataframe(df_lm, use_container_width=True, hide_index=True, height=250)
            csv_download(df_lm, "mms_large_suspects.csv")
        else:
            st.success("No large MMS abuse detected.")

        st.dataframe(mms_df.head(300), use_container_width=True, hide_index=True, height=250)
        csv_download(mms_df, "mms_records.csv")
    else:
        st.info("No MMS records match the current filter.")

    st.divider()

    # ================= RCS =================
    st.markdown("### 💬 RCS Analysis")
    if len(rcs_df):
        r1, r2 = st.columns([1, 2])
        with r1:
            rt = rcs_df["rcs_type"].value_counts().reset_index()
            rt.columns = ["rcs_type", "count"]
            fig = px.pie(rt, names="rcs_type", values="count", hole=0.5, title="RCS by Type")
            fig.update_layout(height=340)
            _chart(fig, use_container_width=True)
        with r2:
            fig = px.histogram(
                rcs_df,
                x="bytes",
                nbins=50,
                title="RCS Message Size Distribution",
                color_discrete_sequence=["#0ea5e9"],
            )
            fig.update_layout(height=340, xaxis_title="Bytes", yaxis_title="Count")
            _chart(fig, use_container_width=True)

        st.dataframe(rcs_df.head(300), use_container_width=True, hide_index=True, height=250)
        csv_download(rcs_df, "rcs_records.csv")
    else:
        st.info("No RCS records match the current filter.")

    st.divider()

    # ================= COMBINED CDR =================
    st.markdown("### 📋 Combined Voice + Messaging CDR Sample")
    vm = cdrs[cdrs["call_type"].isin(["voice", "sms", "mms", "rcs"])].copy()
    cols_show = [
        "record_id",
        "timestamp",
        "msisdn",
        "call_type",
        "duration_sec",
        "bytes",
        "voice_bearer",
        "voice_codec",
        "mms_content_type",
        "mms_delivery",
        "rcs_type",
        "cell_id",
        "tech",
        "city",
    ]
    cols_show = [c for c in cols_show if c in vm.columns]
    st.dataframe(vm[cols_show].head(500), use_container_width=True, hide_index=True, height=400)
    csv_download(vm, "voice_messaging_cdr.csv")
