"""Unit tests for attack_core — pure functions, no DB required.

These tests are fast (no subprocess, no DB) and run by default in CI.
"""

import pytest

from attack_core import (
    ATTACK_CATALOG,
    attacks_to_alerts,
    expand_events,
    generate_scenarios,
    pick_target,
)


# ------------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------------
@pytest.fixture
def fake_idx():
    """A minimal target index that exercises every routing branch."""
    return {
        "cores": {
            "HSS": ["HSS-01", "HSS-02"],
            "SGW": ["SGW-01"],
            "PGW": ["PGW-01"],
            "UPF": ["UPF-01"],
            "IMS": ["IMS-01"],
            "AMF": ["AMF-01"],
            "SMF": ["SMF-01"],
            "MME": ["MME-01"],
            "MSC": ["MSC-01"],
            "RIS-C": ["RIS-01"],
            "ISAC": ["ISAC-01"],
            "AI-RAN": ["AIRAN-01"],
            "NWDAF": ["NWDAF-01"],
        },
        "all_cores": ["AMF-01", "SMF-01", "UPF-01", "MME-01"],
        "cells_5g": ["5G-TEH-0001", "5G-TEH-0002"],
        "cells_6g": ["6G-TEH-0001"],
    }


# ==================================================================
# pick_target
# ==================================================================
class TestPickTarget:
    def test_diameter_routes_to_hss(self, fake_idx):
        t = pick_target("DIAMETER_ULR_FLOOD", fake_idx)
        assert t in fake_idx["cores"]["HSS"]

    def test_gtp_routes_to_sgw_or_pgw(self, fake_idx):
        t = pick_target("GTP_C_FLOOD", fake_idx)
        assert t in ("SGW-01", "PGW-01")

    def test_pfcp_routes_to_upf(self, fake_idx):
        t = pick_target("PFCP_SESSION_FLOOD", fake_idx)
        assert t == "UPF-01"

    def test_ss7_routes_to_msc(self, fake_idx):
        t = pick_target("SS7_MAP_ATI_ABUSE", fake_idx)
        assert t == "MSC-01"

    def test_thz_targets_6g_cell(self, fake_idx):
        t = pick_target("THZ_JAMMING", fake_idx)
        assert t in fake_idx["cells_6g"]

    def test_oran_targets_5g_cell(self, fake_idx):
        t = pick_target("ORAN_E2_ABUSE", fake_idx)
        assert t in fake_idx["cells_5g"]

    def test_ris_targets_risc(self, fake_idx):
        t = pick_target("RIS_PHASE_POISON", fake_idx)
        assert t == "RIS-01"

    def test_unknown_attack_uses_all_cores(self, fake_idx):
        t = pick_target("SOME_NEW_ATTACK", fake_idx)
        assert t in fake_idx["all_cores"]

    def test_empty_pool_returns_unknown(self):
        empty = {"cores": {}, "all_cores": [], "cells_5g": [], "cells_6g": []}
        assert pick_target("DIAMETER_ULR_FLOOD", empty) == "UNKNOWN"

    def test_thz_empty_6g_returns_unknown(self):
        idx = {"cores": {}, "all_cores": [], "cells_5g": [], "cells_6g": []}
        assert pick_target("THZ_JAMMING", idx) == "UNKNOWN"


# ==================================================================
# generate_scenarios
# ==================================================================
class TestGenerateScenarios:
    def test_count_matches_request(self, fake_idx):
        for n in (1, 5, 25, 50):
            s = generate_scenarios(n, fake_idx)
            assert len(s) == n

    def test_required_fields_present(self, fake_idx):
        s = generate_scenarios(3, fake_idx)
        required = {
            "scenario_id",
            "name",
            "attack_type",
            "target_layer",
            "target_node",
            "target_iface",
            "protocol",
            "severity",
            "start_ts",
            "end_ts",
            "duration_sec",
            "rate_pps",
            "total_events",
            "source_ip",
            "mitre",
            "status",
            "notes",
        }
        for sc in s:
            assert required.issubset(sc.keys())

    def test_all_attack_types_are_known(self, fake_idx):
        s = generate_scenarios(50, fake_idx)
        for sc in s:
            assert sc["attack_type"] in ATTACK_CATALOG

    def test_forced_6g_types_always_present(self, fake_idx):
        # When n >= 4, at least 4 6G-family scenarios must appear
        s = generate_scenarios(10, fake_idx)
        types = {x["attack_type"] for x in s}
        sixg_forced = {"RIS_PHASE_POISON", "AI_RAN_POISON", "THZ_JAMMING", "QUIC_FLOOD_6G"}
        # Guarantee: all 4 are present when n >= 4
        assert sixg_forced.issubset(types)

    def test_scenario_ids_unique(self, fake_idx):
        s = generate_scenarios(20, fake_idx)
        ids = [x["scenario_id"] for x in s]
        assert len(ids) == len(set(ids))

    def test_status_is_valid(self, fake_idx):
        s = generate_scenarios(20, fake_idx)
        valid = {"BLOCKED", "DETECTED", "SUCCESS", "ONGOING"}
        for sc in s:
            assert sc["status"] in valid

    def test_severity_is_valid(self, fake_idx):
        s = generate_scenarios(20, fake_idx)
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        for sc in s:
            assert sc["severity"] in valid

    def test_no_unknown_targets_when_idx_has_data(self, fake_idx):
        s = generate_scenarios(20, fake_idx)
        assert all(sc["target_node"] != "UNKNOWN" for sc in s)

    def test_rate_within_plausible_range(self, fake_idx):
        s = generate_scenarios(30, fake_idx)
        for sc in s:
            assert sc["rate_pps"] > 0
            assert sc["rate_pps"] <= 2_000_000

    def test_duration_is_positive(self, fake_idx):
        s = generate_scenarios(10, fake_idx)
        for sc in s:
            assert sc["duration_sec"] > 0


