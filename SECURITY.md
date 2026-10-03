# Security Policy

## Supported Versions

Only the latest `main` branch receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| Older tags | :x:             |

## Reporting a Vulnerability

**Please do not open a public issue for security vulnerabilities.**

Instead, use one of the following private channels:

1. **GitHub Security Advisories** (preferred):
   [Open a private advisory](https://github.com/hosras/MNO-simulator/security/advisories/new)

2. **Email**: Please reach out via the email listed on the GitHub profile
   [@hosras](https://github.com/hosras).

When reporting, please include:

- A clear description of the issue
- Steps to reproduce
- Potential impact
- Any suggested mitigation (if known)

## Response Timeline

- **Initial acknowledgment**: within 72 hours
- **Triage + severity assessment**: within 7 days
- **Fix or mitigation**: as soon as practical, coordinated with the reporter

## Scope

TELECOM-NET-SIM is a **fully local, offline-only** simulator:

- No network calls are made at runtime (verified by `generate_evidence.py`)
- All data is generated locally and stored in a single SQLite file
- Dashboards bind to `127.0.0.1` only (loopback)
- Streamlit telemetry is disabled

The threat model assumes a **trusted host**. Areas of interest for security
research include:

- Password storage (`telecom_common.set_password` / `verify_password`)
- The admin login rate-limiter (`admin/services/rate_limit.py`)
- The SQLite backup / restore path (`admin/services/backup.py`)
- Any input parsing that reaches SQL without parameterization

## Out of Scope

- Vulnerabilities in the simulated "attacks" — these are **simulations**
  and never leave the host
- Issues in third-party dependencies (please report those upstream)
- Social engineering, physical access, or issues requiring a compromised host

## Credit

Responsible disclosures that result in a fix will be credited in the
CHANGELOG (unless the reporter prefers to remain anonymous).

Thank you for helping keep this project safe.
