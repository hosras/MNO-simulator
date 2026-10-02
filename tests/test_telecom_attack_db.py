"""Tests for the DB layer of telecom_attack.py.

We monkeypatch telecom_attack.db_connect to point at a temp SQLite DB,
so the real project DB is never touched.
"""

import sqlite3

import pytest

import telecom_attack


# ------------------------------------------------------------------
# Fixture: isolated DB with prerequisite tables
# ------------------------------------------------------------------
@pytest.fixture
def attack_db(tmp_path, monkeypatch):
    db_path = tmp_path / "attack_test.db"

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
    cur.executemany(
        "INSERT INTO cores VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("HSS-01", "HSS-A", "HSS", "4G/5G", "Tehran", 100000),
            ("AMF-01", "AMF-A", "AMF", "5G", "Tehran", 100000),
            ("SMF-01", "SMF-A", "SMF", "5G", "Tehran", 100000),
            ("UPF-01", "UPF-A", "UPF", "5G", "Tehran", 100000),
            ("MME-01", "MME-A", "MME", "4G", "Tehran", 100000),
            ("SGW-01", "SGW-A", "SGW", "4G", "Tehran", 100000),
            ("PGW-01", "PGW-A", "PGW", "4G", "Tehran", 100000),
            ("MSC-01", "MSC-A", "MSC", "2G/3G", "Tehran", 100000),
            ("IMS-01", "IMS-A", "IMS", "VoLTE", "Tehran", 100000),
            ("NWDAF-01", "NWDAF-A", "NWDAF", "6G", "Tehran", 100000),
            ("RIS-C-01", "RIS-A", "RIS-C", "6G", "Tehran", 100000),
            ("ISAC-01", "ISAC-A", "ISAC", "6G", "Tehran", 100000),
            ("AI-RAN-01", "AIRAN-A", "AI-RAN", "6G", "Tehran", 100000),
        ],
    )
    cur.executemany(
        "INSERT INTO cells VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("5G-TEH-0001", "cell5g-1", "5G", "Tehran", 35.7, 51.4, "NR-n78", 0, 4, 40, 100),
            ("5G-TEH-0002", "cell5g-2", "5G", "Tehran", 35.7, 51.4, "NR-n78", 0, 4, 40, 100),
            ("6G-TEH-0001", "cell6g-1", "6G", "Tehran", 35.7, 51.4, "THz-140", 0, 4, 40, 100),
        ],
    )
    con.commit()
    con.close()

    yield db_path


def _count(db_path, table):
    con = sqlite3.connect(str(db_path))
    try:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        con.close()


# ==================================================================
# init_attack_tables
# ==================================================================
class TestInitAttackTables:
    def test_creates_attack_scenarios(self, attack_db):
        telecom_attack.init_attack_tables()
        con = sqlite3.connect(str(attack_db))
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        con.close()
        assert "attack_scenarios" in names
        assert "attack_events" in names

    def test_idempotent(self, attack_db):
        telecom_attack.init_attack_tables()
        telecom_attack.init_attack_tables()


# ==================================================================
# _build_target_index
# ==================================================================
class TestBuildTargetIndex:
    def test_reads_cores(self, attack_db):
        idx = telecom_attack._build_target_index()
        assert "HSS-01" in idx["cores"]["HSS"]
        assert "AMF-01" in idx["cores"]["AMF"]
        assert len(idx["all_cores"]) >= 5

    def test_reads_5g_cells(self, attack_db):
        idx = telecom_attack._build_target_index()
        assert "5G-TEH-0001" in idx["cells_5g"]

    def test_reads_6g_cells(self, attack_db):
        idx = telecom_attack._build_target_index()
        assert "6G-TEH-0001" in idx["cells_6g"]

    def test_db_error_returns_empty(self, monkeypatch):
        def bad_connect():
            raise RuntimeError("db down")

        monkeypatch.setattr(telecom_attack, "db_connect", bad_connect)
        idx = telecom_attack._build_target_index()
        assert idx["all_cores"] == []
        assert idx["cells_5g"] == []
        assert idx["cells_6g"] == []


