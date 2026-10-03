"""Auto-generate README.md from the project's live structure.

Reflects the current package-based layout:
  - Top-level modules (telecom_*.py, attack_core.py)
  - Packages        (dashboard/, admin/, radar/)
  - Tests           (tests/*.py)
  - Windows batch files
  - requirements.txt + requirements-ci.txt
  - CI badge (auto-linked to GitHub Actions)

Usage:
    python generate_readme.py
"""

import ast
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# --- GitHub slug (edit if your repo moves) ---
GITHUB_USER = "hosras"
GITHUB_REPO = "MNO-simulator"
CI_BADGE_URL = (
    f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/actions/" f"workflows/ci.yml/badge.svg"
)
CI_LINK_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/actions/" f"workflows/ci.yml"
COVERAGE_BADGE_URL = (
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/" f"main/.github/coverage.svg"
)
DOCKER_BADGE_URL = (
    f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/actions/" f"workflows/docker.yml/badge.svg"
)
DOCKER_LINK_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/actions/" f"workflows/docker.yml"
SECURITY_BADGE_URL = (
    f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/actions/" f"workflows/security.yml/badge.svg"
)
SECURITY_LINK_URL = (
    f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/actions/" f"workflows/security.yml"
)
DOCS_URL = "https://docs.sunpannel.ir/"
REPO_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}"

PACKAGES = ["dashboard", "admin", "radar"]


# ================================================================
# File iteration helpers
# ================================================================
def iter_project_py_files():
    """Yield all project .py files: top-level + package modules.

    Excludes: __pycache__, tests/, .venv/, generate_*.py, restore_*.py,
              check_*.py, main.py (launcher), and anything in sub-packages
              that is not part of the runtime surface.
    """
    # Top-level runtime modules
    for p in sorted(ROOT.glob("telecom_*.py")):
        yield p
    p = ROOT / "attack_core.py"
    if p.exists():
        yield p
    p = ROOT / "telecom_logging.py"
    if p.exists():
        yield p
    # Package modules
    for pkg in PACKAGES:
        pkg_dir = ROOT / pkg
        if not pkg_dir.is_dir():
            continue
        for p in sorted(pkg_dir.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            yield p


def rel_path(p: Path) -> str:
    """Return path relative to ROOT with forward slashes."""
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.name


# ================================================================
# Scanners
# ================================================================
def scan_python_module(path: Path):
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return None

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

    public = private = classes = 0
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("_"):
                private += 1
            else:
                public += 1
        elif isinstance(node, ast.ClassDef):
            classes += 1

    return {
        "file": rel_path(path),
        "name": path.stem,
        "docstring": docstring,
        "n_public": public,
        "n_private": private,
        "n_classes": classes,
        "n_lines": src.count("\n") + 1,
        "package": _detect_package(path),
    }


def _detect_package(path: Path) -> str:
    """Return the top-level package name or '—'."""
    try:
        first = path.relative_to(ROOT).parts[0]
    except ValueError:
        return "—"
    return first if first in PACKAGES else "—"


def scan_test_file(path: Path):
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return None

    n_tests = sum(
        1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    )
    n_classes = sum(
        1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name.startswith("Test")
    )
    return {"file": path.name, "n_tests": n_tests, "n_classes": n_classes}


def count_collected_tests():
    """Run pytest --collect-only and return the total count (or None)."""
    try:
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "--no-header",
                "-o",
                "addopts=",
                "--ignore=tests/benchmarks",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=90,
        )
        for line in reversed(r.stdout.splitlines()):
            m = re.search(r"(\d+)\s+tests?\s+collected", line)
            if m:
                return int(m.group(1))
    except Exception:
        pass
    return None


def scan_batch_files():
    return sorted(p.name for p in ROOT.glob("*.bat"))


def read_requirements(fname="requirements.txt"):
    p = ROOT / fname
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
HEADER = "\n".join(
    [
        "# TELECOM-NET-SIM",
        "",
        f"[![CI]({CI_BADGE_URL})]({CI_LINK_URL})",
        f"[![Docker]({DOCKER_BADGE_URL})]({DOCKER_LINK_URL})",
        f"[![Security]({SECURITY_BADGE_URL})]({SECURITY_LINK_URL})",
        f"![Coverage]({COVERAGE_BADGE_URL})",
        "",
        f"**Documentation:** [{DOCS_URL}]({DOCS_URL})",
        "",
        "> Fully local mobile network simulator with OSINT/SIGINT analytics,",
        "> attack scenario generation, and three Streamlit dashboards.",
        "",
        "**Zero external network calls. All data is generated locally and stored",
        "in a single SQLite file.**",
        "",
        "Streamlit telemetry is **disabled** via `.streamlit/config.toml`",
        '(`gatherUsageStats = false`, `address = "127.0.0.1"`). The dashboards',
        "bind to loopback only - no LAN or internet exposure.",
        "",
        "*This README is auto-generated. Regenerate with:* " "`python generate_readme.py`",
        "",
    ]
)


