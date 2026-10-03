# TELECOM-NET-SIM

[![CI](https://github.com/hosras/MNO-simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/hosras/MNO-simulator/actions/workflows/ci.yml)
[![Docker](https://github.com/hosras/MNO-simulator/actions/workflows/docker.yml/badge.svg)](https://github.com/hosras/MNO-simulator/actions/workflows/docker.yml)
[![Security](https://github.com/hosras/MNO-simulator/actions/workflows/security.yml/badge.svg)](https://github.com/hosras/MNO-simulator/actions/workflows/security.yml)
![Coverage](https://raw.githubusercontent.com/hosras/MNO-simulator/main/.github/coverage.svg)

**Documentation:** [https://docs.sunpannel.ir/](https://docs.sunpannel.ir/)

> Fully local mobile network simulator with OSINT/SIGINT analytics,
> attack scenario generation, and three Streamlit dashboards.

**Zero external network calls. All data is generated locally and stored
in a single SQLite file.**

Streamlit telemetry is **disabled** via `.streamlit/config.toml`
(`gatherUsageStats = false`, `address = "127.0.0.1"`). The dashboards
bind to loopback only - no LAN or internet exposure.

*This README is auto-generated. Regenerate with:* `python generate_readme.py`

## Architecture

The project is split into thin **entry-point shims** at the repo root
and the actual implementation lives in three self-contained packages.
This keeps diffs small, enables isolated testing, and lets each
dashboard ship independently.

```
MNO-simulator/
├── telecom_net_sim.py       # CLI simulator   (top-level module)
├── telecom_attack.py        # attack orchestrator (DB layer)
├── attack_core.py           # pure attack logic (no DB, unit-testable)
├── telecom_common.py        # shared utilities + schema
├── telecom_ui_common.py     # Streamlit + Plotly helpers
├── telecom_logging.py       # centralized logging
│
├── telecom_dashboard.py     # shim -> dashboard.main
├── telecom_admin.py         # shim -> admin.main
├── telecom_radar.py         # shim -> radar.main
│
├── dashboard/               # operations dashboard
│   ├── main.py
│   ├── services/  (data, styles, ui)
│   └── views/     (13 tabs)
│
├── admin/                   # CRUD + audit + backup
│   ├── main.py
│   ├── services/  (auth, audit, backup, db, rate_limit)
│   └── views/     (9 tabs)
│
├── radar/                   # statistical analytics
│   ├── main.py
│   ├── services/  (anomaly, pdf, period, ui)
│   └── views/     (14 tabs)
│
├── tests/                   # pytest suite
│   └── benchmarks/          # pytest-benchmark (14 benchmarks)
│
└── .github/workflows/       # 5 workflows (CI, Docker, Docs, Security)
```

### Why this split?

- **Small diffs**: editing one tab changes one small file, not a 1,300-line one.
- **Testable**: services (`anomaly`, `backup`, `pdf`, `period`) have no
  Streamlit import — they can be unit-tested without a runtime.
- **Backward compatible**: `streamlit run telecom_dashboard.py` still
  works exactly as before.

---

## Features

### Simulation
- Multi-technology topology: **2G / 3G / 4G / 5G / 6G** (sub-THz + mmWave)
- 10 Iranian cities weighted by population
- Configurable subscriber count (default 5,000) and CDR count (default 60,000)
- Special-line classes: VIP / Government / Corporate / Emergency / Test
- Voice bearers: VoLTE / VoWiFi / VoNR / Vo6G / CSFB
- Messaging: SMS / MMS / RCS
- End-to-end encryption simulation (5 cipher suites, incl. Kyber-1024)

### Analysis
- **OSINT**: public cell registry, social complaints, sentiment
- **SIGINT**: IMEI churn, SIM-box, impossible-travel, weak cells,
  CLIR abuse, filter-bypass users, MMS abuse
- **Encryption coverage** by line class + failure tracking
- **Alert engine** with 9 rule classes -> SMS dispatch to SOC

### Attack Simulator
- 24 attack types across SS7 / Diameter / GTP / PFCP / SIP / HTTP2
  / O-RAN / 6G (RIS, ISAC, AI-RAN, THz, QUIC)
- MTTD / MTTR simulation
- Persists scenarios + events + alerts to the same DB
- **Pure core** (`attack_core.py`) usable without a DB

### Dashboards
1. `telecom_dashboard.py` - operations dashboard (13 tabs)
2. `telecom_radar.py`     - statistical analytics + anomaly detection
                            + PDF export (14 tabs)
3. `telecom_admin.py`     - CRUD + audit log + backup / restore (9 tabs)

### Quality & Tooling
- **CI** on GitHub Actions (Python 3.11 / 3.12 / 3.13 / 3.14, Linux)
- **282 unit + smoke + integration tests**, runs in <15 s
- **14 performance benchmarks** (pytest-benchmark)
- **~98% coverage** on core services (views excluded)
- **mypy** type checking (Success: 0 issues)
- **ruff** linter + formatter (pre-commit hook)
- **bandit** static security analysis (0 issues)
- **pip-audit** dependency vulnerability scan (0 CVEs)
- **Docker** multi-stage image + docker-compose
- **Centralized logging** with `--verbose` / `--quiet` / `--log-file`
- **Hermetic**: seeded RNG, no external calls, no telemetry

---

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux / macOS

pip install -r requirements.txt
```

For CI or a minimal dev environment, use `requirements-ci.txt`
instead — it only pulls the packages the project actually imports.

---

## Usage

### 1. Generate the dataset

```bash
python telecom_net_sim.py                    # defaults: seed=1403, 5k subs, 60k CDRs
python telecom_net_sim.py --seed 42          # reproducible, different scenario
python telecom_net_sim.py --random-seed      # non-reproducible, fresh every run
python telecom_net_sim.py --subs 500 --cdrs 2000   # fast smoke run
```

Outputs `telecom_sim_output/telecom_sim.db`, `report.txt`, and 10 PNG charts.

### 2. Run the attack simulator (optional)

```bash
python telecom_attack.py
```

Or from Python (pure functions, no DB required):

```python
from attack_core import generate_scenarios, expand_events
idx = {"cores": {"HSS": ["HSS-01"]}, "all_cores": [],
       "cells_5g": [], "cells_6g": ["6G-001"]}
scenarios = generate_scenarios(10, idx)   # no DB, no I/O
events    = expand_events(scenarios, samples_per_scenario=20)
```

### 3. Open a dashboard

```bash
streamlit run telecom_dashboard.py
streamlit run telecom_radar.py
streamlit run telecom_admin.py
```

All three bind to `127.0.0.1` by default (see `.streamlit/config.toml`).
If a port is busy, pass `--server.port 8502`.

### 4. Restore the 2 PB traffic figure (display only)

```bash
python restore_2pb.py
```

Scales `SUM(bytes)` for display only. The DB does **not** physically
hold 2 PB.

---

### Package Layout

| Package | Files | Lines | Purpose |
|---|---:|---:|---|
| *(top-level)* | 10 | 3,622 | Top-level modules (simulator, attack, logging, common) |
| `dashboard/` | 21 | 1,852 | Operations dashboard + OSINT/SIGINT views |
| `admin/` | 19 | 1,527 | CRUD, audit log, backup / restore |
| `radar/` | 23 | 2,620 | Statistical analytics + anomaly detection + PDF |

---

## Modules

| Module | Lines | Public | Private | Classes | Description |
|---|---:|---:|---:|---:|---|
| `telecom_admin.py` | 22 | 0 | 0 | 0 | Backwards-compatible shim. |
| `telecom_attack.py` | 723 | 7 | 2 | 0 | TELECOM-ATTACK-SIM v1.0 |
| `telecom_common.py` | 239 | 14 | 1 | 0 | TELECOM-NET-SIM | Common Utilities v1.0 (shared across modules) |
| `telecom_dashboard.py` | 22 | 0 | 0 | 0 | Backwards-compatible shim. |
| `telecom_logging.py` | 104 | 3 | 1 | 0 | Centralized logging configuration for TELECOM-NET-SIM. |
| `telecom_net_sim.py` | 1,756 | 18 | 0 | 3 | TELECOM-NET-SIM v3.0 |
| `telecom_radar.py` | 22 | 0 | 0 | 0 | Backwards-compatible shim. |
| `telecom_ui_common.py` | 141 | 5 | 0 | 0 | Shared Streamlit + Plotly helpers used by dashboard and radar. |
| `attack_core.py` | 489 | 5 | 0 | 0 | TELECOM-ATTACK-CORE v1.0 |
| `telecom_logging.py` | 104 | 3 | 1 | 0 | Centralized logging configuration for TELECOM-NET-SIM. |
| `dashboard/__init__.py` | 11 | 0 | 0 | 0 | TELECOM Network Dashboard package. |
| `dashboard/_config.py` | 13 | 0 | 0 | 0 | Package-level constants shared by all dashboard modules. |
| `dashboard/main.py` | 164 | 1 | 0 | 0 | Dashboard entry point — sets page config, sidebar, KPI row, tabs. |
| `dashboard/services/__init__.py` | 2 | 0 | 0 | 0 | Non-Streamlit services: data access, filters, styles, UI helpers. |
| `dashboard/services/data.py` | 55 | 3 | 0 | 0 | Data access — cached DB load + filter application. |
| `dashboard/services/styles.py` | 29 | 1 | 0 | 0 | Global CSS — injected once by main(). |
| `dashboard/services/ui.py` | 48 | 3 | 0 | 0 | Small Streamlit UI helpers (KPI card, formatter, page header). |
| `dashboard/views/__init__.py` | 2 | 0 | 0 | 0 | One module per tab. Each exposes render(data, filtered). |
| `dashboard/views/alerts.py` | 182 | 1 | 0 | 0 | Tab 9 — Alert Engine & SMS Notifications. |
| `dashboard/views/attacks.py` | 94 | 1 | 0 | 0 | Tab 12 — Attack Simulation Results. |
| `dashboard/views/encryption.py` | 128 | 1 | 0 | 0 | Tab 8 — End-to-End Encryption. |
| `dashboard/views/network.py` | 56 | 1 | 0 | 0 | Tab 1 — Network Topology & Core Nodes. |
| `dashboard/views/osint.py` | 101 | 1 | 0 | 0 | Tab 5 — OSINT Analysis. |
| `dashboard/views/overview.py` | 88 | 1 | 0 | 0 | Tab 0 — Network Overview (map + tech share + cells per city). |
| `dashboard/views/report.py` | 33 | 1 | 0 | 0 | Tab 11 — Management Report. |
| `dashboard/views/sigint.py` | 120 | 1 | 0 | 0 | Tab 6 — SIGINT Analysis. |
| `dashboard/views/signal.py` | 73 | 1 | 0 | 0 | Tab 3 — Signal Quality (RF layer). |
| `dashboard/views/special_lines.py` | 244 | 1 | 0 | 0 | Tab 7 — Special Lines & Privileged Access. |
| `dashboard/views/subscribers.py` | 62 | 1 | 0 | 0 | Tab 10 — Subscriber Analytics. |
| `dashboard/views/traffic.py` | 91 | 1 | 0 | 0 | Tab 2 — Traffic Analysis (CDR). |
| `dashboard/views/voice_messaging.py` | 256 | 1 | 0 | 0 | Tab 4 — Voice Bearers & Messaging (VoLTE/VoWiFi/VoNR/CSFB + MMS + RCS). |
| `admin/__init__.py` | 10 | 0 | 0 | 0 | TELECOM Admin Panel package. |
| `admin/_config.py` | 23 | 0 | 0 | 0 | Package-level constants shared across admin modules. |
| `admin/main.py` | 243 | 1 | 4 | 0 | Admin panel entry point — login flow + tabs. |
| `admin/services/__init__.py` | 2 | 0 | 0 | 0 | Non-Streamlit services for the admin panel. |
| `admin/services/audit.py` | 27 | 2 | 0 | 0 | Audit log: schema init + append helper. |
| `admin/services/auth.py` | 20 | 3 | 0 | 0 | Session-state helpers for authentication (Streamlit-based). |
| `admin/services/backup.py` | 127 | 3 | 0 | 0 | SQLite backup / restore / list — free of Streamlit imports. |
| `admin/services/db.py` | 12 | 0 | 0 | 0 | Thin wrappers re-exported so views import from one place. |
| `admin/services/rate_limit.py` | 47 | 2 | 0 | 0 | Login rate-limit helpers. |
| `admin/views/__init__.py` | 2 | 0 | 0 | 0 | One module per admin tab. Each exposes render(). |
| `admin/views/alerts.py` | 105 | 1 | 0 | 0 | Tab 4 — Manage Alerts. |
| `admin/views/audit.py` | 48 | 1 | 0 | 0 | Tab 8 — Audit Log. |
| `admin/views/backup.py` | 87 | 1 | 0 | 0 | Tab 7 — Backup & Restore. |
| `admin/views/cells.py` | 151 | 1 | 4 | 0 | Tab 2 — Manage Cells. |
| `admin/views/cores.py` | 113 | 1 | 3 | 0 | Tab 3 — Manage Core Nodes. |
| `admin/views/dashboard.py` | 41 | 1 | 0 | 0 | Tab 0 — Admin Dashboard summary. |
| `admin/views/encryption.py` | 95 | 1 | 0 | 0 | Tab 6 — Encryption Management. |
| `admin/views/special_lines.py` | 108 | 1 | 0 | 0 | Tab 5 — Special Lines Management. |
| `admin/views/subscribers.py` | 266 | 1 | 4 | 0 | Tab 1 — Manage Subscribers (CRUD). |
| `radar/__init__.py` | 11 | 0 | 0 | 0 | TELECOM Radar package. |
| `radar/_config.py` | 18 | 0 | 0 | 0 | Package-level constants shared across radar modules. |
| `radar/main.py` | 393 | 1 | 3 | 0 | Radar entry point — orchestrates sidebar, filters, tabs. |
| `radar/services/__init__.py` | 2 | 0 | 0 | 0 | Non-Streamlit services for the radar dashboard. |
| `radar/services/anomaly.py` | 154 | 1 | 1 | 0 | Z-score based anomaly detection — free of Streamlit imports. |
| `radar/services/pdf.py` | 113 | 1 | 0 | 0 | PDF report builder — free of Streamlit imports. |
| `radar/services/period.py` | 54 | 3 | 0 | 0 | Period comparison helpers — free of Streamlit imports. |
| `radar/services/ui.py` | 127 | 8 | 0 | 0 | Small Streamlit UI helpers (cards, formatters, section headers). |
| `radar/views/__init__.py` | 2 | 0 | 0 | 0 | One module per radar tab. Each exposes render(data, filtered, ctx). |
| `radar/views/anomalies.py` | 111 | 1 | 0 | 0 | Tab 2 — Anomaly Detection. |
| `radar/views/attack_radar.py` | 135 | 1 | 0 | 0 | Tab 13 — Attack Radar. |
| `radar/views/encryption.py` | 125 | 1 | 0 | 0 | Tab 9 — Encryption Coverage. |
| `radar/views/geography.py` | 145 | 1 | 0 | 0 | Tab 11 — Geographic Distribution. |
| `radar/views/messaging.py` | 117 | 1 | 0 | 0 | Tab 7 — Messaging Analytics. |
| `radar/views/osint.py` | 97 | 1 | 0 | 0 | Tab 12 — OSINT Radar. |
| `radar/views/overview.py` | 154 | 1 | 0 | 0 | Tab 0 — Radar Overview. |
| `radar/views/period_compare.py` | 210 | 1 | 0 | 0 | Tab 1 — Period Comparison. |
| `radar/views/special_lines.py` | 114 | 1 | 0 | 0 | Tab 10 — Special Lines Analytics. |
| `radar/views/technology.py` | 106 | 1 | 0 | 0 | Tab 5 — Technology Distribution. |
| `radar/views/threat_radar.py` | 136 | 1 | 0 | 0 | Tab 8 — Threat Radar. |
| `radar/views/time_series.py` | 96 | 1 | 0 | 0 | Tab 3 — Time Series. |
| `radar/views/traffic_mix.py` | 91 | 1 | 0 | 0 | Tab 4 — Traffic Mix. |
| `radar/views/voice.py` | 109 | 1 | 0 | 0 | Tab 6 — Voice Analytics. |

---

## Testing

**294 tests** collected across 18 files.

```bash
pytest              # fast tests (unit + smoke + db + attack_core)
pytest --run-slow   # also runs the full simulator end-to-end
pytest tests/benchmarks/ --benchmark-only -o addopts=""   # benchmarks
```

| File | Test functions | Test classes |
|---|---:|---:|
| `tests/test_admin_audit.py` | 13 | 3 |
| `tests/test_admin_auth.py` | 14 | 3 |
| `tests/test_admin_backup.py` | 19 | 3 |
| `tests/test_admin_rate_limit.py` | 17 | 3 |
| `tests/test_attack_core.py` | 34 | 4 |
| `tests/test_common.py` | 31 | 6 |
| `tests/test_coverage_100.py` | 12 | 9 |
| `tests/test_coverage_extra.py` | 24 | 10 |
| `tests/test_db.py` | 5 | 2 |
| `tests/test_integration.py` | 1 | 0 |
| `tests/test_logging.py` | 19 | 5 |
| `tests/test_make_coverage_badge.py` | 21 | 3 |
| `tests/test_radar_anomaly.py` | 16 | 7 |
| `tests/test_radar_pdf.py` | 7 | 3 |
| `tests/test_radar_period.py` | 17 | 3 |
| `tests/test_smoke.py` | 2 | 0 |
| `tests/test_telecom_attack_db.py` | 19 | 6 |
| `tests/test_unit.py` | 19 | 6 |

_Note: parametrized tests are counted once by the AST scanner but expand to multiple cases at collect time (`pytest --collect-only` reports 294 total)._

---

## Dependencies

Version-constrained in `requirements.txt`:

```
altair==6.3.0
altgraph==0.17.5
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.14.2
arabic-reshaper==3.0.1
attrdict==2.0.1
attrs==26.1.0
audioop-lts==0.2.2
blinker==1.9.0
brotli==1.2.0
cabarchive==0.2.5
certifi==2026.7.22
charset-normalizer==3.5.1
choreographer==1.4.0
click==8.4.2
colorama==0.4.6
contourpy==1.3.3
cx_Freeze==8.7.0
cycler==0.12.1
darkdetect==0.8.0
docx==0.2.4
einops==0.8.2
fastapi==0.141.1
filelock==3.32.6
Flask==3.1.3
fonttools==4.65.0
freeze-core==0.7.5
fsspec==2026.9.0
gradio==6.28.0
gradio_client==2.7.1
groovy==0.1.2
h11==0.16.0
hf-gradio==0.4.1
hf-xet==1.6.0
httpcore==1.0.9
httpcore2==2.13.0
httptools==0.8.0
httpx==0.28.1
httpx2==2.13.0
huggingface_hub==1.33.0
idna==3.19
iniconfig==2.3.0
itsdangerous==2.2.0
Jinja2==3.1.6
jiter==0.17.0
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
kaleido==1.4.0
kiwisolver==1.5.1
lief==1.0.0
logistro==2.0.1
lxml==6.1.3
markdown-it-py==4.2.0
MarkupSafe==3.0.3
matplotlib==3.11.1
mdurl==0.1.2
mpmath==1.3.0
narwhals==2.26.0
networkx==3.7
Nuitka==4.2.1
numpy==2.5.3
openai==3.14.0
orjson==3.12.0
packaging==26.3
pandas==2.3.3
pefile==2024.8.26
pillow==12.3.0
platformdirs==4.11.12
plotly==5.24.1
pluggy==1.6.0
protobuf==7.36.2
pyarrow==25.0.1
pydantic==2.13.4
pydantic_core==2.46.4
pydeck==0.9.3
pydub==0.25.1
pygame-ce==2.5.8
Pygments==2.21.0
pyinstaller==6.22.3
pyinstaller-hooks-contrib==2026.7
pyparsing==3.3.2
PyQt-Fluent-Widgets==1.11.3
PyQt5-Frameless-Window==0.8.2
PyQt6-Fluent-Widgets==1.11.3
PyQt6-Frameless-Window==0.8.2
pyqtdarktheme==0.1.7
pyqtgraph==0.14.0
PySide6==6.11.2
PySide6-Fluent-Widgets==1.11.3
PySide6_Addons==6.11.2
PySide6_Essentials==6.11.2
PySideSix-Frameless-Window==0.8.2
pytest==8.4.2
python-bidi==0.6.11
python-dateutil==2.9.0.post0
python-docx==1.2.0
python-dotenv==1.2.3
python-msilib==0.7.0
python-multipart==0.0.32
python-pptx==1.0.2
pytz==2026.4
pywin32==312
pywin32-ctypes==0.2.3
PyYAML==6.0.3
referencing==0.37.0
regex==2026.9.10
reportlab==5.0.1
requests==2.34.2
rich==15.0.0
rpds-py==2026.6.3
safehttpx==0.1.7
safetensors==0.8.0
semantic-version==2.10.0
setuptools==84.0.0
shellingham==1.5.4
shiboken6==6.11.2
simplejson==4.1.2
six==1.17.0
sniffio==1.3.1
starlette==1.6.0
streamlit==1.64.0
streamlit-autorefresh==1.0.1
striprtf==0.0.33
sympy==1.14.0
tenacity==9.1.4
timm==1.0.30
tokenizers==0.22.2
toml==0.10.2
tomlkit==0.14.0
tqdm==4.70.1
transformers==4.57.6
truststore==0.10.4
typer==0.27.2
typing-inspection==0.4.4
typing_extensions==4.16.0
tzdata==2026.4
urllib3==2.8.0
uvicorn==0.52.4
watchdog==6.0.0
websockets==16.1.1
Werkzeug==3.1.8
wheel==0.48.0
xlsxwriter==3.2.9
zstandard==0.25.0
```

Minimal CI set in `requirements-ci.txt`:

```
streamlit>=1.30
plotly>=5.20
pandas>=2.0
numpy>=1.26
matplotlib>=3.8
reportlab>=4.0
streamlit-autorefresh>=1.0
pytest>=8.0
pytest-cov>=5.0
mypy>=1.11
bandit[toml]>=1.7
pip-audit>=2.7
pytest-benchmark>=4.0
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
*.bak
*.v1_backup
*.v2_backup
*.v3_backup
_admin_auth_backup/
.benchmarks/
logs/
site/
*.zip
*.pdf
*.pyc
```

---

## Logging

Centralized logging via `telecom_logging.py`, with CLI flags:

| Flag | Effect |
|---|---|
| `--verbose`, `-v` | DEBUG-level output |
| `--quiet`, `-q` | Only WARNING and above |
| `--log-file PATH` | Also write to `PATH` (UTF-8) |

Log format:

```
HH:MM:SS | LEVEL   | module                | message
```

Example:

```
10:51:00 | INFO    | telecom_net_sim       | [1/7] Building network topology...
10:51:00 | INFO    | telecom_attack        | Generating 25 scenarios...
10:51:00 | WARNING | telecom_attack        | Attack simulation skipped: ...
```

Full documentation: [Logging guide](https://docs.sunpannel.ir/logging/)

---

## Docker

Run the project in a container with `docker compose`:

```bash
# Build the image + generate a small dataset + start all dashboards
docker compose up --build

# Dashboard: http://localhost:8501
# Radar:     http://localhost:8502
# Admin:     http://localhost:8503
```

### Plain docker (without compose)

```bash
docker build -t telecom-net-sim .

# Generate the database
docker run --rm \
    -v $(pwd)/telecom_sim_output:/app/telecom_sim_output \
    telecom-net-sim python telecom_net_sim.py --subs 500 --cdrs 2000

# Run a dashboard (bound to loopback only)
docker run --rm -p 127.0.0.1:8501:8501 \
    -v $(pwd)/telecom_sim_output:/app/telecom_sim_output \
    telecom-net-sim streamlit run telecom_dashboard.py \
    --server.address 0.0.0.0
```

### Notes

- Multi-stage build (builder + slim runtime)
- Runs as **non-root** (`appuser`)
- All dashboards bind to **`127.0.0.1`** on the host (not exposed to LAN)
- A shared volume (`telecom_data`) is used between the simulator
  and the three dashboards
- A dedicated Docker workflow runs in CI to verify the image builds
  and the simulator produces a valid database

---

## Design Notes

### Why local-only?
No network calls anywhere. All data comes from a seeded RNG
(default `SEED = 1403`, overridable via `--seed` / `--random-seed`).
Runs are reproducible by default, tests are hermetic, and Streamlit
telemetry is disabled.

### Why SQLite?
Single-file DB, zero setup, easy backup / restore, portable.

### Why shims at the root?
`telecom_dashboard.py`, `telecom_admin.py` and `telecom_radar.py`
are 22-line shims that call `dashboard.main()`, `admin.main()`,
`radar.main()` respectively. This keeps the historical command
`streamlit run telecom_dashboard.py` working while the actual code
lives in a small, focused package.

### Why `main()` guards everywhere?
Streamlit scripts execute top-to-bottom on every rerun. Without a
guard, `import telecom_*` would run the whole UI. Each entry point
defines `main()` and calls it only under `__main__`. This makes
every module importable and testable.

### Why SQLite's online backup API?
`shutil.copy2` on a WAL-mode DB copies only `.db`, not the pending
`-wal`. The backup can be inconsistent.
`sqlite3.Connection.backup()` produces a consistent snapshot even
while writers are active.

### Why split `attack_core.py` from `telecom_attack.py`?
All simulation logic (scenario generation, event expansion, alert
conversion) is DB-free and lives in `attack_core.py`. The DB layer,
target indexing and CLI orchestration live in `telecom_attack.py`.
This makes the core testable in <0.5 s without spinning up SQLite.

### Why a shared `telecom_logging.py`?
Instead of scattered `print()` calls, every module uses a scoped
logger via `get_logger(__name__)`. The entry points call
`setup_logging()` once. This gives us log levels, timestamps, and
per-module prefixes for free, and it is testable with `caplog`.

---

## Known Limitations

- The attack simulator is **defensive-only**: no packets leave the host.
- `restore_2pb.py` scales `SUM(bytes)` for display only; the DB does
  **not** physically hold 2 PB.
- Streamlit dashboards are read-only; all writes go through the admin panel.
- GitHub Actions currently tests on Python 3.11, 3.12, 3.13, and 3.14 (Linux).
- `test_db.py`, `test_smoke.py` and `test_integration.py` require
  `telecom_sim_output/telecom_sim.db` to exist (or generate one on
  the fly); run `python telecom_net_sim.py --subs 500 --cdrs 2000`
  first if they fail locally.
- Performance benchmarks live in `tests/benchmarks/` and are excluded
  from the default test run (see `tests/benchmarks/README.md`).

---

*Generated 2026-10-03 by `generate_readme.py`.*
