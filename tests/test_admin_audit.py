"""Unit tests for admin.services.audit and admin.services.db."""

import pytest

import admin.services.audit as audit_module
import admin.services.db as db_module


# ==================================================================
# audit.py — init_audit
# ==================================================================
class TestInitAudit:
    def test_calls_db_exec_once(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            audit_module,
            "db_exec",
            lambda sql, *a, **k: calls.append(sql),
        )
        audit_module.init_audit()
        assert len(calls) == 1

    def test_creates_audit_log_table(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            audit_module,
            "db_exec",
            lambda sql, *a, **k: calls.append(sql),
        )
        audit_module.init_audit()
        assert "CREATE TABLE IF NOT EXISTS audit_log" in calls[0]

    def test_schema_includes_expected_columns(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            audit_module,
            "db_exec",
            lambda sql, *a, **k: calls.append(sql),
        )
        audit_module.init_audit()
        sql = calls[0]
        for col in ("id", "ts", "user", "action", "entity", "entity_id", "details"):
            assert col in sql


# ==================================================================
# audit.py — log_audit
# ==================================================================
class TestLogAudit:
    def test_inserts_row(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            audit_module,
            "db_exec",
            lambda sql, params=(), **k: calls.append((sql, params)),
        )
        monkeypatch.setattr(audit_module, "current_user", lambda: "alice")
        audit_module.log_audit("LOGIN", "system", "-", "successful")
        assert len(calls) == 1
        sql, params = calls[0]
        assert sql.startswith("INSERT INTO audit_log")
        assert "alice" in params
        assert "LOGIN" in params

    def test_default_details_empty(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            audit_module,
            "db_exec",
            lambda sql, params=(), **k: calls.append((sql, params)),
        )
        monkeypatch.setattr(audit_module, "current_user", lambda: "bob")
        audit_module.log_audit("LOGOUT", "system", "-")
        _, params = calls[0]
        assert "" in params

    def test_entity_id_is_stringified(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            audit_module,
            "db_exec",
            lambda sql, params=(), **k: calls.append((sql, params)),
        )
        monkeypatch.setattr(audit_module, "current_user", lambda: "admin")
        audit_module.log_audit("DELETE", "subscriber", 12345)
        _, params = calls[0]
        assert "12345" in params

    def test_timestamp_format(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            audit_module,
            "db_exec",
            lambda sql, params=(), **k: calls.append((sql, params)),
        )
        monkeypatch.setattr(audit_module, "current_user", lambda: "x")
        audit_module.log_audit("ACT", "ent", "id")
        _, params = calls[0]
        # Timestamp is first param
        ts = params[0]
        assert len(ts) == 19  # YYYY-MM-DD HH:MM:SS
        assert ts[4] == "-" and ts[7] == "-"


# ==================================================================
# db.py — re-exports
# ==================================================================
class TestDbModuleReexports:
    def test_reexports_db_df(self):
        assert db_module.db_df is not None

    def test_reexports_db_exec(self):
        assert db_module.db_exec is not None

    def test_reexports_db_one(self):
        assert db_module.db_one is not None

    def test_reexports_db_count(self):
        assert db_module.db_count is not None

    def test_reexports_db_chunked_in_update(self):
        assert db_module.db_chunked_in_update is not None

    def test_all_exports_defined(self):
        expected = {
            "db_df",
            "db_exec",
            "db_one",
            "db_count",
            "db_chunked_in_update",
        }
        assert set(db_module.__all__) == expected
