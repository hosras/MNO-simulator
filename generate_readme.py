# -*- coding: utf-8 -*-
"""Auto-generate README.md from the project's live structure.

Reads the actual source files and produces a README that reflects:
  - Python modules       (docstring, public/private function counts)
  - Test files           (test function counts per file)
  - Windows batch files
  - requirements.txt     (version-constrained dependency list)

Usage:
    python generate_readme.py
"""
import ast
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# ================================================================
# Scanners
# ================================================================
def scan_python_module(path):
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return None

    # --- Extract a meaningful description from the docstring ---
    raw_doc = (ast.get_docstring(tree) or "").strip()
    docstring = "(no docstring)"
    for line in raw_doc.split("\n"):
        s = line.strip()
        if not s:
            continue
        if set(s) <= set("=-_*# "):
            continue
        docstring = s
        break

    # --- Count public / private functions and classes ---
    public = 0
    private = 0
    classes = 0
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("_"):
                private += 1
            else:
                public += 1
        elif isinstance(node, ast.ClassDef):
            classes += 1

    return {
        "file":      path.name,
        "docstring": docstring,
        "n_public":  public,
        "n_private": private,
        "n_classes": classes,
        "n_lines":   src.count("\n") + 1,
    }


def scan_test_file(path):
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return None

    n_tests = sum(
        1 for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    )
    n_classes = sum(
        1 for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef) and n.name.startswith("Test")
    )
    return {"file": path.name, "n_tests": n_tests, "n_classes": n_classes}


def scan_batch_files():
    return sorted(p.name for p in ROOT.glob("*.bat"))


def read_requirements():
    p = ROOT / "requirements.txt"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


# ================================================================
# Static text blocks
# ================================================================
HEADER = "\n".join([
    "# TELECOM-NET-SIM",
    "",
    "> Fully local mobile network simulator with OSINT/SIGINT analytics,",
    "> attack scenario generation, and three Streamlit dashboards.",
    "",
    "**Zero external network calls. All data is generated locally and stored",
    "in a single SQLite file.**",
    "",
    "Streamlit telemetry is **disabled** via `.streamlit/config.toml`",
    "(`gatherUsageStats = false`, `address = \"127.0.0.1\"`). The dashboards",
    "bind to loopback only - no LAN or internet exposure.",
    "",
    "*This README is auto-generated. Regenerate with:* "
    "`python generate_readme.py`",
    "",
])


FEATURES = "\n".join([
    "## Features",
    "",
    "### Simulation",
    "- Multi-technology topology: **2G / 3G / 4G / 5G / 6G** (sub-THz + mmWave)",
    "- 10 Iranian cities weighted by population",
    "- 5,000 subscribers with special-line classes "
    "(VIP / Government / Corporate / Emergency / Test)",
    "- 60,000 CDRs across voice / SMS / MMS / data / USSD / RCS",
    "- Voice bearers: VoLTE / VoWiFi / VoNR / Vo6G / CSFB",
    "- End-to-end encryption simulation (5 cipher suites, incl. Kyber-1024)",
    "",
    "### Analysis",
    "- **OSINT**: public cell registry, social complaints, sentiment",
    "- **SIGINT**: IMEI churn, SIM-box, impossible-travel, weak cells,",
    "  CLIR abuse, filter-bypass users, MMS abuse",
    "- **Encryption coverage** by line class + failure tracking",
    "- **Alert engine** with 9 rule classes -> SMS dispatch to SOC",
    "",
    "### Attack Simulator",
    "- 23 attack types across SS7 / Diameter / GTP / PFCP / SIP / "
    "HTTP2 / O-RAN / 6G",
    "- MTTD / MTTR simulation",
    "- Persists scenarios + events + alerts to the same DB",
    "",
    "### Dashboards",
    "1. `telecom_dashboard.py` - operations dashboard",
    "2. `telecom_radar.py`     - statistical analytics + PDF export",
    "3. `telecom_admin.py`     - CRUD + audit log + backup / restore",
    "",
    "Shared helpers: `telecom_ui_common.py` (Streamlit + Plotly).",
    "",
])


