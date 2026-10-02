# -*- coding: utf-8 -*-
"""Backwards-compatible shim.

The old monolithic telecom_admin.py has been split into the
`admin/` package. This file exists so that existing invocations
(`streamlit run telecom_admin.py`) keep working.

Use either:
    streamlit run telecom_admin.py
    streamlit run admin/main.py
"""
import os
import sys

# Ensure the project root is importable so `admin` package is found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from admin.main import main

if __name__ == "__main__":
    main()