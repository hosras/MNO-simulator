# -*- coding: utf-8 -*-
"""Global CSS — injected once by main()."""
import streamlit as st


def inject_css():
    st.markdown("""
    <style>
      html, body, [class*="css"] {
        direction: ltr; text-align: left;
        font-family: 'Segoe UI','Roboto','Helvetica Neue',sans-serif;
      }
      .kpi-card {
        background: linear-gradient(135deg,#1f2937 0%,#111827 100%);
        color:#e5e7eb; padding:16px 18px; border-radius:14px;
        border:1px solid #374151; box-shadow:0 4px 14px rgba(0,0,0,.35);
        text-align:left;
      }
      .kpi-card .kpi-label {font-size:13px; color:#9ca3af;}
      .kpi-card .kpi-value {font-size:26px; font-weight:700; color:#fff; margin-top:2px;}
      .kpi-card .kpi-sub   {font-size:12px; color:#10b981; margin-top:4px;}
      section.main > div {padding-top: 1rem;}
      div[data-testid="stMetricValue"] { font-size: 22px; }
    </style>
    """, unsafe_allow_html=True)