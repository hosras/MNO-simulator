"""Tab 5 — Special Lines Management."""

import streamlit as st

from admin.services.audit import log_audit
from admin.services.db import db_df, db_exec, db_one
from telecom_common import LINE_CLASSES, db_chunked_in_update


def render():
    st.subheader("Special Lines Management")
    c1, c2 = st.columns(2)
    with c1:
        lc_s = st.multiselect(
            "Line Class",
            ["VIP", "Government", "Corporate", "Emergency", "Test"],
            default=["VIP", "Government", "Corporate", "Emergency", "Test"],
            key="sl_lc",
        )
    with c2:
        ob = st.checkbox("Only filter-bypass", key="sl_ob")
        oc = st.checkbox("Only CLIR", key="sl_oc")

    sql = "SELECT * FROM subscribers WHERE line_class != 'Normal'"
    params = []
    if lc_s:
        sql += f" AND line_class IN ({','.join('?'*len(lc_s))})"
        params += lc_s
    if ob:
        sql += " AND filter_bypass=1"
    if oc:
        sql += " AND clir_enabled=1"
    df = db_df(sql, tuple(params))
    st.caption(f"{len(df)} special subscribers")
    st.dataframe(df, use_container_width=True, hide_index=True, height=400)

    st.markdown("#### Bulk Update")
    newc = st.selectbox(
        "Change ALL to:",
        ["VIP", "Government", "Corporate", "Emergency", "Test", "Normal"],
    )
    if st.checkbox("I understand", key="sl_blk_c"):
        if st.button("Apply"):
            if len(df) > 0:
                n = db_chunked_in_update(
                    "subscribers",
                    "msisdn",
                    "line_class=?",
                    [newc],
                    df["msisdn"].tolist(),
                )
                log_audit("BULK_UPDATE", "subscriber", f"{n}", f"class={newc}")
                st.success(f"Updated {n}.")
                st.rerun()

    st.markdown("#### Single Toggle")
    msisdn = st.text_input("MSISDN", key="sl_msisdn_toggle")
    if not msisdn:
        return
    row = db_one(
        """SELECT msisdn,line_class,international_access,
            filter_bypass,clir_enabled,clir_override,priority_qos,
            lawful_intercept,direct_routing
            FROM subscribers WHERE msisdn=?""",
        (msisdn,),
    )
    if not row:
        st.warning("Not found.")
        return
    st.write(
        dict(
            zip(
                ["msisdn", "class", "intl", "fb", "clir", "cliro", "qos", "li", "dr"],
                row,
                strict=False,
            )
        )
    )
    with st.form("toggle_sl"):
        p1, p2, p3 = st.columns(3)
        with p1:
            nlc = st.selectbox(
                "Line Class",
                LINE_CLASSES,
                index=LINE_CLASSES.index(row[1]) if row[1] in LINE_CLASSES else 0,
            )
            intl = st.checkbox("International", bool(row[2]))
            fb = st.checkbox("Filter Bypass", bool(row[3]))
        with p2:
            clir = st.checkbox("CLIR", bool(row[4]))
            cliro = st.checkbox("CLIR Override", bool(row[5]))
            qos = st.slider("QoS", 0, 9, int(row[6]))
        with p3:
            li = st.checkbox("Lawful Intercept", bool(row[7]))
            dr = st.checkbox("Direct Routing", bool(row[8]))
        if st.form_submit_button("Save", use_container_width=True):
            db_exec(
                """UPDATE subscribers SET line_class=?,
                    international_access=?,filter_bypass=?,
                    clir_enabled=?,clir_override=?,priority_qos=?,
                    lawful_intercept=?,direct_routing=?
                    WHERE msisdn=?""",
                (nlc, int(intl), int(fb), int(clir), int(cliro), qos, int(li), int(dr), msisdn),
            )
            log_audit("PERM_UPDATE", "subscriber", msisdn, f"class={nlc}")
            st.success("Saved.")
            st.rerun()