INSTALL = "\n".join([
    "## Installation",
    "",
    "```bash",
    "python -m venv .venv",
    ".venv\\Scripts\\activate            # Windows",
    "# source .venv/bin/activate       # Linux / macOS",
    "",
    "pip install -r requirements.txt",
    "```",
    "",
])


USAGE = "\n".join([
    "## Usage",
    "",
    "### 1. Generate the dataset",
    "",
    "```bash",
    "python telecom_net_sim.py",
    "```",
    "",
    "Outputs `telecom_sim_output/telecom_sim.db`, `report.txt`, "
    "and 10 PNG charts.",
    "",
    "### 2. Run the attack simulator (optional)",
    "",
    "```bash",
    "python telecom_attack.py",
    "```",
    "",
    "### 3. Open a dashboard",
    "",
    "```bash",
    "streamlit run telecom_dashboard.py",
    "streamlit run telecom_radar.py",
    "streamlit run telecom_admin.py",
    "```",
    "",
    "All three bind to `127.0.0.1` by default "
    "(see `.streamlit/config.toml`).",
    "",
    "### 4. Restore the 2 PB traffic figure (display only)",
    "",
    "```bash",
    "python restore_2pb.py",
    "```",
    "",
    "Scales `SUM(bytes)` for display only. The DB does **not** physically",
    "hold 2 PB.",
    "",
])


DATA_ARTIFACTS = "\n".join([
    "## Data & Artifacts",
    "",
    "Generated at runtime - nothing is committed to version control.",
    "",
    "| Path | Purpose |",
    "|---|---|",
    "| `telecom_sim_output/telecom_sim.db` | SQLite database (main store) |",
    "| `telecom_sim_output/report.txt` | Textual summary |",
    "| `telecom_sim_output/*.png` | 10 charts |",
    "| `telecom_sim_output/backups/` | Internal SQLite backups |",
    "",
    "WAL sidecar files (`telecom_sim.db-wal`, `telecom_sim.db-shm`) are",
    "created by SQLite during writes and are handled automatically by the",
    "backup API.",
    "",
    "Recommended `.gitignore` entries:",
    "",
    "```",
    ".venv/",
    "__pycache__/",
    "telecom_sim_output/",
    "*.zip",
    "*.pdf",
    "*.pyc",
    "```",
    "",
])


DESIGN_NOTES = "\n".join([
    "## Design Notes",
    "",
    "### Why local-only?",
    "No network calls anywhere. All data comes from a seeded RNG",
    "(`SEED = 1403` in `telecom_net_sim.py`). Runs are reproducible and",
    "tests are hermetic. Streamlit telemetry is disabled.",
    "",
    "### Why SQLite?",
    "Single-file DB, zero setup, easy backup / restore, portable.",
    "",
    "### Why `main()` guards in every Streamlit module?",
    "Streamlit scripts execute top-to-bottom on every rerun. Without a",
    "guard, `import telecom_*` would run the whole UI. Each module",
    "defines a `main()` and ends with a guard that runs it only when",
    "executed under `streamlit run` or as `__main__`. This makes every",
    "module both a script and a library.",
    "",
    "### Why SQLite's online backup API?",
    "`shutil.copy2` on a WAL-mode DB copies only `.db`, not the pending",
    "`-wal`. The backup can be inconsistent. "
    "`sqlite3.Connection.backup()` produces a consistent snapshot even",
    "while writers are active.",
    "",
])


