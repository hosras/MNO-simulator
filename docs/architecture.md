# Architecture

## Package Layout

The project uses thin **entry-point shims** at the repository root.
The actual implementation lives in three self-contained packages.

```
MNO-simulator/
- telecom_net_sim.py       # CLI simulator
- telecom_attack.py        # attack orchestrator (DB layer)
- attack_core.py           # pure attack logic (no DB)
- telecom_common.py        # shared utilities + schema
- telecom_ui_common.py     # Streamlit + Plotly helpers
-
- telecom_dashboard.py     # shim -> dashboard.main
- telecom_admin.py         # shim -> admin.main
- telecom_radar.py         # shim -> radar.main
-
- dashboard/               # operations dashboard (13 tabs)
- admin/                   # CRUD + audit + backup (9 tabs)
- radar/                   # statistical analytics (14 tabs)
- tests/                   # pytest suite
- .github/workflows/       # CI
```

## Why this split?

### Small diffs
Editing one dashboard tab changes **one small file**, not a 1,300-line monolith.

### Testable
Services (`anomaly`, `backup`, `pdf`, `period`) have **no Streamlit import**.
They can be unit-tested without a runtime.

### Backward compatible
`streamlit run telecom_dashboard.py` still works exactly as before.

## Design Decisions

### Why local-only?
No network calls anywhere. All data comes from a seeded RNG
(default `SEED = 1403`, overridable via `--seed` / `--random-seed`).

### Why SQLite?
Single-file DB, zero setup, easy backup/restore, portable.
WAL mode + `sqlite3.Connection.backup()` gives atomic snapshots.

### Why split attack_core.py from telecom_attack.py?
- **attack_core.py** -- pure functions. No DB, no I/O. 34 unit tests in 0.3 s.
- **telecom_attack.py** -- the DB layer: target indexing, persistence, alert injection, CLI orchestration.

### Why main() guards everywhere?
Streamlit scripts execute top-to-bottom on every rerun. Without a
guard, `import telecom_dashboard` would run the whole UI.

## Database Schema

| Table | Purpose |
|---|---|
| `cells` | 2G-6G cell sites |
| `cores` | Core nodes (MSC, MME, AMF, UPF, NWDAF, ...) |
| `subscribers` | 5,000 subscribers with line classes + encryption |
| `cdrs` | Call detail records |
| `alerts` | Rule-engine alerts |
| `sms_alerts` | SOC SMS dispatch log |
| `audit_log` | Admin actions |
| `attack_scenarios` | Attack simulator output |
| `attack_events` | Attack time-series |
| `sigint_findings` | JSON blobs of SIGINT analysis |
