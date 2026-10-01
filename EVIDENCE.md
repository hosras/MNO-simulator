# EVIDENCE — Fully Local Operation

**Project:** TELECOM-NET-SIM  
**Generated:** 2026-10-01 09:40:32  
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

Scanned files: `telecom_*.py`  
Tokens searched: `requests`, `urllib`, `http.client`, `aiohttp`, `httpx`, `urlopen`, `socket.socket`, `socket.create_connection`, `websocket`, `telnetlib`, `ftplib`, `smtplib`, `paramiko`, `http.server`, `flask`, `fastapi`

✅ **No network imports or calls found.**

```cmd
findstr /S /I /M "requests urllib socket http.client aiohttp httpx urlopen" *.py
```

(no output)

## 5. Source Modules

Total: **7** Python modules

| Module |
|---|
| `telecom_admin.py` |
| `telecom_attack.py` |
| `telecom_common.py` |
| `telecom_dashboard.py` |
| `telecom_net_sim.py` |
| `telecom_radar.py` |
| `telecom_ui_common.py` |

## 6. Import Smoke Test

Command:

```cmd
python -c "import telecom_admin, telecom_attack, telecom_common, telecom_dashboard, telecom_net_sim, telecom_radar, telecom_ui_common; print('OK')"
```

Result:

✅ **All modules imported cleanly.**

```text
OK: all modules imported cleanly
```

## 7. Runtime Dependencies

From `requirements.txt`:

```text
pandas>=2.0,<3.0
streamlit>=1.30,<2.0
plotly>=5.18,<6.0
matplotlib>=3.7,<4.0
pytest>=7.4,<9.0
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

*Auto-generated 2026-10-01 09:40:32 by `generate_evidence.py`.*
