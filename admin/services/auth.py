"""Session-state helpers for authentication (Streamlit-based)."""

import streamlit as st


def is_logged_in() -> bool:
    return st.session_state.get("admin_logged_in", False)


def current_user() -> str:
    try:
        return st.session_state.get("admin_user") or "anonymous"
    except Exception:
        return "system"


def logout() -> None:
    st.session_state["admin_logged_in"] = False
    st.session_state["admin_user"] = None
