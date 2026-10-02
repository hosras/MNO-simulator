# -*- coding: utf-8 -*-
"""Backwards-compatible shim.

The old monolithic telecom_dashboard.py has been split into the
`dashboard/` package. This file exists so that existing invocations
(`streamlit run telecom_dashboard.py`) keep working.

Use either:
    streamlit run telecom_dashboard.py
    streamlit run dashboard/main.py
"""
import os
import sys

# Ensure the project root is importable so `dashboard` package is found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dashboard.main import main

if __name__ == "__main__":
    main()