ARCHITECTURE = "\n".join(
    [
        "## Architecture",
        "",
        "The project is split into thin **entry-point shims** at the repo root",
        "and the actual implementation lives in three self-contained packages.",
        "This keeps diffs small, enables isolated testing, and lets each",
        "dashboard ship independently.",
        "",
        "```",
        "MNO-simulator/",
        "├── telecom_net_sim.py       # CLI simulator   (top-level module)",
        "├── telecom_attack.py        # attack orchestrator (DB layer)",
        "├── attack_core.py           # pure attack logic (no DB, unit-testable)",
        "├── telecom_common.py        # shared utilities + schema",
        "├── telecom_ui_common.py     # Streamlit + Plotly helpers",
        "├── telecom_logging.py       # centralized logging",
        "│",
        "├── telecom_dashboard.py     # shim -> dashboard.main",
        "├── telecom_admin.py         # shim -> admin.main",
        "├── telecom_radar.py         # shim -> radar.main",
        "│",
        "├── dashboard/               # operations dashboard",
        "│   ├── main.py",
        "│   ├── services/  (data, styles, ui)",
        "│   └── views/     (13 tabs)",
        "│",
        "├── admin/                   # CRUD + audit + backup",
        "│   ├── main.py",
        "│   ├── services/  (auth, audit, backup, db, rate_limit)",
        "│   └── views/     (9 tabs)",
        "│",
        "├── radar/                   # statistical analytics",
        "│   ├── main.py",
        "│   ├── services/  (anomaly, pdf, period, ui)",
        "│   └── views/     (14 tabs)",
        "│",
        "├── tests/                   # pytest suite",
        "│   └── benchmarks/          # pytest-benchmark (14 benchmarks)",
        "│",
        "└── .github/workflows/       # 5 workflows (CI, Docker, Docs, Security)",
        "```",
        "",
        "### Why this split?",
        "",
        "- **Small diffs**: editing one tab changes one small file, not a 1,300-line one.",
        "- **Testable**: services (`anomaly`, `backup`, `pdf`, `period`) have no",
        "  Streamlit import — they can be unit-tested without a runtime.",
        "- **Backward compatible**: `streamlit run telecom_dashboard.py` still",
        "  works exactly as before.",
        "",
    ]
)


FEATURES = "\n".join(
    [
        "## Features",
        "",
        "### Simulation",
        "- Multi-technology topology: **2G / 3G / 4G / 5G / 6G** (sub-THz + mmWave)",
        "- 10 Iranian cities weighted by population",
        "- Configurable subscriber count (default 5,000) and CDR count (default 60,000)",
        "- Special-line classes: VIP / Government / Corporate / Emergency / Test",
        "- Voice bearers: VoLTE / VoWiFi / VoNR / Vo6G / CSFB",
        "- Messaging: SMS / MMS / RCS",
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
        "- 24 attack types across SS7 / Diameter / GTP / PFCP / SIP / HTTP2",
        "  / O-RAN / 6G (RIS, ISAC, AI-RAN, THz, QUIC)",
        "- MTTD / MTTR simulation",
        "- Persists scenarios + events + alerts to the same DB",
        "- **Pure core** (`attack_core.py`) usable without a DB",
        "",
        "### Dashboards",
        "1. `telecom_dashboard.py` - operations dashboard (13 tabs)",
        "2. `telecom_radar.py`     - statistical analytics + anomaly detection",
        "                            + PDF export (14 tabs)",
        "3. `telecom_admin.py`     - CRUD + audit log + backup / restore (9 tabs)",
        "",
        "### Quality & Tooling",
        "- **CI** on GitHub Actions (Python 3.11 / 3.12 / 3.13 / 3.14, Linux)",
        "- **282 unit + smoke + integration tests**, runs in <15 s",
        "- **14 performance benchmarks** (pytest-benchmark)",
        "- **~98% coverage** on core services (views excluded)",
        "- **mypy** type checking (Success: 0 issues)",
        "- **ruff** linter + formatter (pre-commit hook)",
        "- **bandit** static security analysis (0 issues)",
        "- **pip-audit** dependency vulnerability scan (0 CVEs)",
        "- **Docker** multi-stage image + docker-compose",
        "- **Centralized logging** with `--verbose` / `--quiet` / `--log-file`",
        "- **Hermetic**: seeded RNG, no external calls, no telemetry",
        "",
    ]
)


