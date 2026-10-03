# Performance Benchmarks

Hot paths are benchmarked with [pytest-benchmark](https://pytest-benchmark.readthedocs.io/).
Benchmarks live in `tests/benchmarks/` and are **ignored by default**.

## Running

```bash
# Run all benchmarks
pytest tests/benchmarks/ --benchmark-only -o addopts=""

# Save a baseline
pytest tests/benchmarks/ --benchmark-only --benchmark-autosave -o addopts=""

# Compare against the latest baseline
pytest tests/benchmarks/ --benchmark-only --benchmark-compare -o addopts=""
```

## What is measured

| Module | Functions |
|---|---|
| `attack_core` | `pick_target`, `generate_scenarios`, `expand_events`, `attacks_to_alerts` |
| `radar.services.period` | `split_periods`, `period_stats`, `delta_pct` |
| `radar.services.anomaly` | `detect_anomalies` |

In total, **14 benchmarks** covering the hottest paths.

## Sample output

```
Name (time in us)                    Min        Max       Mean
---------------------------------------------------------------
test_delta_pct                    0.5000     1.2000     0.6000
test_pick_target_6g               1.5000     3.0000     1.8000
test_generate_25                 45.0000    80.0000    55.0000
test_generate_500               950.0000  1200.0000  1050.0000
test_split_periods_10k          280.0000   400.0000   320.0000
test_detect_anomalies_10k       650.0000   900.0000   720.0000
---------------------------------------------------------------
```

(Times vary by machine.)

## Baseline storage

When you run with `--benchmark-autosave`, results go to:

```
.benchmarks/<platform>-<python>-<arch>/
```

This directory is `.gitignore`d, so baselines stay local. To share a
baseline across a team, use `--benchmark-json=baseline.json` and commit
that file.

## Why benchmarks are not in CI

Benchmarks are inherently noisy on shared CI runners:

- CPU frequency varies between runs.
- Neighboring jobs steal CPU time.
- Warmup rounds behave differently.

Instead, we run them **manually** on developer machines, or as a
separate informational job (no failure threshold).

## Regression testing locally

After generating a baseline, later runs can be compared:

```bash
pytest tests/benchmarks/ --benchmark-only --benchmark-compare -o addopts=""
```

`pytest-benchmark` will flag any benchmark whose mean exceeds the
baseline by a configurable percentage.
