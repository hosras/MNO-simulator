# -*- coding: utf-8 -*-
"""Tab 1 — Manage Subscribers (CRUD)."""
import sqlite3

import streamlit as st

from telecom_common import (
    CITIES, LINE_CLASSES, PLANS, CIPHER_SUITES,
    gen_msisdn, gen_imsi, gen_imei, gen_key_id,
)
from admin.services.db import db_df, db_exec, db_one
from admin.services.audit import log_audit


def render():
    st.subheader("Manage Subscribers")
    action = st.radio("Action", ["View", "Add", "Edit", "Delete"],
                      horizontal=True, key="sub_act",
                      label_visibility="collapsed")

    if action == "View":
        _view()
    elif action == "Add":
        _add()
    elif action == "Edit":
        _edit()
    elif action == "Delete":
        _delete()


def _view():
    c1, c2, c3 = st.columns(3)
    with c1:
        search = st.text_input("Search (MSISDN/IMSI/IMEI)", key="sub_q")
    with c2:
        lc_f = st.multiselect("Line Class", LINE_CLASSES,
                              default=LINE_CLASSES, key="sub_lc")
    with c3:
        lim = st.number_input("Limit", 50, 10000, 500, 50, key="sub_lim")
    sql = "SELECT * FROM subscribers WHERE 1=1"
    params = []
    if search:
        sql += " AND (msisdn LIKE ? OR imsi LIKE ? OR imei LIKE ?)"
        p = f"%{search}%"
        params += [p, p, p]
    if lc_f:
        sql += f" AND line_class IN ({','.join('?'*len(lc_f))})"
        params += lc_f
    sql += f" LIMIT {int(lim)}"
    df = db_df(sql, tuple(params))
    st.caption(f"{len(df)} records")
    st.dataframe(df, use_container_width=True, hide_index=True, height=500)
    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        "subscribers.csv", "text/csv",
    )


