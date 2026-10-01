# -*- coding: utf-8 -*-
"""Slow integration test: run the whole simulator in an isolated dir.

Skipped unless pytest is invoked with --run-slow.

Safety: copies all telecom_*.py into a temp dir and runs there, so the
real telecom_sim_output/ is never touched.
"""
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.slow
def test_full_simulator_run(tmp_path):
    # 1) Copy source files
    py_files = list(PROJECT_ROOT.glob("telecom_*.py"))
    assert py_files, "no telecom_*.py files found in project root"
    for py in py_files:
        shutil.copy2(py, tmp_path)

    # 2) Run from isolated dir
    proc = subprocess.run(
        [sys.executable, "telecom_net_sim.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, (
        f"simulator failed:\nSTDOUT:\n{proc.stdout[-2000:]}\n"
        f"STDERR:\n{proc.stderr[-2000:]}"
    )

    # 3) DB must exist and be populated
    db = tmp_path / "telecom_sim_output" / "telecom_sim.db"
    assert db.exists(), f"DB not created at {db}"

    con = sqlite3.connect(db)
    try:
        n_cells = con.execute("SELECT COUNT(*) FROM cells").fetchone()[0]
        n_subs = con.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
        n_cdrs = con.execute("SELECT COUNT(*) FROM cdrs").fetchone()[0]
        n_6g = con.execute(
            "SELECT COUNT(*) FROM cells WHERE tech='6G'"
        ).fetchone()[0]
        n_alerts = con.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        n_atk = con.execute(
            "SELECT COUNT(*) FROM attack_scenarios"
        ).fetchone()[0]
    finally:
        con.close()

    assert n_cells > 0
    assert n_subs == 5000
    assert n_cdrs == 60_000
    assert n_6g > 0
    assert n_alerts > 0
    assert n_atk == 25

    # 4) report.txt must mention 6G cells
    report = (tmp_path / "telecom_sim_output" / "report.txt").read_text(
        encoding="utf-8"
    )
    assert "6G" in report
    assert "NETWORK TOPOLOGY" in report

    # 5) attack_scenarios should include 6G layer
    con = sqlite3.connect(db)
    try:
        layers = {row[0] for row in con.execute(
            "SELECT DISTINCT target_layer FROM attack_scenarios"
        )}
    finally:
        con.close()
    assert "6G" in layers, f"no 6G scenarios persisted: {layers}"
