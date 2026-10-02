"""Admin panel entry point — login flow + tabs.

All Streamlit rendering happens inside main(); nothing at import time.
"""

import os
from datetime import datetime

import streamlit as st

from admin._config import LOGIN_MAX_FAILS, LOGIN_WINDOW_MIN
from admin.services.audit import init_audit, log_audit
from admin.services.auth import current_user, is_logged_in, logout
from admin.services.backup import create_backup
from admin.services.db import db_count, db_df
from admin.services.rate_limit import (
    count_recent_failed_logins,
    lockout_remaining_sec,
)
from admin.views import (
    alerts as v_alerts,
)
from admin.views import (
    audit as v_audit,
)
from admin.views import (
    backup as v_backup,
)
from admin.views import (
    cells as v_cells,
)
from admin.views import (
    cores as v_cores,
)
from admin.views import (
    dashboard as v_dashboard,
)
from admin.views import (
    encryption as v_encryption,
)
from admin.views import (
    special_lines as v_special_lines,
)
from admin.views import (
    subscribers as v_subscribers,
)
from telecom_common import (
    DB_PATH,
    has_password,
    set_password,
    verify_password,
)


def _inject_css():
    st.markdown(
        '<style>html,body,[class*="css"]{direction:ltr;text-align:left;'
        "font-family:'Segoe UI',sans-serif;}"
        ".admin-header{background:linear-gradient(90deg,#dc2626,#7c2d12);"
        "padding:18px 24px;border-radius:14px;color:#fff;"
        "display:flex;justify-content:space-between;align-items:center;}"
        ".danger-box{background:#fef2f2;border-left:4px solid #ef4444;"
        "padding:12px 16px;border-radius:8px;margin:10px 0;}</style>",
        unsafe_allow_html=True,
    )


def _render_first_time_setup():
    st.markdown(
        '<div class="admin-header"><div>'
        '<div style="font-size:24px;font-weight:800;">'
        "TELECOM Admin Panel</div>"
        '<div style="opacity:.9;font-size:13px;">'
        "First-time setup</div></div></div>",
        unsafe_allow_html=True,
    )
    st.write("")
    with st.form("setup_pw"):
        pw1 = st.text_input("Password (min 8 chars)", type="password")
        pw2 = st.text_input("Confirm Password", type="password")
        if st.form_submit_button("Create Password", use_container_width=True):
            if len(pw1) < 8:
                st.error("At least 8 characters.")
            elif pw1 != pw2:
                st.error("Mismatch.")
            else:
                set_password(pw1)
                st.session_state["admin_logged_in"] = True
                st.session_state["admin_user"] = "admin"
                st.rerun()


def _render_login():
    recent_fails = count_recent_failed_logins()
    locked_out = recent_fails >= LOGIN_MAX_FAILS

    st.markdown(
        '<div class="admin-header"><div>'
        '<div style="font-size:24px;font-weight:800;">'
        "TELECOM Admin Panel</div>"
        '<div style="opacity:.9;font-size:13px;">'
        "Authenticated access</div></div></div>",
        unsafe_allow_html=True,
    )
    st.write("")

    if locked_out:
        sec = lockout_remaining_sec()
        mins = max(1, (sec + 59) // 60)
        st.error(
            f"Too many failed logins ({recent_fails}/{LOGIN_MAX_FAILS}). "
            f"Try again in about {mins} minute(s)."
        )
        st.stop()

    with st.form("login"):
        user = st.text_input("Username", value="admin")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            if user == "admin" and verify_password(pw):
                st.session_state["admin_logged_in"] = True
                st.session_state["admin_user"] = "admin"
                log_audit("LOGIN", "system", "-", "successful")
                st.rerun()
            else:
                log_audit("LOGIN_FAILED", "system", user or "-", "bad credentials")
                remaining = LOGIN_MAX_FAILS - (recent_fails + 1)
                if remaining > 0:
                    st.error(
                        f"Invalid credentials. "
                        f"{remaining} attempt(s) left in the "
                        f"{LOGIN_WINDOW_MIN}-minute window."
                    )
                else:
                    st.error(
                        f"Too many failed logins. Try again in "
                        f"about {LOGIN_WINDOW_MIN} minute(s)."
                    )


def _render_sidebar():
    with st.sidebar:
        st.markdown(f"### {current_user()}")
        if st.button("Logout", use_container_width=True):
            log_audit("LOGOUT", "system", "-", "")
            logout()
            st.rerun()
        st.divider()
        st.markdown("### Quick Stats")
        st.metric("Subscribers", f"{db_count('subscribers'):,}")
        st.metric("Cells", f"{db_count('cells'):,}")
        try:
            n6g = int(db_df("SELECT COUNT(*) AS n FROM cells WHERE tech='6G'").iloc[0]["n"])
            st.metric("  6G Cells", f"{n6g:,}")
        except Exception:
            pass
        st.metric("Core Nodes", f"{db_count('cores'):,}")
        st.metric("CDR Records", f"{db_count('cdrs'):,}")
        st.metric("Alerts", f"{db_count('alerts'):,}")
        st.divider()
        if st.button("Create Backup Now", use_container_width=True):
            p = create_backup("manual")
            log_audit("BACKUP", "db", p, "manual")
            st.success(f"Backup: {os.path.basename(p)}")


def main():
    st.set_page_config(
        page_title="TELECOM Admin Panel",
        page_icon="\u2699\ufe0f",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_css()

    if not os.path.exists(DB_PATH):
        st.error("Database not found. Run telecom_net_sim.py first.")
        st.stop()

    init_audit()

    # First-time password setup
    if not has_password():
        _render_first_time_setup()
        st.stop()

    # Login
    if not is_logged_in():
        _render_login()
        st.stop()

    # Header
    st.markdown(
        f'<div class="admin-header"><div>'
        f'<div style="font-size:22px;font-weight:800;">'
        f"TELECOM Admin Panel</div>"
        f'<div style="opacity:.9;font-size:13px;">CRUD | Audit | Backup | '
        f"User: <b>{current_user()}</b></div></div>"
        f'<div style="text-align:right;font-size:12px;opacity:.9;">'
        f"{datetime.now():%Y-%m-%d %H:%M}</div></div>",
        unsafe_allow_html=True,
    )
    st.write("")

    _render_sidebar()

    tabs = st.tabs(
        [
            "Dashboard",
            "Subscribers",
            "Cells",
            "Core Nodes",
            "Alerts",
            "Special Lines",
            "Encryption",
            "Backup / Restore",
            "Audit Log",
        ]
    )

    with tabs[0]:
        v_dashboard.render()
    with tabs[1]:
        v_subscribers.render()
    with tabs[2]:
        v_cells.render()
    with tabs[3]:
        v_cores.render()
    with tabs[4]:
        v_alerts.render()
    with tabs[5]:
        v_special_lines.render()
    with tabs[6]:
        v_encryption.render()
    with tabs[7]:
        v_backup.render()
    with tabs[8]:
        v_audit.render()


if __name__ == "__main__":
    main()
