"""Performance benchmarks for TELECOM-NET-SIM.

Run with:
    pytest tests/benchmarks/ --benchmark-only
    pytest tests/benchmarks/ --benchmark-only --benchmark-autosave
    pytest tests/benchmarks/ --benchmark-only --benchmark-compare

These benchmarks are NOT run by default (they are marked with `benchmark`
and only run when pytest-benchmark is installed AND the path is passed
explicitly). To make CI faster, add `--ignore=tests/benchmarks` to the
default pytest command.
"""

import pytest

from attack_core import (
    attacks_to_alerts,
    expand_events,
    generate_scenarios,
    pick_target,
)
from radar.services.anomaly import detect_anomalies
from radar.services.period import delta_pct, period_stats, split_periods


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
@pytest.fixture(scope="module")
def target_index():
    """Realistic target index for scenario generation."""
    return {
        "cores": {
            "HSS": ["HSS-01", "HSS-02"],
            "SGW": ["SGW-01"],
            "PGW": ["PGW-01"],
            "UPF": ["UPF-01"],
            "IMS": ["IMS-01"],
            "AMF": ["AMF-01", "AMF-02"],
            "SMF": ["SMF-01"],
            "MME": ["MME-01"],
            "MSC": ["MSC-01"],
            "RIS-C": ["RIS-01"],
            "ISAC": ["ISAC-01"],
            "AI-RAN": ["AIRAN-01"],
            "NWDAF": ["NWDAF-01"],
        },
        "all_cores": [
            "AMF-01",
            "AMF-02",
            "SMF-01",
            "UPF-01",
            "MME-01",
            "SGW-01",
            "PGW-01",
        ],
        "cells_5g": [f"5G-TEH-{i:04d}" for i in range(1, 51)],
        "cells_6g": [f"6G-TEH-{i:04d}" for i in range(1, 21)],
    }


@pytest.fixture(scope="module")
def big_scenarios(target_index):
    """A large set of scenarios for expand_events benchmarks."""
    return generate_scenarios(500, target_index)


@pytest.fixture(scope="module")
def small_scenarios(target_index):
    """A small set of scenarios."""
    return generate_scenarios(25, target_index)


# ==================================================================
# attack_core — pick_target
# ==================================================================
class TestBenchPickTarget:
    def test_pick_target_diameter(self, benchmark, target_index):
        benchmark(pick_target, "DIAMETER_ULR_FLOOD", target_index)

    def test_pick_target_6g(self, benchmark, target_index):
        benchmark(pick_target, "THZ_JAMMING", target_index)

    def test_pick_target_oran(self, benchmark, target_index):
        benchmark(pick_target, "ORAN_E2_ABUSE", target_index)


# ==================================================================
# attack_core — generate_scenarios
# ==================================================================
class TestBenchGenerateScenarios:
    def test_generate_25(self, benchmark, target_index):
        benchmark(generate_scenarios, 25, target_index)

    def test_generate_100(self, benchmark, target_index):
        benchmark(generate_scenarios, 100, target_index)

    def test_generate_500(self, benchmark, target_index):
        benchmark(generate_scenarios, 500, target_index)


# ==================================================================
# attack_core — expand_events
# ==================================================================
class TestBenchExpandEvents:
    def test_expand_small(self, benchmark, small_scenarios):
        benchmark(expand_events, small_scenarios, 20)

    def test_expand_large(self, benchmark, big_scenarios):
        benchmark(expand_events, big_scenarios, 20)


# ==================================================================
# attack_core — attacks_to_alerts
# ==================================================================
class TestBenchAttacksToAlerts:
    def test_to_alerts_small(self, benchmark, small_scenarios):
        benchmark(attacks_to_alerts, small_scenarios, [])

    def test_to_alerts_large(self, benchmark, big_scenarios):
        benchmark(attacks_to_alerts, big_scenarios, [])


# ==================================================================
# radar.services.period
# ==================================================================
class TestBenchPeriod:
    def test_split_periods_10k(self, benchmark):
        import pandas as pd

        n = 10_000
        df = pd.DataFrame(
            {
                "ts": pd.date_range("2026-01-01", periods=n, freq="min"),
                "record_id": [f"r{i}" for i in range(n)],
                "call_type": ["voice"] * n,
                "bytes": [1024] * n,
                "duration_sec": [60] * n,
            }
        )
        benchmark(split_periods, df)

    def test_period_stats_10k(self, benchmark):
        import pandas as pd

        n = 10_000
        df = pd.DataFrame(
            {
                "ts": pd.date_range("2026-01-01", periods=n, freq="min"),
                "record_id": [f"r{i}" for i in range(n)],
                "call_type": ["voice"] * n,
                "bytes": [1024] * n,
                "duration_sec": [60] * n,
            }
        )
        benchmark(period_stats, df)

    def test_delta_pct(self, benchmark):
        benchmark(delta_pct, 150, 100)


# ==================================================================
# radar.services.anomaly
# ==================================================================
class TestBenchAnomaly:
    @pytest.fixture(scope="class")
    def cdrs_10k(self):
        """Build a 10,000-row DataFrame for anomaly detection."""
        import pandas as pd

        n = 10_000
        return pd.DataFrame(
            {
                "hour": [i % 24 for i in range(n)],
                "city": ["Tehran"] * n,
                "call_type": ["voice"] * n,
                "voice_bearer": ["VoLTE"] * n,
                "tech": ["4G"] * n,
                "record_id": [f"r{i}" for i in range(n)],
            }
        )

    def test_detect_anomalies_10k(self, benchmark, cdrs_10k):
        benchmark(detect_anomalies, cdrs_10k, None, {})
