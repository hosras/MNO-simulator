"""Tab 1 — Network Topology & Core Nodes."""

import plotly.express as px
import streamlit as st

from telecom_ui_common import chart as _chart
from telecom_ui_common import csv_download


def render(data, filtered):
    cells = filtered["cells"]
    cores = data["cores"]
    st.subheader("Network Topology & Core Nodes")

    cc1, cc2 = st.columns(2)

    with cc1:
        st.markdown("#### 🗼 Cell Sites")
        st.dataframe(
            cells[
                [
                    "cell_id",
                    "name",
                    "tech",
                    "city",
                    "band",
                    "azimuth",
                    "tilt",
                    "tx_dbm",
                    "backhaul_gbps",
                ]
            ],
            use_container_width=True,
            height=380,
            hide_index=True,
        )
        csv_download(cells, "cells.csv")

    with cc2:
        st.markdown("#### 🧠 Core Nodes")
        st.dataframe(
            cores[["node_id", "name", "role", "tech", "city", "capacity_tps"]],
            use_container_width=True,
            height=380,
            hide_index=True,
        )
        csv_download(cores, "core_nodes.csv")

    st.markdown("#### 📡 Core Nodes by Role")
    if len(cores):
        role_count = cores["role"].value_counts().reset_index()
        role_count.columns = ["role", "count"]
        fig = px.bar(role_count, x="role", y="count", color="count", color_continuous_scale="Teal")
        fig.update_layout(height=320, coloraxis_showscale=False, xaxis_title="", yaxis_title="")
        _chart(fig, use_container_width=True)
