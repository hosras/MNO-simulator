"""Tab 0 — Network Overview (map + tech share + cells per city)."""

import plotly.express as px
import streamlit as st

from dashboard._config import TECH_COLORS
from telecom_ui_common import chart as _chart


def render(data, filtered):
    cells = filtered["cells"]
    st.subheader("Network Overview")

    c1, c2 = st.columns([2, 1])

    with c1:
        if len(cells):
            fig = px.scatter_geo(
                cells,
                lat="lat",
                lon="lon",
                color="tech",
                hover_name="name",
                hover_data={
                    "cell_id": True,
                    "band": True,
                    "tx_dbm": True,
                    "lat": False,
                    "lon": False,
                },
                color_discrete_map=TECH_COLORS,
                title="Cell Sites Distribution Map",
            )
            fig.update_geos(
                scope="world",
                showcountries=True,
                countrycolor="#64748b",
                showland=True,
                landcolor="#f1f5f9",
                showocean=True,
                oceancolor="#e0f2fe",
                projection_type="natural earth",
                center={"lat": 33.5, "lon": 53.5},
                projection_scale=3.8,
            )
            fig.update_layout(
                height=460, margin=dict(l=0, r=0, t=40, b=0), legend_title_text="Technology"
            )
            _chart(fig, use_container_width=True)
        else:
            st.info("No cells match the current filter.")

    with c2:
        if len(cells):
            tech_count = cells["tech"].value_counts().reset_index()
            tech_count.columns = ["tech", "count"]
            fig = px.pie(
                tech_count,
                names="tech",
                values="count",
                hole=0.55,
                title="Technology Share",
                color="tech",
                color_discrete_map=TECH_COLORS,
            )
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
            _chart(fig, use_container_width=True)

            city_count = cells["city"].value_counts().head(8).reset_index()
            city_count.columns = ["city", "count"]
            fig = px.bar(
                city_count,
                x="count",
                y="city",
                orientation="h",
                title="Cell Sites per City",
                color="count",
                color_continuous_scale="Blues",
            )
            fig.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=40, b=0),
                yaxis_title="",
                xaxis_title="",
                coloraxis_showscale=False,
            )
            _chart(fig, use_container_width=True)
