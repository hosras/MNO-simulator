"""Extra tests to close remaining coverage gaps.

Targets specific defensive branches in backup.py, anomaly.py, pdf.py,
telecom_attack.py, and attack_core.py that aren't exercised by the
happy-path tests.
"""

import importlib
import os
import sqlite3
import sys

import pandas as pd
import pytest

import admin.services.backup as backup_module
import attack_core
import radar.services.pdf as pdf_module
import telecom_attack
from admin.services.backup import create_backup, restore_backup
from radar.services.anomaly import detect_anomalies


# ==================================================================
# Fixtures
# ==================================================================
@pytest.fixture
def isolated_backup(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    bdir = tmp_path / "bk"
    bdir.mkdir()
    monkeypatch.setattr(backup_module, "DB_PATH", str(db))
    monkeypatch.setattr(backup_module, "BACKUP_DIR", str(bdir))
    return {"db": db, "bk": bdir}


@pytest.fixture
def attack_db(tmp_path, monkeypatch):
    db_path = tmp_path / "atk.db"

    def fake_connect():
        con = sqlite3.connect(str(db_path))
        con.execute("PRAGMA journal_mode=WAL")
        return con

    monkeypatch.setattr(telecom_attack, "db_connect", fake_connect)

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE cores (
            node_id TEXT PRIMARY KEY, name TEXT, role TEXT,
            tech TEXT, city TEXT, capacity_tps INT);
        CREATE TABLE cells (
            cell_id TEXT PRIMARY KEY, name TEXT, tech TEXT, city TEXT,
            lat REAL, lon REAL, band TEXT, azimuth INT, tilt INT,
            tx_dbm REAL, backhaul_gbps REAL);
        CREATE TABLE alerts (
            alert_id TEXT PRIMARY KEY, timestamp TEXT, severity TEXT,
            alert_type TEXT, msisdn TEXT, description TEXT, extra TEXT,
            sms_sent INT, sms_to TEXT, sms_body TEXT, ack INT);
        CREATE TABLE sms_alerts (
            sms_id INTEGER PRIMARY KEY AUTOINCREMENT, alert_id TEXT,
            timestamp TEXT, recipient TEXT, body TEXT, status TEXT);
    """)
    cur.execute(
        "INSERT INTO cores VALUES (?,?,?,?,?,?)",
        ("HSS-01", "H", "HSS", "4G", "Tehran", 1),
    )
    cur.execute(
        "INSERT INTO cells VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("6G-TEH-0001", "c", "6G", "Tehran", 35.7, 51.4, "THz-140", 0, 4, 40, 100),
    )
    con.commit()
    con.close()
    yield db_path


def _make_valid_db(path):
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE t (x INT)")
    con.execute("INSERT INTO t VALUES (1)")
    con.commit()
    con.close()


# ==================================================================
# admin/services/backup.py
# ==================================================================
class TestBackupIntegrityFailure:
    def test_create_backup_raises_when_quick_check_fails(self, isolated_backup, monkeypatch):
        """Covers the create_backup integrity-check failure branch."""
        _make_valid_db(isolated_backup["db"])

        class FakeCursor:
            def fetchone(self):
                return ("corrupt",)

        class FakeSrcConnection:
            def backup(self, dst):
                pass

            def close(self):
                pass

        class FakeDstConnection:
            def execute(self, sql):
                return FakeCursor()

            def close(self):
                pass

        call_count = {"n": 0}

        def fake_connect(path):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return FakeSrcConnection()
            return FakeDstConnection()

        # Patch sqlite3.connect globally — the module-level function is
        # mutable (unlike sqlite3.Connection.execute which is immutable).
        monkeypatch.setattr(sqlite3, "connect", fake_connect)

        with pytest.raises(RuntimeError, match="integrity check failed"):
            create_backup("test")


class TestBackupSidecarRemoval:
    def test_remove_oserror_is_suppressed(self, isolated_backup, monkeypatch):
        """Covers the except OSError: pass in sidecar cleanup."""
        _make_valid_db(isolated_backup["db"])
        p = create_backup("snap")
        filename = os.path.basename(p)

        # Create sidecar files so os.path.exists(side) is True
        db_path = str(isolated_backup["db"])
        for suffix in ("-wal", "-shm"):
            with open(db_path + suffix, "wb") as f:
                f.write(b"stale")

        real_remove = os.remove

        def failing_remove(path):
            if path.endswith("-wal") or path.endswith("-shm"):
                raise OSError("locked")
            return real_remove(path)

        monkeypatch.setattr(backup_module.os, "remove", failing_remove)

        # Should not raise despite the OSError
        restore_backup(filename)


class TestBackupOtherPaths:
    def test_restore_none_filename(self, isolated_backup):
        with pytest.raises(RuntimeError, match="Invalid backup filename"):
            restore_backup(None)

    def test_restore_empty_filename(self, isolated_backup):
        with pytest.raises(RuntimeError, match="Invalid backup filename"):
            restore_backup("")

    def test_restore_int_filename(self, isolated_backup):
        with pytest.raises(RuntimeError, match="Invalid backup filename"):
            restore_backup(12345)

    def test_restore_missing_live_db(self, isolated_backup):
        """Covers the 'Live DB not found' raise (backup exists, DB gone)."""
        _make_valid_db(isolated_backup["db"])
        p = create_backup("snap")
        filename = os.path.basename(p)
        isolated_backup["db"].unlink()
        with pytest.raises(RuntimeError, match="Live DB not found"):
            restore_backup(filename)


# ==================================================================
# radar/services/anomaly.py — extra branches
# ==================================================================
class TestAnomalyWeakCellsBranches:
    def test_single_weak_cell_is_skipped(self):
        """Covers branch where len(vals) <= 1."""
        sig = {"weak_cells": [["CELL-A", 5]]}
        # Need at least 4 hours so hourly doesn't kick in
        df = pd.DataFrame(
            [
                {
                    "hour": h,
                    "city": "Tehran",
                    "call_type": "voice",
                    "voice_bearer": "VoLTE",
                    "tech": "4G",
                    "record_id": f"r{i}",
                }
                for h in range(4)
                for i in range(3)
            ]
        )
        result = detect_anomalies(df, pd.DataFrame(), sig)
        assert not any(a["type"] == "Weak Cell" for a in result)

    def test_weak_cells_with_identical_values(self):
        """Covers branch where std == 0 for weak cells."""
        sig = {
            "weak_cells": [
                ["CELL-A", 5],
                ["CELL-B", 5],
                ["CELL-C", 5],
                ["CELL-D", 5],
            ]
        }
        df = pd.DataFrame(
            [
                {
                    "hour": h,
                    "city": "Tehran",
                    "call_type": "voice",
                    "voice_bearer": "VoLTE",
                    "tech": "4G",
                    "record_id": f"r{i}",
                }
                for h in range(4)
                for i in range(3)
            ]
        )
        result = detect_anomalies(df, pd.DataFrame(), sig)
        assert not any(a["type"] == "Weak Cell" for a in result)

    def test_weak_cells_z_below_threshold(self):
        """Covers weak cell loop where abs(z) <= 2."""
        sig = {
            "weak_cells": [
                ["CELL-A", 10],
                ["CELL-B", 10],
                ["CELL-C", 11],
                ["CELL-D", 9],
                ["CELL-E", 10],
                ["CELL-F", 11],
                ["CELL-G", 10],
                ["CELL-H", 10],
                ["CELL-I", 9],
                ["CELL-J", 10],
            ]
        }
        df = pd.DataFrame(
            [
                {
                    "hour": h,
                    "city": "Tehran",
                    "call_type": "voice",
                    "voice_bearer": "VoLTE",
                    "tech": "4G",
                    "record_id": f"r{i}",
                }
                for h in range(4)
                for i in range(3)
            ]
        )
        result = detect_anomalies(df, pd.DataFrame(), sig)
        # All cells within ~2 sigma → no anomalies
        assert not any(a["type"] == "Weak Cell" for a in result)


class TestAnomalyVoiceBearerBranches:
    def test_no_voice_bearer_column(self):
        """Covers branch where 'voice_bearer' not in columns."""
        df = pd.DataFrame(
            [
                {
                    "hour": h,
                    "city": "Tehran",
                    "call_type": "voice",
                    "tech": "4G",
                    "record_id": f"r{i}",
                }
                for h in range(4)
                for i in range(3)
            ]
        )
        detect_anomalies(df, pd.DataFrame(), {})
        # Just shouldn't crash

    def test_voice_bearer_column_with_empty_voice(self):
        """Covers branch where len(v) == 0 in voice section."""
        df = pd.DataFrame(
            [
                {
                    "hour": h,
                    "city": "Tehran",
                    "call_type": "data",
                    "voice_bearer": None,
                    "tech": "4G",
                    "record_id": f"r{i}",
                }
                for h in range(4)
                for i in range(3)
            ]
        )
        result = detect_anomalies(df, pd.DataFrame(), {})
        assert not any(a["type"] == "VoLTE Fallback" for a in result)

    def test_voice_bearer_no_csfb(self):
        """Covers branch where csfb_pct <= 0.8."""
        df = pd.DataFrame(
            [
                {
                    "hour": h,
                    "city": "Tehran",
                    "call_type": "voice",
                    "voice_bearer": "VoLTE",
                    "tech": "4G",
                    "record_id": f"r{i}",
                }
                for h in range(4)
                for i in range(10)
            ]
        )
        result = detect_anomalies(df, pd.DataFrame(), {})
        assert not any(a["type"] == "VoLTE Fallback" for a in result)

    def test_voice_bearer_csfb_but_no_modern_tech(self):
        """Covers branch where modern <= 0.5."""
        df = pd.DataFrame(
            [
                {
                    "hour": h,
                    "city": "Tehran",
                    "call_type": "voice",
                    "voice_bearer": "CSFB",
                    "tech": "2G",
                    "record_id": f"r{i}",
                }
                for h in range(4)
                for i in range(10)
            ]
        )
        result = detect_anomalies(df, pd.DataFrame(), {})
        # No modern tech → no VoLTE Fallback anomaly
        assert not any(a["type"] == "VoLTE Fallback" for a in result)


class TestAnomalyCityAndHourlySkips:
    def test_hourly_std_zero(self):
        """Covers branch where std <= 0 for hourly."""
        df = pd.DataFrame(
            [
                {
                    "hour": h,
                    "city": "Tehran",
                    "call_type": "voice",
                    "voice_bearer": "VoLTE",
                    "tech": "4G",
                    "record_id": f"r{i}",
                }
                for h in range(24)
                for i in range(5)
            ]
        )
        result = detect_anomalies(df, pd.DataFrame(), {})
        assert not any(a["type"] == "Hourly Traffic" for a in result)

    def test_city_std_zero(self):
        """Covers branch where std <= 0 for city."""
        df = pd.DataFrame(
            [
                {
                    "hour": 0,
                    "city": c,
                    "call_type": "voice",
                    "voice_bearer": "VoLTE",
                    "tech": "4G",
                    "record_id": f"r{i}",
                }
                for c in ["A", "B", "C", "D", "E"]
                for i in range(10)
            ]
        )
        result = detect_anomalies(df, pd.DataFrame(), {})
        assert not any(a["type"] == "City Traffic" for a in result)

    def test_too_few_hours_skips_hourly(self):
        """Covers len(hourly) <= 3 branch."""
        df = pd.DataFrame(
            [
                {
                    "hour": h,
                    "city": "Tehran",
                    "call_type": "voice",
                    "voice_bearer": "VoLTE",
                    "tech": "4G",
                    "record_id": f"r{i}",
                }
                for h in range(2)
                for i in range(10)
            ]
        )
        result = detect_anomalies(df, pd.DataFrame(), {})
        assert not any(a["type"] == "Hourly Traffic" for a in result)


# ==================================================================
# radar/services/pdf.py
# ==================================================================
class TestPdfWithoutReportlab:
    def test_module_reload_without_reportlab(self, monkeypatch):
        """Covers the ImportError branch at module top."""
        import builtins

        real_import = builtins.__import__

        def blocked_import(name, *args, **kwargs):
            if name == "reportlab" or name.startswith("reportlab."):
                raise ImportError(f"mocked: {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocked_import)

        # Save and remove any cached pdf module
        saved = sys.modules.pop("radar.services.pdf", None)
        try:
            fresh = importlib.import_module("radar.services.pdf")
            assert fresh.HAS_PDF is False
            # build_pdf returns None when reportlab is missing
            assert fresh.build_pdf("T", [{"text": "x"}]) is None
        finally:
            if saved is not None:
                sys.modules["radar.services.pdf"] = saved


class TestPdfEmptySectionsWithReportlab:
    @pytest.mark.skipif(not pdf_module.HAS_PDF, reason="reportlab not installed")
    def test_pdf_with_empty_table_rows(self):
        """Covers the branch where table has no rows."""
        empty_df = pd.DataFrame({"col": []})
        sections = [
            {"heading": "Empty", "table": empty_df},
        ]
        out = pdf_module.build_pdf("Title", sections)
        assert out is not None
        assert out[:5] == b"%PDF-"

    @pytest.mark.skipif(not pdf_module.HAS_PDF, reason="reportlab not installed")
    def test_pdf_with_only_heading(self):
        sections = [{"heading": "Just heading"}]
        out = pdf_module.build_pdf("T", sections)
        assert out is not None

    @pytest.mark.skipif(not pdf_module.HAS_PDF, reason="reportlab not installed")
    def test_pdf_with_only_text(self):
        sections = [{"text": "Just text, no heading"}]
        out = pdf_module.build_pdf("T", sections)
        assert out is not None


# ==================================================================
# telecom_attack.py — exception paths
# ==================================================================
class TestAttackExceptionPaths:
    def test_inject_with_alerts(self, attack_db):
        """Happy path: inject_attack_alerts writes alerts + sms rows."""
        from attack_core import attacks_to_alerts, expand_events

        s = telecom_attack.generate_attack_scenarios(5)
        e = expand_events(s)
        alerts = attacks_to_alerts(s, e)
        assert alerts

        telecom_attack.inject_attack_alerts(alerts)

        con = sqlite3.connect(str(attack_db))
        n = con.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        con.close()
        assert n == len(alerts)


# ==================================================================
# attack_core.py — branch at 316->319
# ==================================================================
class TestAttackCoreBranches:
    def test_attacks_to_alerts_empty_interesting(self):
        """Covers branch when no scenarios qualify."""
        scenarios = [
            {
                "scenario_id": "x",
                "name": "x",
                "attack_type": "X",
                "target_layer": "X",
                "target_node": "x",
                "target_iface": "x",
                "protocol": "x",
                "severity": "LOW",
                "start_ts": "x",
                "end_ts": "x",
                "duration_sec": 1,
                "rate_pps": 1,
                "total_events": 1,
                "source_ip": "1",
                "mitre": "x",
                "status": "BLOCKED",
                "notes": "",
            },
        ]
        alerts = attack_core.attacks_to_alerts(scenarios, [])
        assert alerts == []

    def test_attacks_to_alerts_overflow_30(self):
        """Covers interesting[:30] slicing."""
        scenarios = [
            {
                "scenario_id": f"s{i}",
                "name": "x",
                "attack_type": "X",
                "target_layer": "X",
                "target_node": "x",
                "target_iface": "x",
                "protocol": "x",
                "severity": "MEDIUM",
                "start_ts": "x",
                "end_ts": "x",
                "duration_sec": 1,
                "rate_pps": 1,
                "total_events": 1,
                "source_ip": "1",
                "mitre": "x",
                "status": "DETECTED",
                "notes": "",
            }
            for i in range(50)
        ]
        alerts = attack_core.attacks_to_alerts(scenarios, [])
        assert len(alerts) == 30

    def test_attacks_to_alerts_unknown_severity(self):
        """Covers sev_map.get default when severity is odd."""
        scenarios = [
            {
                "scenario_id": "x",
                "name": "x",
                "attack_type": "X",
                "target_layer": "X",
                "target_node": "x",
                "target_iface": "x",
                "protocol": "x",
                "severity": "UNKNOWN",
                "start_ts": "x",
                "end_ts": "x",
                "duration_sec": 1,
                "rate_pps": 1,
                "total_events": 1,
                "source_ip": "1",
                "mitre": "x",
                "status": "DETECTED",
                "notes": "",
            },
        ]
        alerts = attack_core.attacks_to_alerts(scenarios, [])
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "MEDIUM"