INSTALL = "\n".join(
    [
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
        "For CI or a minimal dev environment, use `requirements-ci.txt`",
        "instead — it only pulls the packages the project actually imports.",
        "",
    ]
)


USAGE = "\n".join(
    [
        "## Usage",
        "",
        "### 1. Generate the dataset",
        "",
        "```bash",
        "python telecom_net_sim.py                    # defaults: seed=1403, 5k subs, 60k CDRs",
        "python telecom_net_sim.py --seed 42          # reproducible, different scenario",
        "python telecom_net_sim.py --random-seed      # non-reproducible, fresh every run",
        "python telecom_net_sim.py --subs 500 --cdrs 2000   # fast smoke run",
        "```",
        "",
        "Outputs `telecom_sim_output/telecom_sim.db`, `report.txt`, and 10 PNG charts.",
        "",
        "### 2. Run the attack simulator (optional)",
        "",
        "```bash",
        "python telecom_attack.py",
        "```",
        "",
        "Or from Python (pure functions, no DB required):",
        "",
        "```python",
        "from attack_core import generate_scenarios, expand_events",
        'idx = {"cores": {"HSS": ["HSS-01"]}, "all_cores": [],',
        '       "cells_5g": [], "cells_6g": ["6G-001"]}',
        "scenarios = generate_scenarios(10, idx)   # no DB, no I/O",
        "events    = expand_events(scenarios, samples_per_scenario=20)",
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
        "All three bind to `127.0.0.1` by default (see `.streamlit/config.toml`).",
        "If a port is busy, pass `--server.port 8502`.",
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
    ]
)


DATA_ARTIFACTS = "\n".join(
    [
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
        "*.bak",
        "*.v1_backup",
        "*.v2_backup",
        "*.v3_backup",
        "_admin_auth_backup/",
        ".benchmarks/",
        "logs/",
        "site/",
        "*.zip",
        "*.pdf",
        "*.pyc",
        "```",
        "",
    ]
)


LOGGING = "\n".join(
    [
        "## Logging",
        "",
        "Centralized logging via `telecom_logging.py`, with CLI flags:",
        "",
        "| Flag | Effect |",
        "|---|---|",
        "| `--verbose`, `-v` | DEBUG-level output |",
        "| `--quiet`, `-q` | Only WARNING and above |",
        "| `--log-file PATH` | Also write to `PATH` (UTF-8) |",
        "",
        "Log format:",
        "",
        "```",
        "HH:MM:SS | LEVEL   | module                | message",
        "```",
        "",
        "Example:",
        "",
        "```",
        "10:51:00 | INFO    | telecom_net_sim       | [1/7] Building network topology...",
        "10:51:00 | INFO    | telecom_attack        | Generating 25 scenarios...",
        "10:51:00 | WARNING | telecom_attack        | Attack simulation skipped: ...",
        "```",
        "",
        f"Full documentation: [Logging guide]({DOCS_URL}logging/)",
        "",
    ]
)


DOCKER = "\n".join(
    [
        "## Docker",
        "",
        "Run the project in a container with `docker compose`:",
        "",
        "```bash",
        "# Build the image + generate a small dataset + start all dashboards",
        "docker compose up --build",
        "",
        "# Dashboard: http://localhost:8501",
        "# Radar:     http://localhost:8502",
        "# Admin:     http://localhost:8503",
        "```",
        "",
        "### Plain docker (without compose)",
        "",
        "```bash",
        "docker build -t telecom-net-sim .",
        "",
        "# Generate the database",
        "docker run --rm \\",
        "    -v $(pwd)/telecom_sim_output:/app/telecom_sim_output \\",
        "    telecom-net-sim python telecom_net_sim.py --subs 500 --cdrs 2000",
        "",
        "# Run a dashboard (bound to loopback only)",
        "docker run --rm -p 127.0.0.1:8501:8501 \\",
        "    -v $(pwd)/telecom_sim_output:/app/telecom_sim_output \\",
        "    telecom-net-sim streamlit run telecom_dashboard.py \\",
        "    --server.address 0.0.0.0",
        "```",
        "",
        "### Notes",
        "",
        "- Multi-stage build (builder + slim runtime)",
        "- Runs as **non-root** (`appuser`)",
        "- All dashboards bind to **`127.0.0.1`** on the host (not exposed to LAN)",
        "- A shared volume (`telecom_data`) is used between the simulator",
        "  and the three dashboards",
        "- A dedicated Docker workflow runs in CI to verify the image builds",
        "  and the simulator produces a valid database",
        "",
    ]
)


