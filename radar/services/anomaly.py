# -*- coding: utf-8 -*-
"""Z-score based anomaly detection — free of Streamlit imports.

This module is intentionally pure Python/NumPy/Pandas: it can be
unit-tested without running Streamlit.

Public API:
    detect_anomalies(cdrs_df, cells_df, sig_findings) -> list[dict]
"""
from typing import Dict, List

import numpy as np
import pandas as pd

from radar._config import Z_MEDIUM, Z_HIGH


def _severity(abs_z: float) -> str:
    return "HIGH" if abs_z > Z_HIGH else "MEDIUM"


def detect_anomalies(cdrs_df: pd.DataFrame,
                     cells_df: pd.DataFrame,
                     sig_findings: dict) -> List[Dict]:
    """Return a list of anomaly dicts (type, entity, value, z_score, ...).

    Detects:
      - Hourly traffic outliers
      - City traffic outliers
      - Weak cells outliers
      - System-wide encryption failure spikes
      - CLIR abuse spikes
      - VoLTE fallback routing anomalies
    """
    anomalies: List[Dict] = []
    if cdrs_df is None or not len(cdrs_df):
        return anomalies

    # 1. Hourly traffic anomalies
    hourly = cdrs_df.groupby("hour").size()
    if len(hourly) > 3:
        mean, std = hourly.mean(), hourly.std()
        if std > 0:
            for hour, val in hourly.items():
                z = (val - mean) / std
                if abs(z) > Z_MEDIUM:
                    anomalies.append({
                        "type": "Hourly Traffic",
                        "entity": f"Hour {hour:02d}:00",
                        "value": int(val),
                        "expected": int(mean),
                        "z_score": round(z, 2),
                        "severity": _severity(abs(z)),
                        "desc": f"Traffic {z:+.2f}σ from mean ({int(mean)})",
                    })

    # 2. City traffic anomalies
    city_counts = cdrs_df.groupby("city").size()
    if len(city_counts) > 3:
        mean, std = city_counts.mean(), city_counts.std()
        if std > 0:
            for city, val in city_counts.items():
                z = (val - mean) / std
                if abs(z) > Z_MEDIUM:
                    anomalies.append({
                        "type": "City Traffic",
                        "entity": city,
                        "value": int(val),
                        "expected": int(mean),
                        "z_score": round(z, 2),
                        "severity": _severity(abs(z)),
                        "desc": f"Traffic {z:+.2f}σ from mean",
                    })

    # 3. Weak cells
    weak = sig_findings.get("weak_cells", [])
    if weak:
        vals = np.array([c[1] for c in weak])
        if len(vals) > 1:
            mean, std = vals.mean(), vals.std()
            if std > 0:
                for cell_id, val in weak:
                    z = (val - mean) / std
                    if abs(z) > Z_MEDIUM:
                        anomalies.append({
                            "type": "Weak Cell",
                            "entity": cell_id,
                            "value": int(val),
                            "expected": int(mean),
                            "z_score": round(z, 2),
                            "severity": _severity(abs(z)),
                            "desc": f"Bad samples {z:+.2f}σ from mean",
                        })

    # 4. Encryption failures spike
    enc_fails = sig_findings.get("encryption_failures", [])
    if len(enc_fails) > 5:
        anomalies.append({
            "type": "Encryption Failures",
            "entity": "System-wide",
            "value": len(enc_fails),
            "expected": 5,
            "z_score": round((len(enc_fails) - 5) / 3, 2),
            "severity": "HIGH" if len(enc_fails) > 20 else "MEDIUM",
            "desc": f"Unusually high failure count ({len(enc_fails)})",
        })

    # 5. CLIR abuse spike
    clir_abuse = sig_findings.get("clir_abuse", [])
    if len(clir_abuse) > 20:
        anomalies.append({
            "type": "CLIR Abuse Spike",
            "entity": "System-wide",
            "value": len(clir_abuse),
            "expected": 10,
            "z_score": round((len(clir_abuse) - 10) / 5, 2),
            "severity": "HIGH" if len(clir_abuse) > 40 else "MEDIUM",
            "desc": f"Unauthorized CLIR events ({len(clir_abuse)})",
        })

    # 6. Voice bearer distribution anomaly
    if "voice_bearer" in cdrs_df.columns:
        v = cdrs_df[cdrs_df["call_type"] == "voice"]
        if len(v):
            dist = v["voice_bearer"].value_counts(normalize=True)
            tech_mix = cdrs_df["tech"].value_counts(normalize=True)
            modern = tech_mix.get("4G", 0) + tech_mix.get("5G", 0)
            csfb_pct = dist.get("CSFB", 0)
            if csfb_pct > 0.8 and modern > 0.5:
                anomalies.append({
                    "type": "VoLTE Fallback",
                    "entity": "Voice routing",
                    "value": f"{csfb_pct*100:.0f}%",
                    "expected": "20-40%",
                    "z_score": 2.5,
                    "severity": "MEDIUM",
                    "desc": (f"High CSFB ({csfb_pct*100:.0f}%) despite "
                             f"{modern*100:.0f}% modern tech"),
                })

    return anomalies