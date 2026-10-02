"""Tab 0 — Admin Dashboard summary."""

import plotly.express as px
import streamlit as st

from admin.services.db import db_count, db_df


def render():
    st.subheader("Admin Dashboard")
    n_6g = int(db_df("SELECT COUNT(*) AS n FROM cells WHERE tech='6G'").iloc[0]["n"])
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Subscribers", f"{db_count('subscribers'):,}")
    with c2:
        st.metric("Cells", f"{db_count('cells'):,}")
    with c3:
        st.metric("6G Cells", f"{n_6g:,}")
    with c4:
        st.metric("Alerts", f"{db_count('alerts'):,}")
    with c5:
        st.metric("Audit Records", f"{db_count('audit_log'):,}")
    st.divider()
    st.markdown("### Recent Audit Activity")
    recent = db_df(
        "SELECT ts,user,action,entity,entity_id,details " "FROM audit_log ORDER BY id DESC LIMIT 20"
    )
    if not recent.empty:
        st.dataframe(recent, use_container_width=True, hide_index=True)
    st.markdown("### Subscribers by Line Class")
    lc = db_df(
        "SELECT line_class, COUNT(*) AS count FROM subscribers "
        "GROUP BY line_class ORDER BY count DESC"
    )
    if not lc.empty:
        fig = px.bar(lc, x="line_class", y="count", color="count", color_continuous_scale="Blues")
        fig.update_layout(
            height=340, coloraxis_showscale=False, xaxis_title="", yaxis_title="Subscribers"
        )
        st.plotly_chart(fig, use_container_width=True)
