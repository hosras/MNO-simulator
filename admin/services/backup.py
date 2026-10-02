# -*- coding: utf-8 -*-
"""SQLite backup / restore / list — free of Streamlit imports.

These functions are pure w.r.t. Streamlit: they only touch the
filesystem and SQLite. This makes them unit-testable without
running a Streamlit runtime.

Public API:
    create_backup(label="auto") -> str        # absolute path
    list_backups() -> list[str]               # filenames, newest first
    restore_backup(filename) -> str           # absolute path
"""
import os
import sqlite3
from datetime import datetime

from telecom_common import DB_PATH
from admin._config import BACKUP_DIR

os.makedirs(BACKUP_DIR, exist_ok=True)


def create_backup(label: str = "auto") -> str:
    """Create a WAL-consistent snapshot of the SQLite DB.

    Uses sqlite3's online backup API instead of shutil.copy2 so that
    any data still sitting in the -wal file is included. Do NOT swap
    this back to a plain file copy while journal_mode=WAL is active.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    os.makedirs(BACKUP_DIR, exist_ok=True)

    safe_label = "".join(
        ch for ch in str(label) if ch.isalnum() or ch in "-_"
    ) or "auto"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = os.path.join(BACKUP_DIR, f"backup_{safe_label}_{ts}.db")

    src = sqlite3.connect(DB_PATH)
    try:
        dst = sqlite3.connect(fn)
        try:
            src.backup(dst)  # atomic, WAL-aware snapshot
            chk = dst.execute("PRAGMA quick_check").fetchone()
            if not chk or chk[0] != "ok":
                raise RuntimeError(f"Backup integrity check failed: {chk}")
        finally:
            dst.close()
    finally:
        src.close()

    return os.path.abspath(fn)


def list_backups() -> list:
    """Return backup filenames (newest first)."""
    if not os.path.isdir(BACKUP_DIR):
        return []
    return sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")],
        reverse=True,
    )


def restore_backup(backup_filename: str) -> str:
    """Atomically restore a backup into the live DB.

    - Verifies the backup file's integrity before touching anything.
    - Uses sqlite3's backup API (WAL-aware) to overwrite the live DB.
    - Removes stale -wal / -shm sidecar files.
    - Refuses to run if the backup path escapes BACKUP_DIR.

    Returns the absolute path of the restored backup on success.
    Raises RuntimeError on any failure (caller should catch and st.error).
    """
    # ---- 1) Path safety: never trust caller-supplied filenames ----
    if not isinstance(backup_filename, str) or not backup_filename:
        raise RuntimeError("Invalid backup filename.")
    if os.path.basename(backup_filename) != backup_filename:
        raise RuntimeError("Backup filename must not contain path separators.")

    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    if not os.path.isfile(backup_path):
        raise RuntimeError(f"Backup not found: {backup_filename}")
    if not os.path.isfile(DB_PATH):
        raise RuntimeError(f"Live DB not found: {DB_PATH}")

    # ---- 2) Verify the backup before we destroy the live DB ----
    try:
        chk_con = sqlite3.connect(backup_path)
        try:
            res = chk_con.execute("PRAGMA quick_check").fetchone()
        finally:
            chk_con.close()
    except sqlite3.DatabaseError as e:
        raise RuntimeError(f"Backup is not a valid SQLite DB: {e}")

    if not res or res[0] != "ok":
        raise RuntimeError(f"Backup integrity check failed: {res}")

    # ---- 3) Copy the backup INTO the live DB (atomic, WAL-aware) ----
    src = sqlite3.connect(backup_path)
    try:
        dst = sqlite3.connect(DB_PATH)
        try:
            dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            src.backup(dst)
            dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            dst.close()
    finally:
        src.close()

    # ---- 4) Remove stale sidecar files left over from before ----
    for suffix in ("-wal", "-shm"):
        side = DB_PATH + suffix
        if os.path.exists(side):
            try:
                os.remove(side)
            except OSError:
                pass

    return os.path.abspath(backup_path)