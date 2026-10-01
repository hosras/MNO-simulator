# TELECOM-NET-SIM

> Fully local mobile network simulator with OSINT/SIGINT analytics,
> attack scenario generation, and three Streamlit dashboards.

**Zero external network calls. All data is generated locally and stored
in a single SQLite file.**

Streamlit telemetry is **disabled** via `.streamlit/config.toml`
(`gatherUsageStats = false`, `address = "127.0.0.1"`). The dashboards
bind to loopback only - no LAN or internet exposure.

*This README is auto-generated. Regenerate with:* `python generate_readme.py`

## Features

### Simulation
- Multi-technology topology: **2G / 3G / 4G / 5G / 6G** (sub-THz + mmWave)
- 10 Iranian cities weighted by population
- 5,000 subscribers with special-line classes (VIP / Government / Corporate / Emergency / Test)
- 60,000 CDRs across voice / SMS / MMS / data / USSD / RCS
- Voice bearers: VoLTE / VoWiFi / VoNR / Vo6G / CSFB
- End-to-end encryption simulation (5 cipher suites, incl. Kyber-1024)

### Analysis
- **OSINT**: public cell registry, social complaints, sentiment
- **SIGINT**: IMEI churn, SIM-box, impossible-travel, weak cells,
  CLIR abuse, filter-bypass users, MMS abuse
- **Encryption coverage** by line class + failure tracking
- **Alert engine** with 9 rule classes -> SMS dispatch to SOC

### Attack Simulator
- 23 attack types across SS7 / Diameter / GTP / PFCP / SIP / HTTP2 / O-RAN / 6G
- MTTD / MTTR simulation
- Persists scenarios + events + alerts to the same DB

### Dashboards
1. `telecom_dashboard.py` - operations dashboard
2. `telecom_radar.py`     - statistical analytics + PDF export
3. `telecom_admin.py`     - CRUD + audit log + backup / restore

Shared helpers: `telecom_ui_common.py` (Streamlit + Plotly).

---

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux / macOS

pip install -r requirements.txt
```

---

## Usage

### 1. Generate the dataset

```bash
python telecom_net_sim.py
```

Outputs `telecom_sim_output/telecom_sim.db`, `report.txt`, and 10 PNG charts.

### 2. Run the attack simulator (optional)

```bash
python telecom_attack.py
```

### 3. Open a dashboard

```bash
streamlit run telecom_dashboard.py
streamlit run telecom_radar.py
streamlit run telecom_admin.py
```

All three bind to `127.0.0.1` by default (see `.streamlit/config.toml`).

### 4. Restore the 2 PB traffic figure (display only)

```bash
python restore_2pb.py
```

Scales `SUM(bytes)` for display only. The DB does **not** physically
hold 2 PB.

---

## Modules

| Module | Lines | Public | Private | Classes | Description |
|---|---:|---:|---:|---:|---|
| `telecom_admin.py` | 1,164 | 11 | 0 | 0 | TELECOM Admin Panel v2.0 — full CRUD + audit + backup (see common.py) |
| `telecom_attack.py` | 548 | 7 | 2 | 0 | TELECOM-ATTACK-SIM v1.0 |
| `telecom_common.py` | 152 | 14 | 1 | 0 | TELECOM-NET-SIM | Common Utilities v1.0 (shared across modules) |
| `telecom_dashboard.py` | 1,318 | 1 | 0 | 0 | TELECOM-NET-SIM | Dashboard v3.0 (Streamlit) |
| `telecom_net_sim.py` | 1,317 | 17 | 0 | 3 | TELECOM-NET-SIM v3.0 |
| `telecom_radar.py` | 1,640 | 1 | 0 | 0 | TELECOM RADAR v2.0 |
| `telecom_ui_common.py` | 136 | 5 | 0 | 0 | Shared Streamlit + Plotly helpers used by dashboard and radar. |

---

## Testing

**27 tests** across 4 files.

```bash
pytest              # fast tests (unit + smoke + db)
pytest --run-slow   # also runs the full simulator end-to-end
```

| File | Tests | Test classes |
|---|---:|---:|
| `tests/test_db.py` | 5 | 2 |
| `tests/test_integration.py` | 1 | 0 |
| `tests/test_smoke.py` | 2 | 0 |
| `tests/test_unit.py` | 19 | 6 |

---

## Dependencies

Version-constrained in `requirements.txt`:

```
pandas>=2.0,<3.0
streamlit>=1.30,<2.0
plotly>=5.18,<6.0
matplotlib>=3.7,<4.0
pytest>=7.4,<9.0
```

---

## Windows Launchers

| Script | Purpose |
|---|---|
| `menu.bat` | Interactive menu |
| `rebuild.bat` | Full rebuild from scratch |
| `reset_admin.bat` | Reset admin password |
| `restore.bat` | Restore DB from a backup |
| `run_all.bat` | Run simulator + attack + dashboards |
| `snapshot.bat` | Quick read-only snapshot |
| `stop_all.bat` | Stop all Streamlit processes |

---

## Data & Artifacts

Generated at runtime - nothing is committed to version control.

| Path | Purpose |
|---|---|
| `telecom_sim_output/telecom_sim.db` | SQLite database (main store) |
| `telecom_sim_output/report.txt` | Textual summary |
| `telecom_sim_output/*.png` | 10 charts |
| `telecom_sim_output/backups/` | Internal SQLite backups |

WAL sidecar files (`telecom_sim.db-wal`, `telecom_sim.db-shm`) are
created by SQLite during writes and are handled automatically by the
backup API.

Recommended `.gitignore` entries:

```
.venv/
__pycache__/
telecom_sim_output/
*.zip
*.pdf
*.pyc
```

---

## Design Notes

### Why local-only?
No network calls anywhere. All data comes from a seeded RNG
(`SEED = 1403` in `telecom_net_sim.py`). Runs are reproducible and
tests are hermetic. Streamlit telemetry is disabled.

### Why SQLite?
Single-file DB, zero setup, easy backup / restore, portable.

### Why `main()` guards in every Streamlit module?
Streamlit scripts execute top-to-bottom on every rerun. Without a
guard, `import telecom_*` would run the whole UI. Each module
defines a `main()` and ends with a guard that runs it only when
executed under `streamlit run` or as `__main__`. This makes every
module both a script and a library.

### Why SQLite's online backup API?
`shutil.copy2` on a WAL-mode DB copies only `.db`, not the pending
`-wal`. The backup can be inconsistent. `sqlite3.Connection.backup()` produces a consistent snapshot even
while writers are active.

---

## Known Limitations

- The attack simulator is **defensive-only**: no packets leave the host.
- `restore_2pb.py` scales `SUM(bytes)` for display only; the DB does
  **not** physically hold 2 PB.
- Streamlit dashboards are read-only; all writes go through the admin panel.
- No CI configured. Add `.github/workflows/ci.yml` running
  `pytest --run-slow` to enable.
- `test_db.py` and `test_unit.py::TestPickTarget` require
  `telecom_sim_output/telecom_sim.db` to exist; run
  `python telecom_net_sim.py` first if they skip.

---

*Generated 2026-10-01 by `generate_readme.py`.*
