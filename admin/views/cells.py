"""Tab 2 — Manage Cells."""

import streamlit as st

from admin.services.audit import log_audit
from admin.services.db import db_df, db_exec, db_one
from telecom_common import CITIES


def render():
    st.subheader("Manage Cells")
    act = st.radio(
        "Action",
        ["View", "Add", "Edit", "Delete"],
        horizontal=True,
        key="cell_act",
        label_visibility="collapsed",
    )
    if act == "View":
        _view()
    elif act == "Add":
        _add()
    elif act == "Edit":
        _edit()
    elif act == "Delete":
        _delete()


def _view():
    c1, c2 = st.columns(2)
    with c1:
        tf = st.multiselect(
            "Tech",
            ["2G", "3G", "4G", "5G", "6G"],
            default=["2G", "3G", "4G", "5G", "6G"],
            key="cell_tf",
        )
    with c2:
        lm = st.number_input("Limit", 50, 2000, 300, 50, key="cell_lim")
    sql = "SELECT * FROM cells"
    params = []
    if tf:
        sql += f" WHERE tech IN ({','.join('?'*len(tf))})"
        params += tf
    sql += f" LIMIT {int(lm)}"
    st.dataframe(db_df(sql, tuple(params)), use_container_width=True, hide_index=True, height=500)


def _add():
    with st.form("add_cell"):
        c1, c2, c3 = st.columns(3)
        with c1:
            cid = st.text_input("Cell ID", key="cell_add_id")
            nm = st.text_input("Name")
            tc = st.selectbox("Tech", ["2G", "3G", "4G", "5G", "6G"])
            ct = st.selectbox("City", [c[0] for c in CITIES])
        with c2:
            la = st.number_input("Latitude", 20.0, 40.0, 35.6892, 0.0001)
            lo = st.number_input("Longitude", 40.0, 65.0, 51.3890, 0.0001)
            bd = st.selectbox(
                "Band",
                [
                    "GSM-900",
                    "GSM-1800",
                    "UMTS-2100",
                    "UMTS-900",
                    "LTE-B3",
                    "LTE-B7",
                    "LTE-B20",
                    "LTE-B1",
                    "NR-n78",
                    "NR-n41",
                    "NR-n28",
                    "THz-140",
                    "THz-220",
                    "sub-THz-300",
                    "mmWave-28",
                ],
            )
        with c3:
            az = st.slider("Azimuth", 0, 359, 0, 30)
            tl = st.slider("Tilt", 0, 15, 4)
            tx = st.number_input("Tx Power", 10.0, 60.0, 40.0, 0.1)
            bh = st.number_input("Backhaul", 0.1, 100.0, 10.0, 0.1)
        if st.form_submit_button("Add", use_container_width=True):
            try:
                db_exec(
                    "INSERT INTO cells VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (cid, nm, tc, ct, la, lo, bd, az, tl, tx, bh),
                )
                log_audit("CREATE", "cell", cid, tc)
                st.success("Added.")
                st.rerun()
            except Exception as e:
                st.error(str(e))


def _edit():
    cid = st.text_input("Cell ID", key="cell_edit_id")
    if not cid:
        return
    row = db_one("SELECT * FROM cells WHERE cell_id=?", (cid,))
    if not row:
        st.warning("Not found.")
        return
    d = dict(
        zip(
            [
                "cell_id",
                "name",
                "tech",
                "city",
                "lat",
                "lon",
                "band",
                "azimuth",
                "tilt",
                "tx_dbm",
                "backhaul_gbps",
            ],
            row,
            strict=False,
        )
    )
    with st.form("edit_cell"):
        nm = st.text_input("Name", d["name"])
        az = st.slider("Azimuth", 0, 359, int(d["azimuth"]), 30)
        tl = st.slider("Tilt", 0, 15, int(d["tilt"]))
        tx = st.number_input("Tx Power", 10.0, 60.0, float(d["tx_dbm"]), 0.1)
        bh = st.number_input("Backhaul", 0.1, 100.0, float(d["backhaul_gbps"]), 0.1)
        if st.form_submit_button("Save", use_container_width=True):
            db_exec(
                """UPDATE cells SET name=?,azimuth=?,tilt=?,
                   tx_dbm=?,backhaul_gbps=? WHERE cell_id=?""",
                (nm, az, tl, tx, bh, cid),
            )
            log_audit("UPDATE", "cell", cid, "")
            st.success("Updated.")
            st.rerun()


def _delete():
    cid = st.text_input("Cell ID", key="cell_del_id")
    if cid and db_one("SELECT 1 FROM cells WHERE cell_id=?", (cid,)):
        if st.checkbox("Confirm", key="cell_del_c"):
            if st.button("Delete", type="primary"):
                db_exec("DELETE FROM cells WHERE cell_id=?", (cid,))
                log_audit("DELETE", "cell", cid, "")
                st.success("Deleted.")
                st.rerun()
