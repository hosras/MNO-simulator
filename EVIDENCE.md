# EVIDENCE — Fully Local Operation

**Project:** TELECOM-NET-SIM  
**Generated:** 2026-10-03 12:07:12  
**Purpose:** Prove the simulator runs entirely offline — no network calls, no telemetry, no LAN exposure.

---

## 1. Streamlit Telemetry Disabled

File: `.streamlit/config.toml`

| Setting | Value | Expected | Status |
|---|---|---|---|
| `gatherUsageStats` | `false` | `false` | ✅ |
| `address` | `"127.0.0.1"` | `"127.0.0.1"` | ✅ |
| `enableCORS` | `true` | `true` | ✅ |
| `enableXsrfProtection` | `true` | `true` | ✅ |

## 2. Runtime Binding (loopback only)

Expected output when running a dashboard:

```text
Uvicorn server started on 127.0.0.1:8501

  You can now view your Streamlit app in your browser.

  URL: http://127.0.0.1:8501
```

**Note:** There must be **no** `External URL` line and **no** `Network URL` on a non-loopback address.

## 3. Socket Binding Verification

Command:

```cmd
netstat -ano | findstr :8501
```

Expected result — every address must be `127.0.0.1`:

```text
TCP    127.0.0.1:8501    0.0.0.0:0         LISTENING     <pid>
TCP    127.0.0.1:8501    127.0.0.1:XXXXX   ESTABLISHED   <pid>
```

**Red flags:** any line with `0.0.0.0:8501` or `[::]:8501` means the port is exposed beyond loopback.

## 4. Static Code Analysis

Scanned: top-level modules (`telecom_*.py`, `attack_core.py`) and all package modules (`dashboard/`, `admin/`, `radar/`).

Tokens searched: `requests`, `urllib`, `http.client`, `aiohttp`, `httpx`, `urlopen`, `socket.socket`, `socket.create_connection`, `websocket`, `telnetlib`, `ftplib`, `smtplib`, `paramiko`, `http.server`, `flask`, `fastapi`

✅ **No network imports or calls found.**

## 5. Source Modules

Total: **72** Python modules (9,517 lines).

| Module | Lines |
|---|---:|
| `telecom_admin.py` | 22 |
| `telecom_attack.py` | 723 |
| `telecom_common.py` | 239 |
| `telecom_dashboard.py` | 22 |
| `telecom_logging.py` | 104 |
| `telecom_net_sim.py` | 1,756 |
| `telecom_radar.py` | 22 |
| `telecom_ui_common.py` | 141 |
| `attack_core.py` | 489 |
| `dashboard/__init__.py` | 11 |
| `dashboard/_config.py` | 13 |
| `dashboard/main.py` | 164 |
| `dashboard/services/__init__.py` | 2 |
| `dashboard/services/data.py` | 55 |
| `dashboard/services/styles.py` | 29 |
| `dashboard/services/ui.py` | 48 |
| `dashboard/views/__init__.py` | 2 |
| `dashboard/views/alerts.py` | 182 |
| `dashboard/views/attacks.py` | 94 |
| `dashboard/views/encryption.py` | 128 |
| `dashboard/views/network.py` | 56 |
| `dashboard/views/osint.py` | 101 |
| `dashboard/views/overview.py` | 88 |
| `dashboard/views/report.py` | 33 |
| `dashboard/views/sigint.py` | 120 |
| `dashboard/views/signal.py` | 73 |
| `dashboard/views/special_lines.py` | 244 |
| `dashboard/views/subscribers.py` | 62 |
| `dashboard/views/traffic.py` | 91 |
| `dashboard/views/voice_messaging.py` | 256 |
| `admin/__init__.py` | 10 |
| `admin/_config.py` | 23 |
| `admin/main.py` | 243 |
| `admin/services/__init__.py` | 2 |
| `admin/services/audit.py` | 27 |
| `admin/services/auth.py` | 20 |
| `admin/services/backup.py` | 127 |
| `admin/services/db.py` | 12 |
| `admin/services/rate_limit.py` | 47 |
| `admin/views/__init__.py` | 2 |
| `admin/views/alerts.py` | 105 |
| `admin/views/audit.py` | 48 |
| `admin/views/backup.py` | 87 |
| `admin/views/cells.py` | 151 |
| `admin/views/cores.py` | 113 |
| `admin/views/dashboard.py` | 41 |
| `admin/views/encryption.py` | 95 |
| `admin/views/special_lines.py` | 108 |
| `admin/views/subscribers.py` | 266 |
| `radar/__init__.py` | 11 |
| `radar/_config.py` | 18 |
| `radar/main.py` | 393 |
| `radar/services/__init__.py` | 2 |
| `radar/services/anomaly.py` | 154 |
| `radar/services/pdf.py` | 113 |
| `radar/services/period.py` | 54 |
| `radar/services/ui.py` | 127 |
| `radar/views/__init__.py` | 2 |
| `radar/views/anomalies.py` | 111 |
| `radar/views/attack_radar.py` | 135 |
| `radar/views/encryption.py` | 125 |
| `radar/views/geography.py` | 145 |
| `radar/views/messaging.py` | 117 |
| `radar/views/osint.py` | 97 |
| `radar/views/overview.py` | 154 |
| `radar/views/period_compare.py` | 210 |
| `radar/views/special_lines.py` | 114 |
| `radar/views/technology.py` | 106 |
| `radar/views/threat_radar.py` | 136 |
| `radar/views/time_series.py` | 96 |
| `radar/views/traffic_mix.py` | 91 |
| `radar/views/voice.py` | 109 |

## 6. Import Smoke Test

Command:

```cmd
python -c "import telecom_admin, telecom_attack, telecom_common, telecom_dashboard, telecom_logging, telecom_net_sim, telecom_radar, telecom_ui_common, attack_core, dashboard, admin, radar; print('OK')"
```

Result:

✅ **All modules imported cleanly.**

```text
OK: all modules imported cleanly
```

## 7. Runtime Dependencies

From `requirements.txt` (145 packages):

```text
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

From `requirements-ci.txt` (13 packages, used by CI):

```text
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

## 8. Artifact Hygiene

Recommended entries present in `.gitignore`:

- `.venv/`
- `__pycache__/`
- `telecom_sim_output/`
- `*.zip`
- `*.pdf`

---

## Verification Summary

| Check | Result |
|---|---|
| Streamlit telemetry disabled | ✅ PASS |
| Loopback bind address configured | ✅ PASS |
| No network imports in source | ✅ PASS |
| All modules import cleanly | ✅ PASS |

**Overall: ✅ Project operates fully locally.**

---

*Auto-generated 2026-10-03 12:07:12 by `generate_evidence.py`.*
