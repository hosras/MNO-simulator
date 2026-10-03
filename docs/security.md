# Security Model

## Threat Model

Designed for **offline, single-host operation**.

- The host is trusted.
- Dashboards are accessed from the same machine (127.0.0.1).
- No data ever leaves the host.

## Guarantees

### Zero external network calls

Verified by static analysis:

```bash
python generate_evidence.py
```

### Streamlit telemetry disabled

`.streamlit/config.toml`:

```toml
[server]
address = "127.0.0.1"

[browser]
gatherUsageStats = false
```

### Loopback-only binding

```bash
netstat -ano | findstr :8501
```

Every address must be `127.0.0.1`. Red flags: `0.0.0.0:8501` or `[::]:8501`.

### Password hashing

Admin passwords use **scrypt**:

- `n = 2^14`
- `r = 8`
- `p = 1`
- `dklen = 32`

Salt is 16 random bytes from `secrets.token_bytes()`.
Comparison uses `hmac.compare_digest`.

### Login rate-limiting

5 failed attempts within 15 minutes triggers a lockout.
Counter lives in `audit_log` (not `session_state`).

### Backup integrity

- WAL-aware snapshots via `sqlite3.Connection.backup()`
- `PRAGMA quick_check` before restore
- Path-traversal protection

## Reporting a vulnerability

Please **do not** open a public issue. Use GitHub Security Advisories.
