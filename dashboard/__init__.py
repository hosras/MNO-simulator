"""TELECOM Network Dashboard package.

Usage:
    streamlit run telecom_dashboard.py      (backwards-compatible shim)
    streamlit run dashboard/main.py         (direct)
"""

from dashboard.main import main

__all__ = ["main"]
