"""Tab 3 — Manage Core Nodes."""

import streamlit as st

from admin.services.audit import log_audit
from admin.services.db import db_df, db_exec, db_one
from telecom_common import CITIES

CORE_ROLES = [
    "MSC",
    "BSC",
    "RNC",
    "MME",
    "SGW",
    "PGW",
    "HSS",
    "PCRF",
    "AMF",
    "SMF",
    "UPF",
    "IMS",
    "MMSC",
    "RCS-AS",
    "NWDAF",
    "RIS-C",
    "ISAC",
    "AI-RAN",
]


def render():
    st.subheader("Manage Core Nodes")
    act = st.radio(
        "Action",
        ["View", "Add", "Edit", "Delete"],
        horizontal=True,
        key="core_act",
        label_visibility="collapsed",
    )
    if act == "View":
        st.dataframe(
            db_df("SELECT * FROM cores ORDER BY role"),
            use_container_width=True,
            hide_index=True,
            height=500,
        )
    elif act == "Add":
        _add()
    elif act == "Edit":
        _edit()
    elif act == "Delete":
        _delete()


def _add():
    with st.form("add_core"):
        c1, c2 = st.columns(2)
        with c1:
            nid = st.text_input("Node ID", key="core_add_id")
            nm = st.text_input("Name")
            rl = st.selectbox("Role", CORE_ROLES)
        with c2:
            tc = st.text_input("Tech", "4G/5G")
            ct = st.selectbox("City", [c[0] for c in CITIES])
            cp = st.number_input("Capacity (tps)", 1000, 1_000_000, 100_000, 1000)
        if st.form_submit_button("Add", use_container_width=True):
            try:
                db_exec("INSERT INTO cores VALUES(?,?,?,?,?,?)", (nid, nm, rl, tc, ct, cp))
                log_audit("CREATE", "core", nid, rl)
                st.success("Added.")
                st.rerun()
            except Exception as e:
                st.error(str(e))


def _edit():
    nid = st.text_input("Node ID", key="core_edit_id")
    if not nid:
        return
    row = db_one("SELECT * FROM cores WHERE node_id=?", (nid,))
    if not row:
        st.warning("Not found.")
        return
    d = dict(
        zip(
            ["node_id", "name", "role", "tech", "city", "capacity_tps"],
            row,
            strict=False,
        )
    )
    with st.form("edit_core"):
        nm = st.text_input("Name", d["name"])
        cp = st.number_input("Capacity", 1000, 1_000_000, int(d["capacity_tps"]), 1000)
        if st.form_submit_button("Save", use_container_width=True):
            db_exec(
                "UPDATE cores SET name=?,capacity_tps=? WHERE node_id=?",
                (nm, cp, nid),
            )
            log_audit("UPDATE", "core", nid, "")
            st.success("Updated.")
            st.rerun()


def _delete():
    nid = st.text_input("Node ID", key="core_del_id")
    if nid and db_one("SELECT 1 FROM cores WHERE node_id=?", (nid,)):
        if st.checkbox("Confirm", key="core_del_c"):
            if st.button("Delete", type="primary"):
                db_exec("DELETE FROM cores WHERE node_id=?", (nid,))
                log_audit("DELETE", "core", nid, "")
                st.success("Deleted.")
                st.rerun()
