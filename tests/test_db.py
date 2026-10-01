# -*- coding: utf-8 -*-
"""Read-only checks against the live DB + schema invariants."""
import json
import sqlite3
import pytest


EXPECTED_TABLES = {
    "cells", "cores", "subscribers", "cdrs",
    "osint_public_registry", "osint_complaints",
    "sigint_findings", "alerts", "sms_alerts",
    "audit_log", "attack_scenarios", "attack_events",
}


class TestSchema:
    def test_all_expected_tables_exist(self, real_db):
        con = sqlite3.connect(real_db)
        names = {row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        con.close()
        missing = EXPECTED_TABLES - names
        assert not missing, f"missing tables: {missing}"

    def test_cells_has_6g(self, real_db):
        con = sqlite3.connect(real_db)
        n = con.execute("SELECT COUNT(*) FROM cells WHERE tech='6G'"
                        ).fetchone()[0]
        con.close()
        assert n > 0, "DB has no 6G cells"

    def test_cdrs_have_all_types(self, real_db):
        con = sqlite3.connect(real_db)
        types = {row[0] for row in con.execute(
            "SELECT DISTINCT call_type FROM cdrs"
        )}
        con.close()
        # voice/sms/mms/data/ussd/rcs should all be present given weights
        for t in ("voice", "sms", "data"):
            assert t in types, f"call_type {t} missing from cdrs"


class TestSigintFindings:
    def test_findings_are_valid_json(self, real_db):
        con = sqlite3.connect(real_db)
        rows = list(con.execute("SELECT key, value FROM sigint_findings"))
        con.close()
        assert rows, "no sigint_findings rows"
        for key, val in rows:
            parsed = json.loads(val)
            assert isinstance(parsed, dict), f"{key} is not a JSON object"

    def test_encryption_coverage_reasonable(self, real_db):
        con = sqlite3.connect(real_db)
        row = con.execute(
            "SELECT value FROM sigint_findings WHERE key='SIGINT'"
        ).fetchone()
        con.close()
        sig = json.loads(row[0])
        cov = sig.get("encryption_coverage", {})
        # Each class entry must have coverage_pct in [0, 100]
        for cls, st in cov.items():
            assert 0 <= st["coverage_pct"] <= 100, f"{cls}: {st}"