# ==================================================================
# expand_events
# ==================================================================
class TestExpandEvents:
    def test_event_count_matches(self, fake_idx):
        s = generate_scenarios(5, fake_idx)
        ev = expand_events(s, samples_per_scenario=10)
        assert len(ev) == 5 * 10

    def test_default_samples(self, fake_idx):
        s = generate_scenarios(3, fake_idx)
        ev = expand_events(s)
        assert len(ev) == 3 * 20

    def test_required_fields_present(self, fake_idx):
        s = generate_scenarios(2, fake_idx)
        ev = expand_events(s, samples_per_scenario=3)
        required = {
            "scenario_id",
            "ts",
            "attack_type",
            "target_node",
            "source_ip",
            "pps",
            "latency_ms",
            "drop_pct",
            "detected",
            "detected_by",
            "blocked",
            "mttd_sec",
            "mttr_sec",
            "severity",
            "notes",
        }
        for e in ev:
            assert required.issubset(e.keys())

    def test_all_scenario_ids_present(self, fake_idx):
        s = generate_scenarios(5, fake_idx)
        ev = expand_events(s, samples_per_scenario=4)
        scen_ids = {x["scenario_id"] for x in s}
        ev_ids = {e["scenario_id"] for e in ev}
        assert ev_ids == scen_ids

    def test_detected_implies_mttd(self, fake_idx):
        s = generate_scenarios(5, fake_idx)
        ev = expand_events(s, samples_per_scenario=30)
        for e in ev:
            if e["detected"]:
                assert e["mttd_sec"] is not None
            if e["blocked"]:
                assert e["mttr_sec"] is not None

    def test_latency_is_positive(self, fake_idx):
        s = generate_scenarios(5, fake_idx)
        ev = expand_events(s, samples_per_scenario=5)
        assert all(e["latency_ms"] > 0 for e in ev)

    def test_drop_within_bounds(self, fake_idx):
        s = generate_scenarios(5, fake_idx)
        ev = expand_events(s, samples_per_scenario=5)
        for e in ev:
            assert 0 <= e["drop_pct"] <= 95.0

    def test_success_scenarios_have_no_mttd(self, fake_idx):
        # Force a single SUCCESS scenario
        s = generate_scenarios(1, fake_idx)
        s[0]["status"] = "SUCCESS"
        ev = expand_events(s, samples_per_scenario=5)
        for e in ev:
            assert e["mttd_sec"] is None


# ==================================================================
# attacks_to_alerts
# ==================================================================
class TestAttacksToAlerts:
    def test_only_interesting_scenarios_yield_alerts(self, fake_idx):
        s = generate_scenarios(10, fake_idx)
        # force statuses
        for i, sc in enumerate(s):
            sc["status"] = "BLOCKED" if i % 2 == 0 else "DETECTED"
            sc["severity"] = "LOW"  # so CRITICAL doesn't add extra
        alerts = attacks_to_alerts(s, [])
        # only DETECTED ones qualify (BLOCKED with LOW severity doesn't)
        assert len(alerts) == 5

    def test_critical_blocked_still_alerts(self, fake_idx):
        s = generate_scenarios(1, fake_idx)
        s[0]["status"] = "BLOCKED"
        s[0]["severity"] = "CRITICAL"
        alerts = attacks_to_alerts(s, [])
        assert len(alerts) == 1

    def test_alert_fields_present(self, fake_idx):
        s = generate_scenarios(3, fake_idx)
        for sc in s:
            sc["status"] = "DETECTED"
        alerts = attacks_to_alerts(s, [])
        required = {
            "alert_id",
            "timestamp",
            "severity",
            "alert_type",
            "msisdn",
            "description",
            "extra",
            "sms_sent",
            "sms_to",
            "sms_body",
            "ack",
        }
        for a in alerts:
            assert required.issubset(a.keys())

    def test_alert_type_has_attack_prefix(self, fake_idx):
        s = generate_scenarios(3, fake_idx)
        for sc in s:
            sc["status"] = "DETECTED"
        alerts = attacks_to_alerts(s, [])
        for a in alerts:
            assert a["alert_type"].startswith("ATTACK_")

    def test_max_30_alerts(self, fake_idx):
        s = generate_scenarios(50, fake_idx)
        for sc in s:
            sc["status"] = "DETECTED"
        alerts = attacks_to_alerts(s, [])
        assert len(alerts) <= 30

    def test_empty_scenarios_yield_no_alerts(self):
        assert attacks_to_alerts([], []) == []
