"""Tab 8 — Audit Log."""

from datetime import datetime, timedelta

import streamlit as st

from admin.services.audit import log_audit
from admin.services.db import db_df, db_exec


def render():
    st.subheader("Audit Log")
    c1, c2, c3 = st.columns(3)
    with c1:
        aa = db_df("SELECT DISTINCT action FROM audit_log")["action"].tolist()
        af = st.multiselect("Action", sorted(aa), default=sorted(aa), key="au_a")
    with c2:
        ee = db_df("SELECT DISTINCT entity FROM audit_log")["entity"].tolist()
        ef = st.multiselect("Entity", sorted(ee), default=sorted(ee), key="au_e")
    with c3:
        lm = st.number_input("Limit", 50, 5000, 500, 50, key="au_l")

    sql = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if af:
        sql += f" AND action IN ({','.join('?'*len(af))})"
        params += af
    if ef:
        sql += f" AND entity IN ({','.join('?'*len(ef))})"
        params += ef
    sql += f" ORDER BY id DESC LIMIT {int(lm)}"
    df = db_df(sql, tuple(params))
    st.caption(f"{len(df)} records")
    st.dataframe(df, use_container_width=True, hide_index=True, height=500)
    st.download_button(
        "CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        "audit_log.csv",
        "text/csv",
    )
    st.divider()
    if st.button("Clear Audit Log (>30 days)"):
        cut = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        db_exec("DELETE FROM audit_log WHERE ts < ?", (cut,))
        log_audit("CLEAR", "audit_log", ">30d", "")
        st.success("Cleared.")
        st.rerun()
