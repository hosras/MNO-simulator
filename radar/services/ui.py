"""Small Streamlit UI helpers (cards, formatters, section headers)."""

import streamlit as st

from radar._config import BLUE, DARK, GRAY, GREEN, ORANGE, PURPLE, RED
from telecom_ui_common import chart as _chart

# Auto-key counter for download buttons
_dl_counter = {"n": 0}


def fmt(n, decimals=0):
    try:
        n = float(n)
    except Exception:
        return str(n)
    if abs(n) >= 1e9:
        return f"{n/1e9:.{decimals+1}f}B"
    if abs(n) >= 1e6:
        return f"{n/1e6:.{decimals+1}f}M"
    if abs(n) >= 1e3:
        return f"{n/1e3:.{decimals+1}f}K"
    return f"{n:,.{decimals}f}"


def stat_card(label, value, delta=None, delta_pct=None, sub="", compare_on=False):
    delta_html = ""
    if compare_on and delta is not None:
        cls = (
            "stat-delta-up"
            if delta > 0
            else ("stat-delta-down" if delta < 0 else "stat-delta-flat")
        )
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        pct = f" ({delta_pct:+.1f}%)" if delta_pct is not None else ""
        delta_html = f'<div class="{cls}">' f"{arrow} {abs(delta):,.0f}{pct} vs prev</div>"
    sub_html = f'<div class="stat-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
    <div class="stat-card">
      <div class="stat-label">{label}</div>
      <div class="stat-value">{value}</div>
      {delta_html}{sub_html}
    </div>
    """,
        unsafe_allow_html=True,
    )


def threat_card(label, value, sub=""):
    sub_html = (
        (f'<div style="font-size:12px;color:#7f1d1d;margin-top:4px;">' f"{sub}</div>")
        if sub
        else ""
    )
    st.markdown(
        f"""
    <div class="threat-card">
      <div class="threat-label">{label}</div>
      <div class="threat-value">{value}</div>
      {sub_html}
    </div>
    """,
        unsafe_allow_html=True,
    )


def anomaly_card(label, value, sub=""):
    sub_html = (
        (f'<div style="font-size:12px;color:#9a3412;margin-top:4px;">' f"{sub}</div>")
        if sub
        else ""
    )
    st.markdown(
        f"""
    <div class="anomaly-card">
      <div class="anomaly-label">{label}</div>
      <div class="anomaly-value">{value}</div>
      {sub_html}
    </div>
    """,
        unsafe_allow_html=True,
    )


def section(title):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def safe_chart(fig, **kwargs):
    try:
        _chart(fig, use_container_width=True, **kwargs)
    except TypeError:
        _chart(fig, **kwargs)


def dl_button(label, data=None, file_name=None, mime=None, **kwargs):
    """st.download_button with a guaranteed-unique key."""
    _dl_counter["n"] += 1
    kwargs.setdefault("key", f"radar_dl_{_dl_counter['n']}")
    return st.download_button(label, data=data, file_name=file_name, mime=mime, **kwargs)


def csv_btn(df, filename, label="⬇️ CSV"):
    dl_button(
        label, data=df.to_csv(index=False).encode("utf-8-sig"), file_name=filename, mime="text/csv"
    )


__all__ = [
    "fmt",
    "stat_card",
    "threat_card",
    "anomaly_card",
    "section",
    "safe_chart",
    "dl_button",
    "csv_btn",
    "ORANGE",
    "BLUE",
    "GREEN",
    "RED",
    "PURPLE",
    "GRAY",
    "DARK",
]
