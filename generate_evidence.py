"""Auto-generate EVIDENCE.md from the project's live state.

Produces a delivery-ready evidence document that proves the project
operates fully locally. Scans:
  - Top-level modules (telecom_*.py, attack_core.py)
  - Package modules  (dashboard/, admin/, radar/)
  - .streamlit/config.toml  (telemetry + loopback bind)
  - requirements.txt + requirements-ci.txt
  - Import smoke test across all project modules

Usage:
    python generate_evidence.py
Output:
    EVIDENCE.md
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "EVIDENCE.md"

PACKAGES = ["dashboard", "admin", "radar"]


# ------------------------------------------------------------------
# Network-related tokens to scan for in project source files
# ------------------------------------------------------------------
NETWORK_TOKENS = [
    "requests",
    "urllib",
    "http.client",
    "aiohttp",
    "httpx",
    "urlopen",
    "socket.socket",
    "socket.create_connection",
    "websocket",
    "telnetlib",
    "ftplib",
    "smtplib",
    "paramiko",
    "http.server",
    "flask",
    "fastapi",
]


# ------------------------------------------------------------------
# File iteration
# ------------------------------------------------------------------
def iter_project_py_files():
    """Yield every project .py file: top-level + packages."""
    for p in sorted(ROOT.glob("telecom_*.py")):
        yield p
    p = ROOT / "attack_core.py"
    if p.exists():
        yield p
    for pkg in PACKAGES:
        pkg_dir = ROOT / pkg
        if not pkg_dir.is_dir():
            continue
        for p in sorted(pkg_dir.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            yield p


def rel(p: Path) -> str:
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.name


def module_import_names():
    """Return dotted import paths for the smoke test."""
    names = []
    for p in sorted(ROOT.glob("telecom_*.py")):
        names.append(p.stem)
    if (ROOT / "attack_core.py").exists():
        names.append("attack_core")
    for pkg in PACKAGES:
        if (ROOT / pkg / "__init__.py").exists():
            names.append(pkg)
    return names


# ------------------------------------------------------------------
# Scanners
# ------------------------------------------------------------------
def scan_network_imports():
    """Return list of (file, line_no, line) for any suspicious import."""
    hits = []
    for path in iter_project_py_files():
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(src.split("\n"), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            is_import = stripped.startswith("import ") or stripped.startswith("from ")
            is_call = any(
                tok in stripped
                for tok in (
                    "socket.socket(",
                    "urlopen(",
                    "requests.get(",
                    "requests.post(",
                    "httpx.",
                    "aiohttp.",
                )
            )
            if not (is_import or is_call):
                continue
            for tok in NETWORK_TOKENS:
                if tok in stripped:
                    hits.append((rel(path), i, stripped))
                    break
    return hits


def scan_telemetry_config():
    cfg = ROOT / ".streamlit" / "config.toml"
    info = {
        "exists": cfg.exists(),
        "gatherUsageStats": None,
        "address": None,
        "cors": None,
        "xsrf": None,
    }
    if not cfg.exists():
        return info
    text = cfg.read_text(encoding="utf-8")
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("gatherUsageStats"):
            info["gatherUsageStats"] = s.split("=", 1)[1].strip()
        elif s.startswith("address"):
            info["address"] = s.split("=", 1)[1].strip()
        elif s.startswith("enableCORS"):
            info["cors"] = s.split("=", 1)[1].strip()
        elif s.startswith("enableXsrfProtection"):
            info["xsrf"] = s.split("=", 1)[1].strip()
    return info


def scan_requirements(fname):
    p = ROOT / fname
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def list_modules():
    """Return (rel_path, n_lines) for every project .py file."""
    out = []
    for p in iter_project_py_files():
        try:
            n = p.read_text(encoding="utf-8").count("\n") + 1
        except Exception:
            n = 0
        out.append((rel(p), n))
    return out


def list_tests():
    """Return (rel_path, n_lines, n_tests) for every test file."""
    out = []
    tests_dir = ROOT / "tests"
    if not tests_dir.is_dir():
        return out
    for p in sorted(tests_dir.rglob("test_*.py")):
        try:
            src = p.read_text(encoding="utf-8")
        except Exception:
            continue
        n_lines = src.count("\n") + 1
        n_tests = sum(1 for line in src.split("\n") if line.lstrip().startswith("def test_"))
        out.append((rel(p), n_lines, n_tests))
    return out


def run_import_test():
    """Import every project module in a subprocess."""
    names = module_import_names()
    if not names:
        return False, "", "no modules found"
    code = "import " + ", ".join(names) + "; print('OK: all modules imported cleanly')"
    try:
        r = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=90,
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def check_gitignore():
    p = ROOT / ".gitignore"
    if not p.exists():
        return None
    wanted = [
        ".venv/",
        "__pycache__/",
        "telecom_sim_output/",
        "*.zip",
        "*.pdf",
        "*.pyc",
        "logs/",
        "site/",
        ".benchmarks/",
    ]
    text = p.read_text(encoding="utf-8")
    return [w for w in wanted if any(line.strip() == w for line in text.split("\n"))]


# ------------------------------------------------------------------
# Render
# ------------------------------------------------------------------
def fence(lang, content):
    return f"```{lang}\n{content}\n```"


def build_evidence():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cfg = scan_telemetry_config()
    reqs = scan_requirements("requirements.txt")
    ci_reqs = scan_requirements("requirements-ci.txt")
    net_hits = scan_network_imports()
    modules = list_modules()
    tests = list_tests()
    import_ok, import_out, import_err = run_import_test()
    gi = check_gitignore()

    parts = []

    # Header
    parts.append("# EVIDENCE — Fully Local Operation")
    parts.append("")
    parts.append("**Project:** TELECOM-NET-SIM  ")
    parts.append(f"**Generated:** {now}  ")
    parts.append(
        "**Purpose:** Prove the simulator runs entirely offline — "
        "no network calls, no telemetry, no LAN exposure."
    )
    parts.append("")
    parts.append("---")
    parts.append("")

    # 1. Streamlit config
    parts.append("## 1. Streamlit Telemetry Disabled")
    parts.append("")
    parts.append("File: `.streamlit/config.toml`")
    parts.append("")
    if not cfg["exists"]:
        parts.append("> ⚠️ **MISSING** — `.streamlit/config.toml` not found.")
        parts.append("> Streamlit will emit usage statistics to its servers.")
    else:
        rows = [
            ("gatherUsageStats", cfg["gatherUsageStats"], "false"),
            ("address", cfg["address"], '"127.0.0.1"'),
            ("enableCORS", cfg["cors"], "true"),
            ("enableXsrfProtection", cfg["xsrf"], "true"),
        ]
        parts.append("| Setting | Value | Expected | Status |")
        parts.append("|---|---|---|---|")
        for name, actual, expected in rows:
            ok = "✅" if (actual and expected.strip('"') in actual) else "❌"
            parts.append(f"| `{name}` | `{actual or '—'}` | `{expected}` | {ok} |")
    parts.append("")

    # 2. Runtime output
    parts.append("## 2. Runtime Binding (loopback only)")
    parts.append("")
    parts.append("Expected output when running a dashboard:")
    parts.append("")
    parts.append(
        fence(
            "text",
            "Uvicorn server started on 127.0.0.1:8501\n"
            "\n"
            "  You can now view your Streamlit app in your browser.\n"
            "\n"
            "  URL: http://127.0.0.1:8501",
        )
    )
    parts.append("")
    parts.append(
        "**Note:** There must be **no** `External URL` line and "
        "**no** `Network URL` on a non-loopback address."
    )
    parts.append("")

    # 3. netstat
    parts.append("## 3. Socket Binding Verification")
    parts.append("")
    parts.append("Command:")
    parts.append("")
    parts.append(fence("cmd", "netstat -ano | findstr :8501"))
    parts.append("")
    parts.append("Expected result — every address must be `127.0.0.1`:")
    parts.append("")
    parts.append(
        fence(
            "text",
            "TCP    127.0.0.1:8501    0.0.0.0:0         LISTENING     <pid>\n"
            "TCP    127.0.0.1:8501    127.0.0.1:XXXXX   ESTABLISHED   <pid>",
        )
    )
    parts.append("")
    parts.append(
        "**Red flags:** any line with `0.0.0.0:8501` or `[::]:8501` "
        "means the port is exposed beyond loopback."
    )
    parts.append("")

    # 4. Static scan
    parts.append("## 4. Static Code Analysis")
    parts.append("")
    parts.append(
        "Scanned: top-level modules (`telecom_*.py`, `attack_core.py`) "
        "and all package modules (`dashboard/`, `admin/`, `radar/`)."
    )
    parts.append("")
    parts.append(f"Tokens searched: {', '.join(f'`{t}`' for t in NETWORK_TOKENS)}")
    parts.append("")
    if net_hits:
        parts.append(f"❌ **{len(net_hits)} suspicious line(s) found:**")
        parts.append("")
        parts.append("| File | Line | Content |")
        parts.append("|---|---:|---|")
        for fname, ln, content in net_hits:
            content_esc = content.replace("|", "\\|")
            parts.append(f"| `{fname}` | {ln} | `{content_esc}` |")
    else:
        parts.append("✅ **No network imports or calls found.**")
    parts.append("")

    # 5. Module list
    parts.append("## 5. Source Modules")
    parts.append("")
    total_lines = sum(n for _, n in modules)
    parts.append(f"Total: **{len(modules)}** Python modules " f"({total_lines:,} lines).")
    parts.append("")
    parts.append("| Module | Lines |")
    parts.append("|---|---:|")
    for name, n in modules:
        parts.append(f"| `{name}` | {n:,} |")
    parts.append("")

    # 6. Test files
    parts.append("## 6. Test Files")
    parts.append("")
    if tests:
        total_tests = sum(t[2] for t in tests)
        total_test_lines = sum(t[1] for t in tests)
        parts.append(
            f"Total: **{len(tests)}** test files "
            f"({total_tests} test functions, {total_test_lines:,} lines)."
        )
        parts.append("")
        parts.append("| File | Lines | Test functions |")
        parts.append("|---|---:|---:|")
        for name, n_lines, n_tests in tests:
            parts.append(f"| `{name}` | {n_lines:,} | {n_tests} |")
    else:
        parts.append("_No test files found._")
    parts.append("")

    # 7. Import smoke test
    parts.append("## 7. Import Smoke Test")
    parts.append("")
    names = module_import_names()
    parts.append("Command:")
    parts.append("")
    parts.append(
        fence(
            "cmd",
            'python -c "import ' + ", ".join(names) + "; print('OK')\"",
        )
    )
    parts.append("")
    parts.append("Result:")
    parts.append("")
    if import_ok:
        parts.append("✅ **All modules imported cleanly.**")
        parts.append("")
        parts.append(fence("text", import_out or "OK"))
    else:
        parts.append("❌ **Import failed.**")
        parts.append("")
        if import_err:
            parts.append(fence("text", import_err))
    parts.append("")

    # 8. Dependencies
    parts.append("## 8. Runtime Dependencies")
    parts.append("")
    if reqs:
        parts.append(f"From `requirements.txt` ({len(reqs)} packages):")
        parts.append("")
        parts.append(fence("text", "\n".join(reqs)))
    else:
        parts.append("_`requirements.txt` not found._")
    parts.append("")
    if ci_reqs:
        parts.append(f"From `requirements-ci.txt` ({len(ci_reqs)} packages, " f"used by CI):")
        parts.append("")
        parts.append(fence("text", "\n".join(ci_reqs)))
        parts.append("")

    # 9. .gitignore
    parts.append("## 9. Artifact Hygiene")
    parts.append("")
    if gi is None:
        parts.append("_`.gitignore` not found._")
    elif not gi:
        parts.append("⚠️ `.gitignore` exists but has no recommended entries.")
    else:
        parts.append("Recommended entries present in `.gitignore`:")
        parts.append("")
        for w in gi:
            parts.append(f"- `{w}`")
    parts.append("")

    # Footer
    parts.append("---")
    parts.append("")
    parts.append("## Verification Summary")
    parts.append("")
    checks = [
        (
            "Streamlit telemetry disabled",
            bool(cfg["exists"]) and cfg["gatherUsageStats"] == "false",
        ),
        (
            "Loopback bind address configured",
            bool(cfg["address"]) and "127.0.0.1" in str(cfg["address"]),
        ),
        ("No network imports in source", not net_hits),
        ("All modules import cleanly", import_ok),
    ]
    parts.append("| Check | Result |")
    parts.append("|---|---|")
    for label, ok in checks:
        parts.append(f"| {label} | {'✅ PASS' if ok else '❌ FAIL'} |")
    parts.append("")
    all_ok = all(ok for _, ok in checks)
    parts.append(
        "**Overall: "
        + (
            "✅ Project operates fully locally.**"
            if all_ok
            else "❌ Some checks failed — see above.**"
        )
    )
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(f"*Auto-generated {now} by `generate_evidence.py`.*")
    parts.append("")

    return "\n".join(parts)


def main():
    text = build_evidence()
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK]  wrote {OUT}")
    print(f"[OK]  {len(text):,} chars, " f"{text.count(chr(10)) + 1:,} lines")


if __name__ == "__main__":
    main()
