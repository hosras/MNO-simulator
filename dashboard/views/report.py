"""Tab 11 — Management Report."""

import os

import streamlit as st

from dashboard._config import DB_PATH


def render(data, filtered):
    st.subheader("📄 Management Report")

    sig = data["findings"].get("SIGINT", {})
    osi = data["findings"].get("OSINT", {})

    report_path = os.path.join(os.path.dirname(DB_PATH), "report.txt")
    if os.path.exists(report_path):
        with open(report_path, encoding="utf-8") as f:
            report_text = f.read()
        st.text_area("Report Content (report.txt)", report_text, height=600)
        st.download_button(
            "⬇️ Download Text Report", report_text.encode("utf-8"), "report.txt", "text/plain"
        )
    else:
        st.info("report.txt not found. Please run the simulator.")

    st.divider()
    st.markdown("#### 📦 SIGINT Findings (JSON Summary)")
    st.json(sig, expanded=False)

    st.markdown("#### 📦 OSINT Findings (JSON Summary)")
    st.json(osi, expanded=False)
