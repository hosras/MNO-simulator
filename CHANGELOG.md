# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `SECURITY.md` with disclosure policy and threat-model scope
- `CHANGELOG.md` (this file)
- Python 3.14 added to the CI test matrix
- `attack_core.py` — pure attack logic separated from the DB layer
- MkDocs Material documentation site (live at https://docs.sunpannel.ir)
- GitHub Actions workflow that deploys docs to GitHub Pages
- Coverage badge (self-hosted SVG, ~98% on core services)
- `--random-seed`, `--seed`, `--subs`, `--cdrs` CLI flags
- Google-style docstrings for the public API
- GitHub Issue and Pull Request templates
- Dependabot configuration
- `pre-commit` hooks (ruff + file hygiene)
- `.gitattributes` for cross-platform line endings

### Changed
- **Refactored** `telecom_dashboard.py` into the `dashboard/` package
- **Refactored** `telecom_admin.py` into the `admin/` package
- **Refactored** `telecom_radar.py` into the `radar/` package
- Package layout: each of the three dashboards now has
  `main.py` + `services/` + `views/`
- Entry points (`telecom_dashboard.py`, `telecom_admin.py`,
  `telecom_radar.py`) are now 22-line shims that delegate to their package
- Test count: **31 → 262**
- Coverage: **0% → 98%** (core services only; Streamlit views excluded)

### Fixed
- `restore_backup` now rejects both `/` and `\` path separators
  (cross-platform security fix, caught by CI)
- Restored `CellSite`, `CoreNode`, and `Subscriber` dataclass fields
  that were accidentally removed during docstring edits
- Smoke test now filters Streamlit's non-fatal warnings from stderr

### Security
- Path-traversal check hardened in the backup restore path
- Password hashing uses scrypt (n=2^14, r=8, p=1, dklen=32)
- Login rate-limiting is stored in the audit log (not session state)

---

## [3.0.0] - 2026-10-01

### Added
- Multi-technology topology: 2G / 3G / 4G / 5G / 6G
- 10 Iranian cities weighted by population
- 5,000 subscribers with special-line classes
- 60,000 CDRs across voice / SMS / MMS / data / USSD / RCS
- Voice bearers: VoLTE / VoWiFi / VoNR / Vo6G / CSFB
- End-to-end encryption simulation (5 cipher suites, incl. Kyber-1024)
- OSINT module (public registry, social complaints, sentiment)
- SIGINT module (IMEI churn, SIM-box, impossible-travel, weak cells)
- Alert engine with 9 rule classes and SOC SMS dispatch
- Attack simulator: 24 attack types across SS7 / Diameter / GTP /
  PFCP / SIP / HTTP2 / O-RAN / 6G
- Three Streamlit dashboards (operations, analytics, admin)
- Fully local operation (zero external network calls)

[Unreleased]: https://github.com/hosras/MNO-simulator/commits/main
[3.0.0]: https://github.com/hosras/MNO-simulator/releases/tag/v3.0.0
