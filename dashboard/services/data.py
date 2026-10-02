# -*- coding: utf-8 -*-
"""Data access — cached DB load + filter application."""
from datetime import timedelta

import pandas as pd

from dashboard._config import DB_PATH
from telecom_ui_common import db_mtime, load_data


def get_raw_data():
    """Load the full DB via the shared Streamlit-cached loader."""
    return load_data(DB_PATH, db_mtime(DB_PATH))


def apply_filters(data, sel_cities, sel_techs, date_range):
    """Apply sidebar filters. Returns dict with keys cells/cdrs/subs."""
    cells = data["cells"]
    cdrs = data["cdrs"]
    subs = data["subscribers"]

    mask_cells = cells["city"].isin(sel_cities) & cells["tech"].isin(sel_techs)
    cells_f = cells[mask_cells].copy()

    mask_cdr = cdrs["city"].isin(sel_cities) & cdrs["tech"].isin(sel_techs)
    if date_range and len(date_range) == 2:
        d1 = pd.to_datetime(date_range[0])
        d2 = pd.to_datetime(date_range[1]) + timedelta(days=1)
        mask_cdr &= (cdrs["ts"] >= d1) & (cdrs["ts"] < d2)
    cdrs_f = cdrs[mask_cdr].copy()

    subs_f = subs[subs["city"].isin(sel_cities)] if "city" in subs.columns else subs

    return {"cells": cells_f, "cdrs": cdrs_f, "subs": subs_f}


def render_sidebar_filters(cells, cdrs):
    """Render sidebar filter widgets. Returns (sel_cities, sel_techs, date_range)."""
    import streamlit as st

    all_cities = sorted(cells["city"].unique())
    sel_cities = st.multiselect("Cities", all_cities, default=all_cities)

    all_techs = sorted(cells["tech"].unique())
    sel_techs = st.multiselect("Technology", all_techs, default=all_techs)

    if len(cdrs):
        min_d = cdrs["ts"].min().date()
        max_d = cdrs["ts"].max().date()
        date_range = st.date_input("Date Range", (min_d, max_d))
    else:
        date_range = None

    return sel_cities, sel_techs, date_range