DESIGN_NOTES = "\n".join(
    [
        "## Design Notes",
        "",
        "### Why local-only?",
        "No network calls anywhere. All data comes from a seeded RNG",
        "(default `SEED = 1403`, overridable via `--seed` / `--random-seed`).",
        "Runs are reproducible by default, tests are hermetic, and Streamlit",
        "telemetry is disabled.",
        "",
        "### Why SQLite?",
        "Single-file DB, zero setup, easy backup / restore, portable.",
        "",
        "### Why shims at the root?",
        "`telecom_dashboard.py`, `telecom_admin.py` and `telecom_radar.py`",
        "are 22-line shims that call `dashboard.main()`, `admin.main()`,",
        "`radar.main()` respectively. This keeps the historical command",
        "`streamlit run telecom_dashboard.py` working while the actual code",
        "lives in a small, focused package.",
        "",
        "### Why `main()` guards everywhere?",
        "Streamlit scripts execute top-to-bottom on every rerun. Without a",
        "guard, `import telecom_*` would run the whole UI. Each entry point",
        "defines `main()` and calls it only under `__main__`. This makes",
        "every module importable and testable.",
        "",
        "### Why SQLite's online backup API?",
        "`shutil.copy2` on a WAL-mode DB copies only `.db`, not the pending",
        "`-wal`. The backup can be inconsistent.",
        "`sqlite3.Connection.backup()` produces a consistent snapshot even",
        "while writers are active.",
        "",
        "### Why split `attack_core.py` from `telecom_attack.py`?",
        "All simulation logic (scenario generation, event expansion, alert",
        "conversion) is DB-free and lives in `attack_core.py`. The DB layer,",
        "target indexing and CLI orchestration live in `telecom_attack.py`.",
        "This makes the core testable in <0.5 s without spinning up SQLite.",
        "",
        "### Why a shared `telecom_logging.py`?",
        "Instead of scattered `print()` calls, every module uses a scoped",
        "logger via `get_logger(__name__)`. The entry points call",
        "`setup_logging()` once. This gives us log levels, timestamps, and",
        "per-module prefixes for free, and it is testable with `caplog`.",
        "",
    ]
)


LIMITATIONS_HEAD = "\n".join(
    [
        "## Known Limitations",
        "",
        "- The attack simulator is **defensive-only**: no packets leave the host.",
        "- `restore_2pb.py` scales `SUM(bytes)` for display only; the DB does",
        "  **not** physically hold 2 PB.",
        "- Streamlit dashboards are read-only; all writes go through the admin panel.",
        "- GitHub Actions currently tests on Python 3.11, 3.12, 3.13, and 3.14 (Linux).",
        "- `test_db.py`, `test_smoke.py` and `test_integration.py` require",
        "  `telecom_sim_output/telecom_sim.db` to exist (or generate one on",
        "  the fly); run `python telecom_net_sim.py --subs 500 --cdrs 2000`",
        "  first if they fail locally.",
        "- Performance benchmarks live in `tests/benchmarks/` and are excluded",
        "  from the default test run (see `tests/benchmarks/README.md`).",
        "",
    ]
)


# ================================================================
# Renderers
# ================================================================
def render_architecture(modules):
    """Summarise packages with file counts and total lines."""
    by_pkg = {}
    for m in modules:
        by_pkg.setdefault(m["package"], []).append(m)

    out = [
        "### Package Layout",
        "",
        "| Package | Files | Lines | Purpose |",
        "|---|---:|---:|---|",
    ]
    purpose = {
        "dashboard": "Operations dashboard + OSINT/SIGINT views",
        "admin": "CRUD, audit log, backup / restore",
        "radar": "Statistical analytics + anomaly detection + PDF",
        "—": "Top-level modules (simulator, attack, logging, common)",
    }
    order = ["—"] + PACKAGES
    for pkg in order:
        if pkg not in by_pkg:
            continue
        files = by_pkg[pkg]
        total = sum(f["n_lines"] for f in files)
        label = "*(top-level)*" if pkg == "—" else f"`{pkg}/`"
        out.append(f"| {label} | {len(files)} | {total:,} | " f"{purpose.get(pkg, '')} |")
    out.append("")
    return "\n".join(out)


