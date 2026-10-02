"""Unit tests for telecom_common — password + DB helpers."""

import sqlite3

import pytest

import telecom_common as common
from telecom_common import (
    db_chunked_in_update,
    db_count,
    db_df,
    db_exec,
    db_one,
    has_password,
    set_password,
    verify_password,
)


# ==================================================================
# Password helpers
# ==================================================================
@pytest.fixture
def temp_auth(tmp_path, monkeypatch):
    """Redirect auth file paths to tmp_path."""
    auth_file = tmp_path / ".admin_auth"
    salt_file = tmp_path / ".admin_salt"
    monkeypatch.setattr(common, "_AUTH_FILE", str(auth_file))
    monkeypatch.setattr(common, "_SALT_FILE", str(salt_file))
    monkeypatch.setattr(common, "OUT_DIR", str(tmp_path))
    return {"auth": auth_file, "salt": salt_file}


class TestPasswordFunctions:
    def test_has_password_initially_false(self, temp_auth):
        assert has_password() is False

    def test_has_password_true_after_set(self, temp_auth):
        set_password("mypassword123")
        assert has_password() is True

    def test_set_password_creates_files(self, temp_auth):
        set_password("mypassword123")
        assert temp_auth["auth"].exists()
        assert temp_auth["salt"].exists()

    def test_set_password_creates_out_dir(self, tmp_path, monkeypatch):
        # Non-existent OUT_DIR should be created
        out = tmp_path / "newdir"
        monkeypatch.setattr(common, "_AUTH_FILE", str(out / "a"))
        monkeypatch.setattr(common, "_SALT_FILE", str(out / "s"))
        monkeypatch.setattr(common, "OUT_DIR", str(out))
        set_password("pw")
        assert out.is_dir()

    def test_set_password_different_salt_each_time(self, temp_auth):
        set_password("pw1")
        salt1 = temp_auth["salt"].read_bytes()
        set_password("pw2")
        salt2 = temp_auth["salt"].read_bytes()
        assert salt1 != salt2

    def test_verify_password_correct(self, temp_auth):
        set_password("mypassword123")
        assert verify_password("mypassword123") is True

    def test_verify_password_wrong(self, temp_auth):
        set_password("mypassword123")
        assert verify_password("wrongpassword") is False

    def test_verify_password_no_password_set(self, temp_auth):
        assert verify_password("anything") is False

    def test_verify_password_empty_string(self, temp_auth):
        set_password("mypassword123")
        assert verify_password("") is False

    def test_verify_password_unicode(self, temp_auth):
        set_password("رمز-عبور-۱۲۳")
        assert verify_password("رمز-عبور-۱۲۳") is True

    def test_has_password_missing_salt(self, temp_auth):
        temp_auth["auth"].write_bytes(b"fake")
        assert has_password() is False

    def test_has_password_missing_auth(self, temp_auth):
        temp_auth["salt"].write_bytes(b"fake")
        assert has_password() is False

    def test_verify_password_handles_scrypt_failure(self, temp_auth, monkeypatch):
        set_password("pw")

        # Force scrypt to raise
        def boom(*a, **k):
            raise RuntimeError("scrypt failed")

        monkeypatch.setattr(common, "_scrypt", boom)
        assert verify_password("pw") is False


# ==================================================================
# DB helpers
# ==================================================================
@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "test.db")


class TestDbExec:
    def test_create_and_insert(self, temp_db):
        db_exec("CREATE TABLE t (x INT)", path=temp_db)
        db_exec("INSERT INTO t VALUES (42)", path=temp_db)
        r = db_one("SELECT x FROM t", path=temp_db)
        assert r == (42,)

    def test_exec_with_params(self, temp_db):
        db_exec("CREATE TABLE t (x INT, y TEXT)", path=temp_db)
        db_exec("INSERT INTO t VALUES (?, ?)", (1, "a"), path=temp_db)
        r = db_one("SELECT y FROM t WHERE x=?", (1,), path=temp_db)
        assert r == ("a",)

    def test_exec_invalid_sql_raises(self, temp_db):
        with pytest.raises(sqlite3.OperationalError):
            db_exec("INVALID SQL", path=temp_db)

    def test_exec_uses_wal_mode(self, temp_db):
        db_exec("CREATE TABLE t (x INT)", path=temp_db)
        r = db_one("PRAGMA journal_mode", path=temp_db)
        assert r[0].lower() == "wal"


