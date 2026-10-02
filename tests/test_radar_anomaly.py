# -*- coding: utf-8 -*-
"""Unit tests for radar.services.anomaly — pure, no Streamlit, no DB."""
import pandas as pd
import pytest

from radar.services.anomaly import detect_anomalies


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def make_cdrs(hour_counts: dict, city_counts: dict = None,
              call_type: str = "voice", tech: str = "4G") -> pd.DataFrame:
    """Build a minimal CDR DataFrame with the columns anomaly.py reads."""
    rows = []
    for hour, n in hour_counts.items():
        for _ in range(n):
            rows.append({
                "hour": hour,
                "city": "Tehran",
                "call_type": call_type,
                "voice_bearer": "VoLTE" if call_type == "voice" else None,
                "tech": tech,
                "record_id": f"r{len(rows)}",
            })
    if city_counts:
        for city, n in city_counts.items():
            for _ in range(n):
                rows.append({
                    "hour": 0,
                    "city": city,
                    "call_type": call_type,
                    "voice_bearer": "VoLTE" if call_type == "voice" else None,
                    "tech": tech,
                    "record_id": f"r{len(rows)}",
                })
    return pd.DataFrame(rows)


# ==================================================================
# Basic contract
# ==================================================================
class TestContract:
    def test_empty_df_returns_empty_list(self):
        assert detect_anomalies(pd.DataFrame(), pd.DataFrame(), {}) == []

    def test_none_df_returns_empty_list(self):
        assert detect_anomalies(None, None, {}) == []

    def test_returns_list_of_dicts(self):
        df = make_cdrs({h: 10 for h in range(24)})
        result = detect_anomalies(df, pd.DataFrame(), {})
        assert isinstance(result, list)
        for a in result:
            assert isinstance(a, dict)

    def test_each_anomaly_has_required_keys(self):
        df = make_cdrs({h: 10 for h in range(24)})
        df.loc[5, "hour"] = 5  # make sure hour is int-like
        result = detect_anomalies(df, pd.DataFrame(), {})
        required = {"type", "entity", "value", "expected",
                    "z_score", "severity", "desc"}
        for a in result:
            assert required.issubset(a.keys())

    def test_no_anomalies_on_uniform_data(self):
        # All hours identical → std == 0 → no hourly anomaly
        df = make_cdrs({h: 10 for h in range(24)})
        result = detect_anomalies(df, pd.DataFrame(), {})
        hourly = [a for a in result if a["type"] == "Hourly Traffic"]
        assert hourly == []


# ==================================================================
# Hourly traffic
# ==================================================================
class TestHourlyAnomaly:
    def test_spike_hour_detected(self):
        counts = {h: 10 for h in range(24)}
        counts[5] = 200   # massive spike
        df = make_cdrs(counts)
        result = detect_anomalies(df, pd.DataFrame(), {})
        hourly = [a for a in result if a["type"] == "Hourly Traffic"]
        assert any("Hour 05" in a["entity"] for a in hourly)
        assert any(a["severity"] == "HIGH" for a in hourly)

    def test_dip_hour_detected(self):
        counts = {h: 100 for h in range(24)}
        counts[12] = 5    # massive dip
        df = make_cdrs(counts)
        result = detect_anomalies(df, pd.DataFrame(), {})
        hourly = [a for a in result if a["type"] == "Hourly Traffic"]
        assert any("Hour 12" in a["entity"] for a in hourly)
        # dip => negative z
        assert any(a["z_score"] < 0 for a in hourly)

    def test_skipped_when_too_few_hours(self):
        df = make_cdrs({0: 10, 1: 10})
        result = detect_anomalies(df, pd.DataFrame(), {})
        assert [a for a in result if a["type"] == "Hourly Traffic"] == []


# ==================================================================
# City traffic
# ==================================================================
class TestCityAnomaly:
    def test_city_spike_detected(self):
        city_counts = {f"City{i}": 100 for i in range(10)}
        city_counts["Megacity"] = 5000
        df = make_cdrs({h: 100 for h in range(24)}, city_counts=city_counts)
        result = detect_anomalies(df, pd.DataFrame(), {})
        city_anom = [a for a in result if a["type"] == "City Traffic"]
        assert any(a["entity"] == "Megacity" for a in city_anom)


