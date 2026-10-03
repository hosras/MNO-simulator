"""Tests to close the remaining coverage gaps.

Targets:
  - admin/services/backup.py:104 (integrity check failure)
  - admin/services/backup.py:123-124 (sidecar removal OSError)
  - attack_core.py:316->319 (branch in attacks_to_alerts)
  - make_coverage_badge.py:16-17 (ImportError path)
  - radar/services/pdf.py:111-112 (build_pdf exception)
  - telecom_attack.py:625-626, 654-655 (exception paths)
  - telecom_logging.py:91 (int level branch)
"""

import os
import sqlite3
import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path before importing project modules.
# (conftest.py does this too, but pytest may collect this file first.)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import admin.services.backup as backup_module  # noqa: E402
import telecom_attack  # noqa: E402


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
@pytest.fixture
def isolated_backup(tmp_path, monkeypatch):
    """Redirect DB_PATH + BACKUP_DIR to tmp_path."""
    db = tmp_path / "t.db"
    bdir = tmp_path / "bk"
    bdir.mkdir()
    monkeypatch.setattr(backup_module, "DB_PATH", str(db))
    monkeypatch.setattr(backup_module, "BACKUP_DIR", str(bdir))
    return {"db": db, "bk": bdir}


def _make_valid_db(path):
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE t (x INT)")
    con.execute("INSERT INTO t VALUES (1)")
    con.commit()
    con.close()


# ==================================================================
# 1) admin/services/backup.py:104 — integrity check failure
# ==================================================================
class TestRestoreIntegrityFailure:
    """Cover the branch where PRAGMA quick_check returns non-ok."""

    def test_restore_raises_when_backup_is_corrupt(self, isolated_backup, monkeypatch):
        # 1) Create a valid live DB + a real backup
        _make_valid_db(isolated_backup["db"])
        p = backup_module.create_backup("snap")
        filename = os.path.basename(p)

        # 2) Patch sqlite3.connect so PRAGMA quick_check returns corrupt
        class FakeCursor:
            def fetchone(self):
                return ("corrupt",)

        class FakeConn:
            def execute(self, sql, *args, **kwargs):
                return FakeCursor()

            def close(self):
                pass

        def patched_connect(path, *args, **kwargs):
            return FakeConn()

        monkeypatch.setattr(backup_module.sqlite3, "connect", patched_connect)

        with pytest.raises(RuntimeError, match="integrity check failed"):
            backup_module.restore_backup(filename)


# ==================================================================
# 2) admin/services/backup.py:123-124 — sidecar removal OSError
# ==================================================================
class TestRestoreSidecarRemoval:
    def test_restore_survives_oserror_on_sidecar_removal(self, isolated_backup, monkeypatch):
        _make_valid_db(isolated_backup["db"])
        p = backup_module.create_backup("snap")
        filename = os.path.basename(p)

        # Pretend the -wal/-shm sidecar files exist
        real_exists = os.path.exists

        def fake_exists(path):
            if str(path).endswith("-wal") or str(path).endswith("-shm"):
                return True
            return real_exists(path)

        monkeypatch.setattr(backup_module.os.path, "exists", fake_exists)

        # Make os.remove raise OSError for the sidecar paths
        def fake_remove(path):
            if str(path).endswith("-wal") or str(path).endswith("-shm"):
                raise OSError("mocked: file is locked")

        monkeypatch.setattr(backup_module.os, "remove", fake_remove)

        # Should NOT raise; the OSError is silently swallowed
        result = backup_module.restore_backup(filename)
        assert os.path.isabs(result)


