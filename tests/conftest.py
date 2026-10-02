"""Shared fixtures for the test suite.

Key guarantee: NO test writes to the real telecom_sim_output/ directory.
All filesystem-touching tests use tmp_path or a subprocess in an
isolated directory.
"""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pytest_addoption(parser):
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow integration tests that spawn the full simulator",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: slow integration tests (subprocess-based)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-slow"):
        return
    skip_slow = pytest.mark.skip(reason="need --run-slow to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture(autouse=True)
def _chdir_project_root(monkeypatch):
    """Make relative paths in telecom_common resolve against project root."""
    monkeypatch.chdir(PROJECT_ROOT)
    yield


@pytest.fixture
def project_root():
    return PROJECT_ROOT


@pytest.fixture
def real_db(project_root):
    """Path to the live DB. Skips the test if it does not exist."""
    p = project_root / "telecom_sim_output" / "telecom_sim.db"
    if not p.exists():
        pytest.skip(f"real DB not found at {p}; run telecom_net_sim.py first")
    return p
