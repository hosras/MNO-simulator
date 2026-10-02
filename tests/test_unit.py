"""Unit tests for pure functions and small helpers."""

import sqlite3

import pytest

from telecom_common import (
    IMEI_TACS,
    MCC,
    MNC,
    MSISDN_PREFIXES,
    gen_imei,
    gen_imsi,
    gen_key_id,
    gen_msisdn,
    luhn,
)


# ------------------------------------------------------------------
# Luhn
# ------------------------------------------------------------------
class TestLuhn:
    def test_standard_vector(self):
        # Classic Luhn test vector: 79927398713 is valid,
        # so the check digit for 7992739871 must be 3.
        assert luhn("7992739871") == "3"

    def test_all_zeros(self):
        assert luhn("0000000000") == "0"

    def test_result_is_single_digit(self):
        for n in ("1", "12345", "999999999999"):
            r = luhn(n)
            assert len(r) == 1 and r.isdigit()


# ------------------------------------------------------------------
# Haversine
# ------------------------------------------------------------------
class TestHaversine:
    def test_same_point_is_zero(self):
        from telecom_net_sim import haversine

        assert haversine(35.0, 51.0, 35.0, 51.0) == 0.0

    def test_tehran_to_mashhad(self):
        from telecom_net_sim import haversine

        d = haversine(35.6892, 51.3890, 36.2605, 59.6168)
        # Real great-circle ~740 km
        assert 700 < d < 800

    def test_london_to_paris(self):
        from telecom_net_sim import haversine

        d = haversine(51.5074, -0.1278, 48.8566, 2.3522)
        # Real great-circle ~344 km
        assert 330 < d < 360


# ------------------------------------------------------------------
# ID generators
# ------------------------------------------------------------------
class TestGenerators:
    def test_imsi_format(self):
        for _ in range(50):
            i = gen_imsi()
            assert len(i) == 15
            assert i.startswith(MCC + MNC)
            assert i.isdigit()

    def test_msisdn_format(self):
        for _ in range(50):
            m = gen_msisdn()
            assert m.startswith("98")
            assert m[2:5] in MSISDN_PREFIXES
            assert len(m) == 12  # 2 + 3 + 7
            assert m.isdigit()

    def test_imei_format_and_luhn(self):
        for _ in range(50):
            e = gen_imei()
            assert len(e) == 15
            assert e[:8] in IMEI_TACS
            # Last digit must be the Luhn check of the first 14
            assert luhn(e[:14]) == e[14]

    def test_key_id_deterministic(self):
        assert gen_key_id("seed") == gen_key_id("seed")
        assert gen_key_id("a") != gen_key_id("b")
        assert gen_key_id("x").startswith("KEY-")
        assert len(gen_key_id("x")) == 20  # "KEY-" + 16 hex chars


# ------------------------------------------------------------------
# Password hashing (isolated via monkeypatch)
# ------------------------------------------------------------------
class TestPassword:
    def test_roundtrip(self, monkeypatch, tmp_path):
        import telecom_common as tc

        auth = tmp_path / "auth.bin"
        salt = tmp_path / "salt.bin"
        monkeypatch.setattr(tc, "_AUTH_FILE", str(auth))
        monkeypatch.setattr(tc, "_SALT_FILE", str(salt))

        assert not tc.has_password()
        tc.set_password("correct horse battery staple")
        assert tc.has_password()
        assert tc.verify_password("correct horse battery staple")
        assert not tc.verify_password("wrong password")
        assert not tc.verify_password("")

    def test_different_passwords_different_salt(self, monkeypatch, tmp_path):
        import telecom_common as tc

        monkeypatch.setattr(tc, "_AUTH_FILE", str(tmp_path / "a"))
        monkeypatch.setattr(tc, "_SALT_FILE", str(tmp_path / "s"))
        tc.set_password("password1")
        salt1 = (tmp_path / "s").read_bytes()
        (tmp_path / "a").unlink()
        (tmp_path / "s").unlink()
        tc.set_password("password1")
        salt2 = (tmp_path / "s").read_bytes()
        # Salt is random per call
        assert salt1 != salt2


# ------------------------------------------------------------------
# _pick_target (uses the real DB read-only)
# ------------------------------------------------------------------
class TestPickTarget:
    def test_thz_jamming_returns_6g_cell(self, real_db):
        from telecom_attack import _build_target_index, _pick_target

        idx = _build_target_index()
        if not idx["cells_6g"]:
            pytest.skip("no 6G cells in DB")
        for _ in range(20):
            assert _pick_target("THZ_JAMMING", idx) in idx["cells_6g"]

    def test_diameter_returns_hss(self, real_db):
        from telecom_attack import _build_target_index, _pick_target

        idx = _build_target_index()
        if "HSS" not in idx["cores"]:
            pytest.skip("no HSS nodes in DB")
        for _ in range(20):
            assert _pick_target("DIAMETER_ULR_FLOOD", idx) in idx["cores"]["HSS"]

    def test_oran_returns_5g_cell(self, real_db):
        from telecom_attack import _build_target_index, _pick_target

        idx = _build_target_index()
        if not idx["cells_5g"]:
            pytest.skip("no 5G cells in DB")
        for _ in range(20):
            assert _pick_target("ORAN_F1_RESET", idx) in idx["cells_5g"]

    def test_unknown_attack_falls_back_to_any_core(self, real_db):
        from telecom_attack import _build_target_index, _pick_target

        idx = _build_target_index()
        result = _pick_target("SOMETHING_NOT_IN_CATALOG", idx)
        assert result in idx["all_cores"] or result == "UNKNOWN"


# ------------------------------------------------------------------
# generate_attack_scenarios (the fixes we applied)
# ------------------------------------------------------------------
class TestScenarioGeneration:
    def test_count_matches_request(self, real_db):
        from telecom_attack import generate_attack_scenarios

        for n in (5, 25, 50):
            assert len(generate_attack_scenarios(n)) == n

    def test_forced_6g_types_always_present(self, real_db):
        from telecom_attack import generate_attack_scenarios

        s = generate_attack_scenarios(25)
        present = {x["attack_type"] for x in s}
        for forced in ("RIS_PHASE_POISON", "AI_RAN_POISON", "THZ_JAMMING", "QUIC_FLOOD_6G"):
            assert forced in present, f"forced 6G {forced} missing"

    def test_no_unknown_targets(self, real_db):
        from telecom_attack import generate_attack_scenarios

        s = generate_attack_scenarios(25)
        unknown = [x["attack_type"] for x in s if x["target_node"] == "UNKNOWN"]
        assert not unknown, f"UNKNOWN targets: {unknown}"
