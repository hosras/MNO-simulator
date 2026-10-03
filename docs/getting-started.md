# Getting Started

## Prerequisites

- **Python 3.11+** (tested on 3.11, 3.12, 3.13)
- **~500 MB** free disk space
- **No network access required**

## Installation

Windows:

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For a minimal dev environment, use `requirements-ci.txt` instead.

## Step 1 - Generate a dataset

```bash
python telecom_net_sim.py                    # defaults: seed=1403, 5k subs, 60k CDRs
python telecom_net_sim.py --seed 42          # reproducible
python telecom_net_sim.py --random-seed      # non-deterministic
python telecom_net_sim.py --subs 500 --cdrs 2000   # fast smoke run
```

Outputs to `telecom_sim_output/`:

- `telecom_sim.db` -- SQLite database
- `report.txt` -- textual summary
- `01..10_*.png` -- 10 charts

### CLI options

| Flag | Default | Description |
|---|---|---|
| `--seed` | `1403` | Random seed for reproducibility |
| `--random-seed` | off | Ignore --seed and use a random one |
| `--subs` | `5000` | Number of subscribers |
| `--cdrs` | `60000` | Number of CDR records |

## Step 2 - (Optional) Run the attack simulator

```bash
python telecom_attack.py
```

Or use the **pure core** (no database required):

```python
from attack_core import generate_scenarios, expand_events

idx = {
    "cores": {"HSS": ["HSS-01"]},
    "all_cores": [],
    "cells_5g": [],
    "cells_6g": ["6G-001"],
}
scenarios = generate_scenarios(10, idx)   # no DB, no I/O
events    = expand_events(scenarios, samples_per_scenario=20)
```

## Step 3 - Run a dashboard

```bash
streamlit run telecom_dashboard.py
streamlit run telecom_radar.py
streamlit run telecom_admin.py
```

All three bind to `127.0.0.1` only. If a port is busy, pass `--server.port 8502`.

### First-time admin setup

The first time you open `telecom_admin.py`, you will be prompted to set a password (min 8 chars). After 5 failed login attempts within 15 minutes, the account is temporarily locked.

## Troubleshooting

**Port 8501 is already in use** -- use a different port:

```bash
streamlit run telecom_dashboard.py --server.port 8502
```

**pytest fails without a database** -- generate a small one:

```bash
python telecom_net_sim.py --subs 500 --cdrs 2000
```
