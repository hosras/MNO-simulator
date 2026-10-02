"""Backwards-compatible shim.

The old monolithic telecom_radar.py has been split into the
`radar/` package. This file exists so that existing invocations
(`streamlit run telecom_radar.py`) keep working.

Use either:
    streamlit run telecom_radar.py
    streamlit run radar/main.py
"""

import os
import sys

# Ensure the project root is importable so `radar` package is found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from radar.main import main

if __name__ == "__main__":
    main()
