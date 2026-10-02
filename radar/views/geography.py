# -*- coding: utf-8 -*-
"""Tab 11 — Geographic Distribution."""
import streamlit as st
import plotly.express as px

from radar._config import ORANGE, BLUE
from radar.services.ui import section, safe_chart, csv_btn


def render(data, filtered, ctx):
    cells_f = filtered["cells"]
    cdrs_f = filtered["cdrs"]

    section("🗺️ Geographic Distribution")

    geo_c1, geo_c2, geo_c3, geo_c4 = st.columns(4)
    with geo_c1:
        geo_proj = st.selectbox(
            "Projection",
            ["natural earth", "mercator", "orthographic", "equirectangular"],
            key="radar_proj",
        )
    with geo_c2:
        geo_size = st.selectbox(
            "Marker size",
            ["None", "tx_dbm", "backhaul_gbps"], key="radar_marker_size",
        )
    with geo_c3:
        geo_style = st.radio(
            "Style", ["Scatter", "Density"],
            horizontal=True, key="radar_style",
        )
    with geo_c4:
        geo_zoom = st.slider("Zoom scale", 2.0, 8.0, 4.0, 0.5,
                             key="radar_zoom")

    if not len(cells_f):
        st.info("No cells match filter.")
        return

    c1, c2 = st.columns(2)
    with c1:
        section("Cell Sites by City")
        gc = cells_f.groupby("city").size().reset_index(name="Cells")
        gc = gc.sort_values("Cells", ascending=True)
        fig = px.bar(gc, x="Cells", y="city", orientation="h",
                     color="Cells",
                     color_continuous_scale=["#fff7ed", ORANGE])
        fig.update_layout(height=420, coloraxis_showscale=False,
                          xaxis_title="", yaxis_title="",
                          margin=dict(l=0, r=0, t=10, b=0))
        safe_chart(fig)
    with c2:
        section("Traffic by City")
        if len(cdrs_f):
            tc = cdrs_f.groupby("city").size().reset_index(name="Records")
            tc = tc.sort_values("Records", ascending=True)
            fig = px.bar(tc, x="Records", y="city", orientation="h",
                         color="Records",
                         color_continuous_scale=["#eff6ff", BLUE])
            fig.update_layout(height=420, coloraxis_showscale=False,
                              xaxis_title="", yaxis_title="",
                              margin=dict(l=0, r=0, t=10, b=0))
            safe_chart(fig)

    st.write("")
    section("Interactive Cell Map")

    if geo_style == "Scatter":
        size_arg = geo_size if geo_size != "None" else None
        fig = px.scatter_geo(
            cells_f, lat="lat", lon="lon", color="tech",
            size=size_arg if size_arg else None,
            size_max=15,
            color_discrete_map={"2G": "#8888ff", "3G": "#38bdf8",
                                "4G": "#22c55e", "5G": ORANGE, "6G": "#a855f7"},
            hover_name="name",
            hover_data={"city": True, "band": True, "tx_dbm": True,
                        "lat": False, "lon": False},
        )
        fig.update_geos(
            scope="world", showcountries=True, countrycolor="#cbd5e1",
            showland=True, landcolor="#f1f5f9",
            showocean=True, oceancolor="#e0f2fe",
            projection_type=geo_proj,
            center={"lat": 33.5, "lon": 53.5},
            projection_scale=geo_zoom,
        )
        fig.update_layout(height=520, legend_title="Tech",
                          margin=dict(l=0, r=0, t=10, b=0))
        safe_chart(fig)
    else:
        density = cells_f.copy()
        density["lat_r"] = (density["lat"] * 10).round() / 10
        density["lon_r"] = (density["lon"] * 10).round() / 10
        dens = (density.groupby(["lat_r", "lon_r"])
                .size().reset_index(name="count"))
        fig = px.density_mapbox(
            dens, lat="lat_r", lon="lon_r", z="count", radius=20,
            center=dict(lat=33.5, lon=53.5), zoom=geo_zoom,
            mapbox_style="open-street-map",
            color_continuous_scale=["#fff7ed", ORANGE, "#dc2626"],
        )
        fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0))
        safe_chart(fig)

    st.write("")
    csv_btn(cells_f[["cell_id", "name", "tech", "city", "lat", "lon", "band"]],
            "cells_geographic.csv")