LIMITATIONS_HEAD = "\n".join([
    "## Known Limitations",
    "",
    "- The attack simulator is **defensive-only**: no packets leave the host.",
    "- `restore_2pb.py` scales `SUM(bytes)` for display only; the DB does",
    "  **not** physically hold 2 PB.",
    "- Streamlit dashboards are read-only; all writes go through the admin panel.",
    "- No CI configured. Add `.github/workflows/ci.yml` running",
    "  `pytest --run-slow` to enable.",
    "- `test_db.py` and `test_unit.py::TestPickTarget` require",
    "  `telecom_sim_output/telecom_sim.db` to exist; run",
    "  `python telecom_net_sim.py` first if they skip.",
    "",
])


# ================================================================
# Renderers for dynamic tables
# ================================================================
def render_modules(modules):
    out = ["## Modules", "",
           "| Module | Lines | Public | Private | Classes | Description |",
           "|---|---:|---:|---:|---:|---|"]
    for m in modules:
        out.append(
            f"| `{m['file']}` | {m['n_lines']:,} | {m['n_public']} | "
            f"{m['n_private']} | {m['n_classes']} | {m['docstring']} |"
        )
    out.append("")
    return "\n".join(out)


def render_tests(test_files):
    total = sum(t["n_tests"] for t in test_files)
    out = ["## Testing", "",
           f"**{total} tests** across {len(test_files)} files.", "",
           "```bash",
           "pytest              # fast tests (unit + smoke + db)",
           "pytest --run-slow   # also runs the full simulator end-to-end",
           "```", "",
           "| File | Tests | Test classes |",
           "|---|---:|---:|"]
    for t in test_files:
        out.append(f"| `tests/{t['file']}` | {t['n_tests']} | {t['n_classes']} |")
    out.append("")
    return "\n".join(out)


def render_dependencies(deps):
    out = ["## Dependencies", "",
           "Version-constrained in `requirements.txt`:", "", "```"]
    out.extend(deps)
    out.extend(["```", ""])
    return "\n".join(out)


def render_batch(files):
    if not files:
        return ""
    desc = {
        "menu.bat":        "Interactive menu",
        "run_all.bat":     "Run simulator + attack + dashboards",
        "rebuild.bat":     "Full rebuild from scratch",
        "stop_all.bat":    "Stop all Streamlit processes",
        "snapshot.bat":    "Quick read-only snapshot",
        "restore.bat":     "Restore DB from a backup",
        "reset_admin.bat": "Reset admin password",
    }
    out = ["## Windows Launchers", "", "| Script | Purpose |", "|---|---|"]
    for f in files:
        out.append(f"| `{f}` | {desc.get(f, '-')} |")
    out.append("")
    return "\n".join(out)


# ================================================================
# Main
# ================================================================
def build_readme():
    modules = []
    for p in sorted(ROOT.glob("telecom_*.py")):
        info = scan_python_module(p)
        if info:
            modules.append(info)

    tests = []
    tests_dir = ROOT / "tests"
    if tests_dir.is_dir():
        for p in sorted(tests_dir.glob("test_*.py")):
            info = scan_test_file(p)
            if info:
                tests.append(info)

    deps = read_requirements()
    batch = scan_batch_files()

    parts = [
        HEADER,
        FEATURES,
        "---", "",
        INSTALL,
        "---", "",
        USAGE,
        "---", "",
        render_modules(modules),
        "---", "",
        render_tests(tests),
        "---", "",
        render_dependencies(deps),
    ]

    b = render_batch(batch)
    if b:
        parts.extend(["---", "", b])

    parts.extend([
        "---", "",
        DATA_ARTIFACTS,
        "---", "",
        DESIGN_NOTES,
        "---", "",
        LIMITATIONS_HEAD,
        "---", "",
        f"*Generated {datetime.now():%Y-%m-%d} by `generate_readme.py`.*",
        "",
    ])

    return "\n".join(parts).rstrip() + "\n"


def main():
    readme = build_readme()
    out = ROOT / "README.md"
    out.write_text(readme, encoding="utf-8", newline="\n")
    print(f"[OK]  wrote {out}")
    print(f"[OK]  {len(readme):,} chars, "
          f"{readme.count(chr(10)) + 1:,} lines")


if __name__ == "__main__":
    main()