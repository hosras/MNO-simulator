"""Unit tests for admin.services.backup — no Streamlit, no real DB.

We monkeypatch DB_PATH and BACKUP_DIR to point at pytest's tmp_path,
so the real project DB is never touched.
"""

import os
import sqlite3

import pytest

import admin.services.backup as backup_module
from admin.services.backup import (
    create_backup,
    list_backups,
    restore_backup,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Redirect DB_PATH + BACKUP_DIR to tmp_path."""
    db_path = tmp_path / "test.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    monkeypatch.setattr(backup_module, "DB_PATH", str(db_path))
    monkeypatch.setattr(backup_module, "BACKUP_DIR", str(backup_dir))

    return {"db": db_path, "backups": backup_dir}


def _make_valid_db(path):
    """Create a tiny valid SQLite DB."""
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO t (v) VALUES ('hello')")
    con.commit()
    con.close()


def _make_invalid_file(path):
    """Create a file that isn't a valid SQLite DB."""
    path.write_bytes(b"this is definitely not sqlite")


# ==================================================================
# create_backup
# ==================================================================
class TestCreateBackup:
    def test_creates_file(self, isolated):
        _make_valid_db(isolated["db"])
        p = create_backup("test")
        assert os.path.isfile(p)
        assert p.endswith(".db")

    def test_returns_absolute_path(self, isolated):
        _make_valid_db(isolated["db"])
        p = create_backup("test")
        assert os.path.isabs(p)

    def test_label_appears_in_filename(self, isolated):
        _make_valid_db(isolated["db"])
        p = create_backup("mylabel")
        assert "mylabel" in os.path.basename(p)

    def test_unsafe_label_is_sanitised(self, isolated):
        _make_valid_db(isolated["db"])
        # Path separators etc. must not leak into the filename.
        p = create_backup("../../etc/passwd")
        base = os.path.basename(p)
        assert ".." not in base
        assert "/" not in base
        assert "\\" not in base

    def test_missing_db_raises(self, isolated):
        with pytest.raises(FileNotFoundError):
            create_backup("no_db")

    def test_default_label(self, isolated):
        _make_valid_db(isolated["db"])
        p = create_backup()
        assert "auto" in os.path.basename(p)


# ==================================================================
# list_backups
# ==================================================================
class TestListBackups:
    def test_empty_dir_returns_empty_list(self, isolated):
        assert list_backups() == []

    def test_missing_dir_returns_empty_list(self, isolated, monkeypatch):
        monkeypatch.setattr(
            backup_module,
            "BACKUP_DIR",
            str(isolated["backups"] / "does_not_exist"),
        )
        assert list_backups() == []

    def test_lists_created_backups(self, isolated):
        _make_valid_db(isolated["db"])
        create_backup("a")
        create_backup("b")
        create_backup("c")
        assert len(list_backups()) == 3

    def test_ignores_non_db_files(self, isolated):
        _make_valid_db(isolated["db"])
        create_backup("valid")
        (isolated["backups"] / "notes.txt").write_text("ignore me")
        (isolated["backups"] / "junk.bin").write_bytes(b"\x00\x01")
        assert len(list_backups()) == 1


# ==================================================================
# restore_backup
# ==================================================================
class TestRestoreBackup:
    def test_restores_from_valid_backup(self, isolated):
        _make_valid_db(isolated["db"])
        p = create_backup("snap")
        filename = os.path.basename(p)
        result = restore_backup(filename)
        assert os.path.isabs(result)
        assert os.path.isfile(result)

    def test_rejects_path_traversal_dotdot(self, isolated):
        with pytest.raises(RuntimeError, match="path separators"):
            restore_backup("../evil.db")

    def test_rejects_path_traversal_slash(self, isolated):
        with pytest.raises(RuntimeError, match="path separators"):
            restore_backup("sub/dir/file.db")

    def test_rejects_path_traversal_backslash(self, isolated):
        with pytest.raises(RuntimeError, match="path separators"):
            restore_backup("sub\\dir\\file.db")

    def test_rejects_empty_filename(self, isolated):
        with pytest.raises(RuntimeError, match="Invalid backup filename"):
            restore_backup("")

    def test_rejects_non_string(self, isolated):
        with pytest.raises(RuntimeError, match="Invalid backup filename"):
            restore_backup(None)

    def test_rejects_missing_backup(self, isolated):
        _make_valid_db(isolated["db"])
        with pytest.raises(RuntimeError, match="not found"):
            restore_backup("nonexistent.db")

    def test_rejects_invalid_sqlite_content(self, isolated):
        _make_valid_db(isolated["db"])
        bogus = isolated["backups"] / "bogus.db"
        _make_invalid_file(bogus)
        with pytest.raises(RuntimeError, match="not a valid SQLite DB"):
            restore_backup("bogus.db")

    def test_missing_live_db_raises(self, isolated):
        # Create backup from a valid DB, then delete the live DB.
        _make_valid_db(isolated["db"])
        p = create_backup("snap")
        isolated["db"].unlink()
        with pytest.raises(RuntimeError, match="Live DB not found"):
            restore_backup(os.path.basename(p))
