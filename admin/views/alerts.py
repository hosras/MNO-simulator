"""Tab 4 — Manage Alerts."""

import random
from datetime import datetime

import streamlit as st

from admin.services.audit import log_audit
from admin.services.db import db_df, db_exec


def render():
    st.subheader("Manage Alerts")
    c1, c2, c3 = st.columns(3)
    with c1:
        sv = st.multiselect(
            "Severity",
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            default=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            key="al_sv",
        )
    with c2:
        ak = st.selectbox(
            "ACK Status",
            ["All", "Unacknowledged", "Acknowledged"],
            key="al_ak",
        )
    with c3:
        lm = st.number_input("Limit", 10, 1000, 100, 10, key="al_lm")

    sql = "SELECT * FROM alerts WHERE 1=1"
    params = []
    if sv:
        sql += f" AND severity IN ({','.join('?'*len(sv))})"
        params += sv
    if ak == "Unacknowledged":
        sql += " AND ack=0"
    elif ak == "Acknowledged":
        sql += " AND ack=1"
    sql += f" ORDER BY timestamp DESC LIMIT {int(lm)}"
    df = db_df(sql, tuple(params))
    st.caption(f"{len(df)} alerts")
    st.dataframe(
        df[["alert_id", "timestamp", "severity", "alert_type", "msisdn", "description", "ack"]],
        use_container_width=True,
        hide_index=True,
        height=400,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("ACK All", use_container_width=True):
            db_exec("UPDATE alerts SET ack=1 WHERE ack=0")
            log_audit("ACK_ALL", "alert", "-", "")
            st.success("ACKed.")
            st.rerun()
    with c2:
        if st.button("Un-ACK All", use_container_width=True):
            db_exec("UPDATE alerts SET ack=0")
            log_audit("UNACK_ALL", "alert", "-", "")
            st.success("Un-ACKed.")
            st.rerun()
    with c3:
        if st.button("Delete ACKed", use_container_width=True):
            db_exec("DELETE FROM alerts WHERE ack=1")
            log_audit("DELETE_ACKED", "alert", "-", "")
            st.success("Deleted.")
            st.rerun()

    st.markdown("#### Add Manual Alert")
    with st.form("add_alert"):
        c1, c2, c3 = st.columns(3)
        with c1:
            sv2 = st.selectbox("Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
            at = st.text_input("Alert Type", "MANUAL")
        with c2:
            ms2 = st.text_input("Related MSISDN", "-")
            snd = st.checkbox("Send SMS to SOC", value=True)
        with c3:
            ds = st.text_area("Description", height=68)
        if st.form_submit_button("Create Alert", use_container_width=True):
            nid = f"ALT-{datetime.now():%Y%m%d}-MAN" f"{random.randint(1000, 9999)}"
            to = random.choice(["989120000001", "989120000002", "989120000003"])
            db_exec(
                """INSERT INTO alerts(alert_id,timestamp,severity,
                    alert_type,msisdn,description,extra,sms_sent,sms_to,
                    sms_body,ack) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    nid,
                    f"{datetime.now():%Y-%m-%d %H:%M:%S}",
                    sv2,
                    at,
                    ms2,
                    ds,
                    "{}",
                    int(snd),
                    to if snd else "",
                    f"[{sv2}] {at} | {ds[:80]}" if snd else "",
                    0,
                ),
            )
            log_audit("CREATE", "alert", nid, at)
            st.success(f"Created {nid}.")
            st.rerun()
