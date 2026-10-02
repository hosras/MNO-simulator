"""Tab 8 — End-to-End Encryption."""

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.services.ui import fmt_num, kpi
from telecom_common import CIPHER_SUITES
from telecom_ui_common import chart as _chart
from telecom_ui_common import csv_download


def render(data, filtered):
    subs = filtered["subs"]
    sig = data["findings"].get("SIGINT", {})

    st.subheader("🔐 End-to-End Encryption (Special Lines)")

    if "e2e_enabled" not in subs.columns:
        st.warning("Encryption fields not found. Re-run the simulator.")
        return

    enc_subs = subs[subs["e2e_enabled"] == 1]
    cov = sig.get("encryption_coverage", {})
    fails = sig.get("encryption_failures", [])

    e1, e2, e3, e4 = st.columns(4)
    with e1:
        kpi("E2E-Enabled Lines", fmt_num(len(enc_subs)), "Encrypted subscribers", "#22c55e")
    with e2:
        kpi(
            "Mandatory Lines",
            fmt_num(int(subs["encryption_required"].sum())),
            "Gov / Emergency",
            "#ef4444",
        )
    with e3:
        kpi(
            "Cipher Suites",
            fmt_num(len(sig.get("cipher_usage", {}))),
            "Active algorithms",
            "#0ea5e9",
        )
    with e4:
        kpi("Encryption Failures", fmt_num(len(fails)), "Handshake errors", "#f59e0b")

    st.write("")

    c1, c2 = st.columns(2)
    with c1:
        if cov:
            cov_df = pd.DataFrame([{"line_class": k, **v} for k, v in cov.items()])
            fig = px.bar(
                cov_df,
                x="line_class",
                y="coverage_pct",
                title="Encryption Coverage by Line Class (%)",
                color="coverage_pct",
                color_continuous_scale="Greens",
                text="coverage_pct",
            )
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(
                height=350,
                coloraxis_showscale=False,
                yaxis_range=[0, 105],
                xaxis_title="",
                yaxis_title="Coverage %",
            )
            _chart(fig, use_container_width=True)

    with c2:
        cu = sig.get("cipher_usage", {})
        if cu:
            cu_df = pd.DataFrame(list(cu.items()), columns=["cipher", "count"])
            fig = px.pie(
                cu_df, names="cipher", values="count", hole=0.55, title="Cipher Suite Usage"
            )
            fig.update_layout(height=350)
            _chart(fig, use_container_width=True)

    st.markdown("#### 🔑 Cipher Suite Details")
    cipher_info = pd.DataFrame(
        [
            {"cipher_suite": k, "key_strength": v["strength"], "quantum_safe": v["quantum_safe"]}
            for k, v in CIPHER_SUITES.items()
        ]
    )
    st.dataframe(cipher_info, use_container_width=True, hide_index=True)
    csv_download(cipher_info, "cipher_suites.csv")

    st.markdown("#### 🔄 Key Distribution (Top 20)")
    ku = sig.get("key_usage", {})
    if ku:
        ku_df = pd.DataFrame(list(ku.items()), columns=["key_id", "usage"])
        st.dataframe(ku_df, use_container_width=True, hide_index=True, height=250)
        csv_download(ku_df, "key_usage.csv")

    st.markdown("#### ⚠️ Encryption Failures")
    if fails:
        df_f = pd.DataFrame(fails)
        fig = px.bar(
            df_f.groupby("line_class").size().reset_index(name="count"),
            x="line_class",
            y="count",
            title="Encryption Failures by Line Class",
            color="count",
            color_continuous_scale="Reds",
        )
        fig.update_layout(height=320, coloraxis_showscale=False, xaxis_title="", yaxis_title="")
        _chart(fig, use_container_width=True)
        st.dataframe(df_f, use_container_width=True, hide_index=True, height=250)
        csv_download(df_f, "encryption_failures.csv")
    else:
        st.success("No encryption failures detected.")

    st.markdown("#### 📋 E2E-Enabled Subscribers")
    if len(enc_subs):
        st.dataframe(
            enc_subs[
                ["msisdn", "imsi", "line_class", "cipher_suite", "key_id", "key_rotation_days"]
            ],
            use_container_width=True,
            hide_index=True,
            height=300,
        )
        csv_download(enc_subs, "e2e_subscribers.csv")