def render_modules(modules):
    out = [
        "## Modules",
        "",
        "| Module | Lines | Public | Private | Classes | Description |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for m in modules:
        out.append(
            f"| `{m['file']}` | {m['n_lines']:,} | {m['n_public']} | "
            f"{m['n_private']} | {m['n_classes']} | {m['docstring']} |"
        )
    out.append("")
    return "\n".join(out)


def render_tests(test_files, collected):
    ast_total = sum(t["n_tests"] for t in test_files)
    if collected is not None:
        title = f"**{collected} tests** collected across {len(test_files)} files."
    else:
        title = f"**~{ast_total} test functions** across " f"{len(test_files)} files (AST count)."
    out = [
        "## Testing",
        "",
        title,
        "",
        "```bash",
        "pytest              # fast tests (unit + smoke + db + attack_core)",
        "pytest --run-slow   # also runs the full simulator end-to-end",
        'pytest tests/benchmarks/ --benchmark-only -o addopts=""   # benchmarks',
        "```",
        "",
        "| File | Test functions | Test classes |",
        "|---|---:|---:|",
    ]
    for t in test_files:
        out.append(f"| `tests/{t['file']}` | {t['n_tests']} | " f"{t['n_classes']} |")
    out.append("")
    if collected is not None:
        out.append(
            f"_Note: parametrized tests are counted once by the "
            f"AST scanner but expand to multiple cases at collect "
            f"time (`pytest --collect-only` reports "
            f"{collected} total)._"
        )
        out.append("")
    return "\n".join(out)


def render_dependencies(deps, ci_deps):
    out = [
        "## Dependencies",
        "",
        "Version-constrained in `requirements.txt`:",
        "",
        "```",
    ]
    out.extend(deps)
    out.extend(["```", ""])
    if ci_deps:
        out.extend(["Minimal CI set in `requirements-ci.txt`:", "", "```"])
        out.extend(ci_deps)
        out.extend(["```", ""])
    return "\n".join(out)


def render_batch(files):
    if not files:
        return ""
    desc = {
        "menu.bat": "Interactive menu",
        "run_all.bat": "Run simulator + attack + dashboards",
        "rebuild.bat": "Full rebuild from scratch",
        "stop_all.bat": "Stop all Streamlit processes",
        "snapshot.bat": "Quick read-only snapshot",
        "restore.bat": "Restore DB from a backup",
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
    for p in iter_project_py_files():
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

    collected = count_collected_tests()
    deps = read_requirements("requirements.txt")
    ci_deps = read_requirements("requirements-ci.txt")
    batch = scan_batch_files()

    parts = [
        HEADER,
        ARCHITECTURE,
        "---",
        "",
        FEATURES,
        "---",
        "",
        INSTALL,
        "---",
        "",
        USAGE,
        "---",
        "",
        render_architecture(modules),
        "---",
        "",
        render_modules(modules),
        "---",
        "",
        render_tests(tests, collected),
        "---",
        "",
        render_dependencies(deps, ci_deps),
    ]

    b = render_batch(batch)
    if b:
        parts.extend(["---", "", b])

    parts.extend(
        [
            "---",
            "",
            DATA_ARTIFACTS,
            "---",
            "",
            LOGGING,
            "---",
            "",
            DOCKER,
            "---",
            "",
            DESIGN_NOTES,
            "---",
            "",
            LIMITATIONS_HEAD,
            "---",
            "",
            f"*Generated {datetime.now():%Y-%m-%d} by `generate_readme.py`.*",
            "",
        ]
    )

    return "\n".join(parts).rstrip() + "\n"


def main():
    readme = build_readme()
    out = ROOT / "README.md"
    out.write_text(readme, encoding="utf-8", newline="\n")
    print(f"[OK]  wrote {out}")
    print(f"[OK]  {len(readme):,} chars, " f"{readme.count(chr(10)) + 1:,} lines")


if __name__ == "__main__":
    main()
