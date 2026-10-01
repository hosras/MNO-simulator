# -*- coding: utf-8 -*-
"""Smoke tests: each module imports cleanly in a fresh subprocess.

Using subprocess (rather than import) gives us a clean __name__ context
and lets us assert on stderr, catching the Streamlit-warning problem
we fixed earlier.
"""
import subprocess
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CLEAN_IMPORT_MODULES = [
    "telecom_common",
    "telecom_net_sim",
    "telecom_attack",
    "telecom_admin",
    "telecom_radar",       # [RADAR-MAIN-GUARD v1]
    "telecom_dashboard",   # [DASHBOARD-MAIN-GUARD v1]
]

SYNTAX_ONLY_MODULES = [
    # (all top-level scripts are now guarded)
]


@pytest.mark.parametrize("mod", CLEAN_IMPORT_MODULES)
def test_import_cleanly(mod):
    proc = subprocess.run(
        [sys.executable, "-c", f"import {mod}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"import {mod} failed:\n{proc.stderr}"
    assert proc.stderr.strip() == "", (
        f"import {mod} produced stderr output:\n{proc.stderr}"
    )


if SYNTAX_ONLY_MODULES:

    @pytest.mark.parametrize("mod", SYNTAX_ONLY_MODULES)
    def test_syntax_only(mod):
        """Scripts that cannot be cleanly imported; verify syntax only."""
        src = (PROJECT_ROOT / f"{mod}.py").read_text(encoding="utf-8")
        compile(src, f"{mod}.py", "exec")
