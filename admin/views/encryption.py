"""Tab 6 — Encryption Management."""

import streamlit as st

from admin.services.audit import log_audit
from admin.services.db import db_df, db_exec, db_one
from telecom_common import CIPHER_SUITES, gen_key_id


def render():
    st.subheader("Encryption Management")
    df = db_df(
        """SELECT msisdn,line_class,cipher_suite,key_id,
            key_rotation_days,e2e_enabled,encryption_required
            FROM subscribers WHERE e2e_enabled=1"""
    )
    st.caption(f"{len(df)} encrypted subscribers")
    st.dataframe(df.head(500), use_container_width=True, hide_index=True, height=400)

    st.markdown("#### Rotate Keys")
    c1, c2 = st.columns(2)
    with c1:
        rc = st.multiselect(
            "Classes:",
            ["VIP", "Government", "Corporate", "Emergency", "Test"],
            default=["Government", "Emergency"],
            key="enc_rc",
        )
    with c2:
        nc = st.selectbox("New cipher", list(CIPHER_SUITES.keys()), key="enc_nc")
    if st.button("Rotate Now", type="primary"):
        if rc:
            ph = ",".join("?" * len(rc))
            rows = db_df(
                f"SELECT msisdn FROM subscribers WHERE line_class IN ({ph})",
                tuple(rc),
            )
            n = 0
            for _, r in rows.iterrows():
                db_exec(
                    "UPDATE subscribers SET key_id=?,cipher_suite=? " "WHERE msisdn=?",
                    (gen_key_id(r["msisdn"]), nc, r["msisdn"]),
                )
                n += 1
            log_audit("KEY_ROTATE", "encryption", f"{n}", f"cipher={nc}")
            st.success(f"Rotated {n}.")
            st.rerun()

    st.markdown("#### Single Subscriber Edit")
    msisdn = st.text_input("MSISDN", key="enc_msisdn_edit")
    if not msisdn:
        return
    row = db_one(
        """SELECT msisdn,cipher_suite,key_id,e2e_enabled,
            encryption_required,key_rotation_days
            FROM subscribers WHERE msisdn=?""",
        (msisdn,),
    )
    if not row:
        st.warning("Not found.")
        return
    st.write(
        dict(
            zip(
                ["msisdn", "cipher", "key_id", "e2e", "req", "rot"],
                row,
                strict=False,
            )
        )
    )
    cl = ["None"] + list(CIPHER_SUITES.keys())
    with st.form("enc_edit"):
        e2e = st.checkbox("E2E Enabled", bool(row[3]))
        er = st.checkbox("Encryption Required", bool(row[4]))
        cs = st.selectbox(
            "Cipher",
            cl,
            index=cl.index(row[1]) if row[1] in cl else 0,
        )
        rt = st.number_input("Rotation days", 0, 365, int(row[5]))
        nk = st.text_input("New Key ID (blank=keep)", "")
        if st.form_submit_button("Save", use_container_width=True):
            kid = nk.strip() or row[2]
            db_exec(
                """UPDATE subscribers SET e2e_enabled=?,
                    encryption_required=?,cipher_suite=?,
                    key_rotation_days=?,key_id=?
                    WHERE msisdn=?""",
                (int(e2e), int(er), cs, rt, kid, msisdn),
            )
            log_audit("ENC_UPDATE", "subscriber", msisdn, f"cipher={cs}")
            st.success("Saved.")
            st.rerun()
