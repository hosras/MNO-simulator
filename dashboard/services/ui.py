# -*- coding: utf-8 -*-
"""Small Streamlit UI helpers (KPI card, formatter, page header)."""
from datetime import datetime
import streamlit as st

from dashboard._config import OPERATOR_DEFAULT


def kpi(label, value, sub="", color="#10b981"):
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub" style="color:{color}">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def fmt_num(n):
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def render_header():
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,#0ea5e9,#1e3a8a);
                padding:18px 24px;border-radius:14px;color:#fff;
                display:flex;justify-content:space-between;align-items:center;">
      <div>
        <div style="font-size:24px;font-weight:800;">📡 {OPERATOR_DEFAULT} Network Dashboard</div>
        <div style="opacity:.85;font-size:13px;">Network Simulation + OSINT/SIGINT + Voice/Messaging + Encryption + Alerts</div>
      </div>
      <div style="text-align:right;font-size:12px;opacity:.9;">
        {datetime.now().strftime('%Y-%m-%d %H:%M')}
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.write("")