# ==================================================================
# 3) attack_core.py — severity branches
# ==================================================================
class TestAttackCoreBranch:
    def test_attacks_to_alerts_with_medium_low_severities(self):
        from attack_core import attacks_to_alerts

        scenarios = [
            {
                "scenario_id": "s1",
                "name": "x",
                "attack_type": "X",
                "target_layer": "X",
                "target_node": "n",
                "target_iface": "i",
                "protocol": "p",
                "severity": "LOW",
                "start_ts": "2026-01-01 00:00:00",
                "end_ts": "2026-01-01 00:01:00",
                "duration_sec": 60,
                "rate_pps": 10,
                "total_events": 600,
                "source_ip": "1.1.1.1",
                "mitre": "T1",
                "status": "DETECTED",
                "notes": "",
            },
            {
                "scenario_id": "s2",
                "name": "x",
                "attack_type": "X",
                "target_layer": "X",
                "target_node": "n",
                "target_iface": "i",
                "protocol": "p",
                "severity": "CRITICAL",
                "start_ts": "2026-01-01 00:00:00",
                "end_ts": "2026-01-01 00:01:00",
                "duration_sec": 60,
                "rate_pps": 10,
                "total_events": 600,
                "source_ip": "1.1.1.1",
                "mitre": "T1",
                "status": "BLOCKED",
                "notes": "",
            },
        ]
        alerts = attacks_to_alerts(scenarios, [])
        assert len(alerts) == 2
        severities = {a["severity"] for a in alerts}
        assert "LOW" in severities
        assert "CRITICAL" in severities

    def test_attacks_to_alerts_all_below_30(self):
        from attack_core import attacks_to_alerts

        scenarios = [
            {
                "scenario_id": f"s{i}",
                "name": "x",
                "attack_type": "X",
                "target_layer": "X",
                "target_node": "n",
                "target_iface": "i",
                "protocol": "p",
                "severity": "HIGH",
                "start_ts": "2026-01-01 00:00:00",
                "end_ts": "2026-01-01 00:01:00",
                "duration_sec": 60,
                "rate_pps": 10,
                "total_events": 600,
                "source_ip": "1.1.1.1",
                "mitre": "T1",
                "status": "DETECTED",
                "notes": "",
            }
            for i in range(5)
        ]
        alerts = attacks_to_alerts(scenarios, [])
        assert len(alerts) == 5


# ==================================================================
# 4) make_coverage_badge.py — ImportError path
# ==================================================================
class TestMakeCoverageBadgeImportError:
    def test_module_raises_systemexit_when_coverage_missing(self, monkeypatch):
        import importlib

        real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def blocked_import(name, *args, **kwargs):
            if name == "coverage" or name.startswith("coverage."):
                raise ImportError("mocked: coverage not available")
            return real_import(name, *args, **kwargs)

        saved = sys.modules.pop("make_coverage_badge", None)
        try:
            monkeypatch.setattr("builtins.__import__", blocked_import)
            with pytest.raises(SystemExit):
                importlib.import_module("make_coverage_badge")
        finally:
            if saved is not None:
                sys.modules["make_coverage_badge"] = saved
            else:
                sys.modules.pop("make_coverage_badge", None)


# ==================================================================
# 5) radar/services/pdf.py — build_pdf exception
# ==================================================================
class TestPdfBuildException:
    def test_build_pdf_returns_none_on_exception(self, monkeypatch):
        import radar.services.pdf as pdf_module

        if not pdf_module.HAS_PDF:
            pytest.skip("reportlab not installed")

        class BrokenTemplate:
            def __init__(self, *a, **kw):
                pass

            def build(self, *a, **kw):
                raise RuntimeError("mocked build failure")

        monkeypatch.setattr(pdf_module, "SimpleDocTemplate", BrokenTemplate)

        out = pdf_module.build_pdf("title", [{"text": "x"}])
        assert out is None