# ==================================================================
# Weak cells (from sig_findings)
# ==================================================================
class TestWeakCellsAnomaly:
    def test_outlier_weak_cell_detected(self):
        # Note on Z-scores: with a single outlier and n-1 similar values,
        # the outlier's |Z| is bounded by sqrt(n-1). To exceed the HIGH
        # threshold of 2.5, we need n >= 8.
        sig = {"weak_cells": [
            ["CELL-A", 5], ["CELL-B", 6], ["CELL-C", 5],
            ["CELL-D", 4], ["CELL-E", 5], ["CELL-F", 5],
            ["CELL-G", 6], ["CELL-H", 5], ["CELL-I", 4],
            ["CELL-Z", 500],
        ]}
        df = make_cdrs({h: 10 for h in range(24)})
        result = detect_anomalies(df, pd.DataFrame(), sig)
        weak = [a for a in result if a["type"] == "Weak Cell"]
        assert any(a["entity"] == "CELL-Z" for a in weak)
        assert any(a["severity"] == "HIGH" for a in weak)

    def test_no_weak_cells_no_anomaly(self):
        df = make_cdrs({h: 10 for h in range(24)})
        result = detect_anomalies(df, pd.DataFrame(), {"weak_cells": []})
        assert [a for a in result if a["type"] == "Weak Cell"] == []


# ==================================================================
# Encryption failures spike
# ==================================================================
class TestEncryptionSpike:
    def test_large_spike_detected(self):
        sig = {"encryption_failures": [{"x": i} for i in range(50)]}
        df = make_cdrs({h: 10 for h in range(24)})
        result = detect_anomalies(df, pd.DataFrame(), sig)
        enc = [a for a in result if a["type"] == "Encryption Failures"]
        assert len(enc) == 1
        assert enc[0]["severity"] == "HIGH"

    def test_small_count_no_anomaly(self):
        sig = {"encryption_failures": [{"x": i} for i in range(3)]}
        df = make_cdrs({h: 10 for h in range(24)})
        result = detect_anomalies(df, pd.DataFrame(), sig)
        assert [a for a in result if a["type"] == "Encryption Failures"] == []


# ==================================================================
# CLIR abuse spike
# ==================================================================
class TestClirSpike:
    def test_large_clir_spike_detected(self):
        sig = {"clir_abuse": [{"x": i} for i in range(50)]}
        df = make_cdrs({h: 10 for h in range(24)})
        result = detect_anomalies(df, pd.DataFrame(), sig)
        clir = [a for a in result if a["type"] == "CLIR Abuse Spike"]
        assert len(clir) == 1
        assert clir[0]["severity"] == "HIGH"


# ==================================================================
# VoLTE fallback anomaly
# ==================================================================
class TestVolteFallback:
    def test_all_csfb_with_modern_tech_detected(self):
        # All voice calls CSFB, but lots of 4G/5G
        df = pd.DataFrame([
            {"hour": 0, "city": "Tehran", "call_type": "voice",
             "voice_bearer": "CSFB", "tech": "4G", "record_id": f"r{i}"}
            for i in range(100)
        ])
        result = detect_anomalies(df, pd.DataFrame(), {})
        fb = [a for a in result if a["type"] == "VoLTE Fallback"]
        assert len(fb) == 1
        assert fb[0]["severity"] == "MEDIUM"

    def test_healthy_mix_no_anomaly(self):
        df = pd.DataFrame([
            {"hour": 0, "city": "Tehran", "call_type": "voice",
             "voice_bearer": "VoLTE", "tech": "4G", "record_id": f"r{i}"}
            for i in range(100)
        ])
        result = detect_anomalies(df, pd.DataFrame(), {})
        assert [a for a in result if a["type"] == "VoLTE Fallback"] == []