class TestDbDf:
    def test_returns_dataframe(self, temp_db):
        db_exec("CREATE TABLE t (x INT)", path=temp_db)
        db_exec("INSERT INTO t VALUES (1), (2), (3)", path=temp_db)
        df = db_df("SELECT * FROM t", path=temp_db)
        assert len(df) == 3

    def test_empty_result(self, temp_db):
        db_exec("CREATE TABLE t (x INT)", path=temp_db)
        df = db_df("SELECT * FROM t", path=temp_db)
        assert len(df) == 0

    def test_with_params(self, temp_db):
        db_exec("CREATE TABLE t (x INT)", path=temp_db)
        db_exec("INSERT INTO t VALUES (1), (2), (3)", path=temp_db)
        df = db_df("SELECT * FROM t WHERE x > ?", (1,), path=temp_db)
        assert len(df) == 2


class TestDbOne:
    def test_returns_row(self, temp_db):
        db_exec("CREATE TABLE t (x INT, y TEXT)", path=temp_db)
        db_exec("INSERT INTO t VALUES (1, 'hello')", path=temp_db)
        r = db_one("SELECT x, y FROM t", path=temp_db)
        assert r == (1, "hello")

    def test_returns_none_on_no_result(self, temp_db):
        db_exec("CREATE TABLE t (x INT)", path=temp_db)
        r = db_one("SELECT * FROM t", path=temp_db)
        assert r is None

    def test_with_params(self, temp_db):
        db_exec("CREATE TABLE t (x INT)", path=temp_db)
        db_exec("INSERT INTO t VALUES (5)", path=temp_db)
        r = db_one("SELECT x FROM t WHERE x=?", (5,), path=temp_db)
        assert r == (5,)


class TestDbCount:
    def test_count_existing_table(self, temp_db):
        db_exec("CREATE TABLE t (x INT)", path=temp_db)
        db_exec("INSERT INTO t VALUES (1), (2), (3)", path=temp_db)
        assert db_count("t", path=temp_db) == 3

    def test_count_empty_table(self, temp_db):
        db_exec("CREATE TABLE t (x INT)", path=temp_db)
        assert db_count("t", path=temp_db) == 0

    def test_count_missing_table_returns_zero(self, temp_db):
        assert db_count("nonexistent_table", path=temp_db) == 0

    def test_count_returns_zero_on_error(self, tmp_path):
        # Path inside a directory that doesn't exist → sqlite error
        weird_path = str(tmp_path / "subdir_that_does_not_exist" / "x.db")
        assert db_count("any_table", path=weird_path) == 0


class TestDbChunkedInUpdate:
    def test_update_some_rows(self, temp_db):
        db_exec("CREATE TABLE t (id TEXT, v INT)", path=temp_db)
        for i in range(5):
            db_exec("INSERT INTO t VALUES (?, ?)", (f"id{i}", 0), path=temp_db)
        n = db_chunked_in_update(
            "t",
            "id",
            "v=?",
            [99],
            ["id1", "id2", "id3"],
            path=temp_db,
        )
        assert n == 3
        df = db_df("SELECT * FROM t WHERE v=99", path=temp_db)
        assert len(df) == 3

    def test_empty_values_returns_zero(self, temp_db):
        db_exec("CREATE TABLE t (id TEXT, v INT)", path=temp_db)
        n = db_chunked_in_update("t", "id", "v=?", [99], [], path=temp_db)
        assert n == 0

    def test_chunking_across_boundary(self, temp_db):
        db_exec("CREATE TABLE t (id TEXT, v INT)", path=temp_db)
        for i in range(10):
            db_exec("INSERT INTO t VALUES (?, ?)", (f"id{i}", 0), path=temp_db)
        n = db_chunked_in_update(
            "t",
            "id",
            "v=?",
            [77],
            [f"id{i}" for i in range(10)],
            chunk_size=3,
            path=temp_db,
        )
        assert n == 10
        df = db_df("SELECT * FROM t WHERE v=77", path=temp_db)
        assert len(df) == 10

    def test_multiple_set_values(self, temp_db):
        db_exec("CREATE TABLE t (id TEXT, v INT, w TEXT)", path=temp_db)
        for i in range(3):
            db_exec("INSERT INTO t VALUES (?, ?, ?)", (f"id{i}", 0, "old"), path=temp_db)
        n = db_chunked_in_update(
            "t",
            "id",
            "v=?, w=?",
            [42, "new"],
            ["id0", "id1"],
            path=temp_db,
        )
        assert n == 2
        df = db_df("SELECT * FROM t WHERE v=42", path=temp_db)
        assert len(df) == 2
        assert (df["w"] == "new").all()