# ==================================================================
# 6) telecom_attack.py — exception paths
# ==================================================================
class TestInjectAlertsExceptions:
    def test_inject_swallows_cleanup_exception(self, monkeypatch):
        class FakeCursor:
            def execute(self, sql, params=()):
                if "DELETE" in sql:
                    raise sqlite3.OperationalError("mocked DELETE failure")

            def close(self):
                pass

        class FakeConn:
            def cursor(self):
                return FakeCursor()

            def commit(self):
                pass

            def close(self):
                pass

        monkeypatch.setattr(telecom_attack, "db_connect", lambda: FakeConn())

        telecom_attack.inject_attack_alerts(
            [
                {
                    "alert_id": "A1",
                    "timestamp": "x",
                    "severity": "HIGH",
                    "alert_type": "ATTACK_X",
                    "msisdn": "-",
                    "description": "d",
                    "extra": "{}",
                    "sms_sent": 0,
                    "sms_to": "",
                    "sms_body": "",
                    "ack": 0,
                }
            ]
        )

    def test_inject_swallows_insert_exception(self, monkeypatch):
        class FakeCursor:
            def execute(self, sql, params=()):
                if "INSERT" in sql.upper():
                    raise sqlite3.IntegrityError("mocked INSERT failure")

            def close(self):
                pass

        class FakeConn:
            def cursor(self):
                return FakeCursor()

            def commit(self):
                pass

            def close(self):
                pass

        monkeypatch.setattr(telecom_attack, "db_connect", lambda: FakeConn())

        telecom_attack.inject_attack_alerts(
            [
                {
                    "alert_id": "A2",
                    "timestamp": "x",
                    "severity": "HIGH",
                    "alert_type": "ATTACK_X",
                    "msisdn": "-",
                    "description": "d",
                    "extra": "{}",
                    "sms_sent": 1,
                    "sms_to": "98...",
                    "sms_body": "b",
                    "ack": 0,
                }
            ]
        )


# ==================================================================
# 7) telecom_logging.py — int level branch
# ==================================================================
class TestLoggingParseLevel:
    def test_parse_level_with_int(self):
        from telecom_logging import _parse_level

        assert _parse_level(10) == 10
        assert _parse_level(20) == 20
        assert _parse_level(30) == 30

    def test_parse_level_with_string(self):
        from telecom_logging import _parse_level

        assert _parse_level("DEBUG") == 10
        assert _parse_level("info") == 20
        assert _parse_level("warning") == 30
        assert _parse_level("unknown") == 20


# ==================================================================
# 8) attack_core.py — all severities
# ==================================================================
class TestAttackCoreSeverityBranch:
    def test_all_severities_covered(self):
        from attack_core import attacks_to_alerts

        base = {
            "name": "x",
            "attack_type": "X",
            "target_layer": "X",
            "target_node": "n",
            "target_iface": "i",
            "protocol": "p",
            "start_ts": "2026-01-01 00:00:00",
            "end_ts": "2026-01-01 00:01:00",
            "duration_sec": 60,
            "rate_pps": 10,
            "total_events": 600,
            "source_ip": "1.1.1.1",
            "mitre": "T1",
            "status": "DETECTED",
            "notes": "",
        }

        severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        scenarios = [
            {**base, "scenario_id": f"s{i}", "severity": sev} for i, sev in enumerate(severities)
        ]
        alerts = attacks_to_alerts(scenarios, [])
        assert len(alerts) == 4
        assert {a["severity"] for a in alerts} == set(severities)


# ==================================================================
# 9) attack_core.py — now is not None branch
# ==================================================================
class TestAttackCoreWithExplicitNow:
    def test_generate_scenarios_with_explicit_now(self):
        from datetime import datetime

        from attack_core import generate_scenarios

        idx = {
            "cores": {"HSS": ["HSS-01"]},
            "all_cores": ["AMF-01"],
            "cells_5g": ["5G-001"],
            "cells_6g": ["6G-001"],
        }

        fixed_now = datetime(2026, 6, 15, 12, 0, 0)
        scenarios = generate_scenarios(5, idx, now=fixed_now)

        assert len(scenarios) == 5
        for s in scenarios:
            assert s["scenario_id"].startswith("ATK-20260615-")
