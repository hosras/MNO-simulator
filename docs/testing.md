# Testing

## Running tests

```bash
pytest              # fast tests
pytest --run-slow   # also runs the full simulator end-to-end
```

## Test suite

**262 tests** across 14 files, executed in under 10 seconds.

| File | Tests | Focus |
|---|---:|---|
| `test_admin_audit.py` | ~30 | audit log + DB wrappers |
| `test_admin_auth.py` | 13 | session-state helpers |
| `test_admin_backup.py` | 19 | backup / restore |
| `test_admin_rate_limit.py` | 17 | login lockout logic |
| `test_attack_core.py` | 34 | pure attack functions |
| `test_common.py` | 31 | password + DB utilities |
| `test_coverage_extra.py` | 45 | edge cases |
| `test_db.py` | 5 | schema invariants |
| `test_integration.py` | 1 | end-to-end run |
| `test_make_coverage_badge.py` | 22 | badge generator |
| `test_radar_anomaly.py` | 16 | Z-score detection |
| `test_radar_pdf.py` | 7 | PDF builder |
| `test_radar_period.py` | 17 | period comparison |
| `test_smoke.py` | 6 | import cleanliness |
| `test_telecom_attack_db.py` | 21 | DB layer |
| `test_unit.py` | 19 | Luhn, haversine, generators |

## Coverage

```bash
coverage erase
coverage run --source=. -m pytest --run-slow -q
coverage report
```

Current coverage: **98%** on core services.

## CI

Every push runs GitHub Actions on Python 3.11, 3.12, 3.13:

1. Install dependencies from `requirements-ci.txt`
2. Verify packages import cleanly
3. Generate a minimal dataset
4. Run fast tests
5. Run slow tests

## pre-commit hooks

```bash
pre-commit install
pre-commit run --all-files
```