def _add():
    with st.form("add_sub"):
        c1, c2, c3 = st.columns(3)
        with c1:
            msisdn = st.text_input("MSISDN", value=gen_msisdn())
            imsi = st.text_input("IMSI", value=gen_imsi())
            imei = st.text_input("IMEI", value=gen_imei())
            city = st.selectbox("City", [c[0] for c in CITIES])
        with c2:
            plan = st.selectbox("Plan", PLANS)
            line_class = st.selectbox("Line Class", LINE_CLASSES)
            kyc = st.number_input("KYC Age (days)", 0, 5000, 365)
            qos = st.slider("Priority QoS", 0, 9, 3)
        with c3:
            intl = st.checkbox("International Access")
            fb = st.checkbox("Filter Bypass")
            clir = st.checkbox("CLIR")
            cliro = st.checkbox("CLIR Override")
            li = st.checkbox("Lawful Intercept")
            dr = st.checkbox("Direct Routing")
            roa = st.checkbox("Roaming Enabled")
        st.markdown("##### Encryption")
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            enc_req = st.checkbox("Encryption Required")
            e2e = st.checkbox("E2E Enabled")
        with ec2:
            cipher = st.selectbox(
                "Cipher Suite", ["None"] + list(CIPHER_SUITES.keys())
            )
        with ec3:
            key_id_in = st.text_input("Key ID", value="")
            rot = st.number_input("Key Rotation (days)", 0, 365, 90)
        if st.form_submit_button("Add Subscriber", use_container_width=True):
            try:
                db_exec(
                    """INSERT INTO subscribers(
                        msisdn,imsi,imei,city,plan,kyc_age_days,
                        roaming_enabled,risk_score,line_class,
                        international_access,filter_bypass,clir_enabled,
                        clir_override,priority_qos,lawful_intercept,
                        direct_routing,whitelisted_asns,
                        encryption_required,cipher_suite,key_id,
                        key_rotation_days,e2e_enabled)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (msisdn, imsi, imei, city, plan, kyc, int(roa), 0.1,
                     line_class, int(intl), int(fb), int(clir),
                     int(cliro), qos, int(li), int(dr), "",
                     int(enc_req), cipher,
                     key_id_in or (gen_key_id(imsi) if e2e else ""),
                     rot, int(e2e)),
                )
                log_audit("CREATE", "subscriber", msisdn,
                          f"class={line_class}")
                st.success("Added.")
                st.rerun()
            except sqlite3.IntegrityError as e:
                st.error(f"Duplicate: {e}")
            except Exception as e:
                st.error(f"Error: {e}")


def _edit():
    msisdn = st.text_input("MSISDN to edit", key="sub_edit_m")
    if not msisdn:
        return
    row = db_one("SELECT * FROM subscribers WHERE msisdn=?", (msisdn,))
    if not row:
        st.warning("Not found.")
        return
    cols = [
        "msisdn", "imsi", "imei", "city", "plan",
        "kyc_age_days", "roaming_enabled", "risk_score",
        "line_class", "international_access", "filter_bypass",
        "clir_enabled", "clir_override", "priority_qos",
        "lawful_intercept", "direct_routing",
        "whitelisted_asns", "encryption_required",
        "cipher_suite", "key_id", "key_rotation_days",
        "e2e_enabled",
    ]
    d = dict(zip(cols, row))
    cl = [c[0] for c in CITIES]
    with st.form("edit_sub"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("MSISDN", d["msisdn"], disabled=True)
            st.text_input("IMSI", d["imsi"], disabled=True)
            imei_new = st.text_input("IMEI", d["imei"])
            city = st.selectbox(
                "City", cl,
                index=cl.index(d["city"]) if d["city"] in cl else 0,
            )
        with c2:
            plan = st.selectbox(
                "Plan", PLANS,
                index=PLANS.index(d["plan"]) if d["plan"] in PLANS else 0,
            )
            line_class = st.selectbox(
                "Line Class", LINE_CLASSES,
                index=LINE_CLASSES.index(d["line_class"])
                if d["line_class"] in LINE_CLASSES else 0,
            )
            qos = st.slider("Priority QoS", 0, 9, int(d["priority_qos"]))
        with c3:
            intl = st.checkbox("International", bool(d["international_access"]))
            fb = st.checkbox("Filter Bypass", bool(d["filter_bypass"]))
            clir = st.checkbox("CLIR", bool(d["clir_enabled"]))
            cliro = st.checkbox("CLIR Override", bool(d["clir_override"]))
            li = st.checkbox("Lawful Intercept", bool(d["lawful_intercept"]))
            dr = st.checkbox("Direct Routing", bool(d["direct_routing"]))
            roa = st.checkbox("Roaming", bool(d["roaming_enabled"]))
        cipher_l = ["None"] + list(CIPHER_SUITES.keys())
        cipher = st.selectbox(
            "Cipher Suite", cipher_l,
            index=cipher_l.index(d["cipher_suite"])
            if d["cipher_suite"] in cipher_l else 0,
        )
        if st.form_submit_button("Save", use_container_width=True):
            db_exec(
                """UPDATE subscribers SET
                    imei=?, city=?, plan=?, kyc_age_days=?,
                    roaming_enabled=?, line_class=?,
                    international_access=?, filter_bypass=?,
                    clir_enabled=?, clir_override=?,
                    priority_qos=?, lawful_intercept=?,
                    direct_routing=?, cipher_suite=?
                    WHERE msisdn=?""",
                (imei_new, city, plan, d["kyc_age_days"],
                 int(roa), line_class, int(intl), int(fb),
                 int(clir), int(cliro), qos, int(li),
                 int(dr), cipher, msisdn),
            )
            log_audit("UPDATE", "subscriber", msisdn, f"class={line_class}")
            st.success("Updated.")
            st.rerun()


def _delete():
    msisdn = st.text_input("MSISDN to delete", key="sub_del_m")
    if not msisdn:
        return
    row = db_one("SELECT * FROM subscribers WHERE msisdn=?", (msisdn,))
    if not row:
        st.warning("Not found.")
        return
    st.json(dict(zip(
        ["msisdn", "imsi", "imei", "city", "plan"], row[:5]
    )))
    if st.checkbox("Confirm", key="sub_del_c"):
        if st.button("Delete", type="primary"):
            db_exec("DELETE FROM subscribers WHERE msisdn=?", (msisdn,))
            log_audit("DELETE", "subscriber", msisdn, "")
            st.success("Deleted.")
            st.rerun()