# ==================================================================
# generate_attack_scenarios
# ==================================================================
class TestGenerateAttackScenarios:
    def test_returns_n_scenarios(self, attack_db):
        s = telecom_attack.generate_attack_scenarios(10)
        assert len(s) == 10

    def test_all_have_known_targets(self, attack_db):
        s = telecom_attack.generate_attack_scenarios(15)
        for sc in s:
            assert sc["target_node"] != "UNKNOWN"

    def test_inits_tables(self, attack_db):
        telecom_attack.generate_attack_scenarios(3)
        con = sqlite3.connect(str(attack_db))
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        con.close()
        assert "attack_scenarios" in names


# ==================================================================
# persist_attacks
# ==================================================================
class TestPersistAttacks:
    def test_writes_scenarios_and_events(self, attack_db):
        from attack_core import expand_events

        scenarios = telecom_attack.generate_attack_scenarios(5)
        events = expand_events(scenarios, samples_per_scenario=3)
        telecom_attack.persist_attacks(scenarios, events)
        assert _count(attack_db, "attack_scenarios") == 5
        assert _count(attack_db, "attack_events") == 15

    def test_wipes_previous_run(self, attack_db):
        from attack_core import expand_events

        s1 = telecom_attack.generate_attack_scenarios(3)
        e1 = expand_events(s1)
        telecom_attack.persist_attacks(s1, e1)

        s2 = telecom_attack.generate_attack_scenarios(7)
        e2 = expand_events(s2)
        telecom_attack.persist_attacks(s2, e2)

        assert _count(attack_db, "attack_scenarios") == 7

    def test_empty_input(self, attack_db):
        telecom_attack.persist_attacks([], [])
        assert _count(attack_db, "attack_scenarios") == 0


# ==================================================================
# inject_attack_alerts
# ==================================================================
class TestInjectAttackAlerts:
    def test_writes_alerts_and_sms(self, attack_db):
        from attack_core import attacks_to_alerts, expand_events

        s = telecom_attack.generate_attack_scenarios(10)
        e = expand_events(s)
        alerts = attacks_to_alerts(s, e)
        telecom_attack.inject_attack_alerts(alerts)

        n_a = _count(attack_db, "alerts")
        n_s = _count(attack_db, "sms_alerts")
        assert n_a == len(alerts)
        assert n_s == len(alerts)

    def test_empty_list_noop(self, attack_db):
        telecom_attack.inject_attack_alerts([])
        assert _count(attack_db, "alerts") == 0

    def test_replaces_previous_attack_alerts(self, attack_db):
        from attack_core import attacks_to_alerts, expand_events

        s1 = telecom_attack.generate_attack_scenarios(10)
        e1 = expand_events(s1)
        a1 = attacks_to_alerts(s1, e1)
        telecom_attack.inject_attack_alerts(a1)

        s2 = telecom_attack.generate_attack_scenarios(3)
        e2 = expand_events(s2)
        a2 = attacks_to_alerts(s2, e2)
        telecom_attack.inject_attack_alerts(a2)

        # Should equal len(a2), not len(a1) + len(a2)
        assert _count(attack_db, "alerts") == len(a2)


# ==================================================================
# run_attack_simulation
# ==================================================================
class TestRunAttackSimulation:
    def test_summary_shape(self, attack_db):
        summary = telecom_attack.run_attack_simulation(
            n_scenarios=5,
            samples_per_scenario=3,
        )
        for key in ("scenarios", "events", "alerts", "by_status", "by_severity"):
            assert key in summary
        assert summary["scenarios"] == 5
        assert summary["events"] == 15

    def test_by_status_sums(self, attack_db):
        summary = telecom_attack.run_attack_simulation(10, 5)
        assert sum(summary["by_status"].values()) == 10
        assert sum(summary["by_severity"].values()) == 10

    def test_no_inject(self, attack_db):
        summary = telecom_attack.run_attack_simulation(
            n_scenarios=3,
            samples_per_scenario=2,
            inject_alerts=False,
        )
        assert summary["scenarios"] == 3
        assert _count(attack_db, "alerts") == 0

    def test_prints_progress(self, attack_db, capsys):
        telecom_attack.run_attack_simulation(2, 2)
        out = capsys.readouterr().out
        assert "[ATTACK]" in out
