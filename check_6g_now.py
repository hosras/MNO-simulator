# -*- coding: utf-8 -*-
"""6G presence check across DB."""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB   = BASE / "telecom_sim_output" / "telecom_sim.db"

print("=" * 60)
print(" 6G PRESENCE CHECK")
print("=" * 60)

if not DB.exists():
    print(f"[X] DB not found: {DB}")
    raise SystemExit(1)

con = sqlite3.connect(str(DB))
cur = con.cursor()

def q(sql):
    try:
        return cur.execute(sql).fetchone()[0]
    except Exception as e:
        return f"ERR: {e}"

n_cells_6g  = q("SELECT COUNT(*) FROM cells WHERE tech='6G'")
n_cores_6g  = q("SELECT COUNT(*) FROM cores WHERE tech='6G'")
n_vo6g      = q("SELECT COUNT(*) FROM cdrs WHERE voice_bearer='Vo6G'")
n_cdrs_6g   = q("SELECT COUNT(*) FROM cdrs WHERE tech='6G'")
n_atk_6g    = q("SELECT COUNT(*) FROM attack_scenarios WHERE target_layer='6G'")
total_bytes = q("SELECT SUM(bytes) FROM cdrs") or 0

print()
print("[1] Database")
print(f"  Cells (tech=6G)              : {n_cells_6g}")
print(f"  Core nodes (tech=6G)         : {n_cores_6g}")
print(f"  Vo6G voice calls             : {n_vo6g}")
print(f"  CDRs on 6G cells             : {n_cdrs_6g}")
print(f"  6G attack scenarios          : {n_atk_6g}")
print(f"  Total traffic                : {total_bytes/1e15:.2f} PB")

rows = cur.execute(
    "SELECT cell_id, city, band FROM cells WHERE tech='6G' LIMIT 5"
).fetchall()
if rows:
    print()
    print("  Sample 6G cells:")
    for r in rows:
        print(f"    - {r[0]:<18} {r[1]:<10} {r[2]}")

rows = cur.execute(
    "SELECT attack_type, severity, status FROM attack_scenarios "
    "WHERE target_layer='6G'"
).fetchall()
if rows:
    print()
    print("  Sample 6G attacks:")
    for r in rows:
        print(f"    - {r[0]:<22} {r[1]:<9} {r[2]}")

con.close()

print()
print("=" * 60)
ok = (isinstance(n_cells_6g, int) and n_cells_6g > 0
      and isinstance(n_vo6g, int) and n_vo6g > 0)
print(f" RESULT: 6G is {'PRESENT' if ok else 'MISSING'} in DB")
print("=" * 60)
