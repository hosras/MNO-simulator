# -*- coding: utf-8 -*-
"""Restore 2 PB total traffic on the current DB.

WARNING: this does NOT create 2 PB of real data.
It scales the `bytes` column in the CDRs table so that SUM(bytes)
reaches ~2 PB for display/reporting purposes. Storage usage on disk
remains unchanged (SQLite pages are rewritten, not grown).
Do not rely on this for capacity planning or billing calculations.
"""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB   = BASE / "telecom_sim_output" / "telecom_sim.db"
TARGET = 2 * 10**15

if not DB.exists():
    raise SystemExit(f"[X] DB not found: {DB}")

con = sqlite3.connect(str(DB))
cur = con.cursor()

cur_sum = cur.execute(
    "SELECT SUM(bytes) FROM cdrs WHERE call_type IN ('data','rcs')"
).fetchone()
current = cur_sum[0] or 0
print(f"[i] Current (data+rcs): {current:,} ({current/1e15:.4f} PB)")

if current <= 0:
    raise SystemExit("[X] No bytes to scale.")

factor = TARGET / current
print(f"[i] Scale factor: {factor:.4f}")

cur.execute("""
    UPDATE cdrs
    SET bytes = CAST(bytes * ? AS INTEGER)
    WHERE call_type IN ('data','rcs')
""", (factor,))
con.commit()

new_total = cur.execute(
    "SELECT SUM(bytes) FROM cdrs WHERE call_type IN ('data','rcs')"
).fetchone()[0]
grand = cur.execute("SELECT SUM(bytes) FROM cdrs").fetchone()[0]
con.close()

print(f"[OK] New (data+rcs): {new_total:,} ({new_total/1e15:.4f} PB)")
print(f"[OK] Grand total:    {grand:,} ({grand/1e15:.4f} PB)")
