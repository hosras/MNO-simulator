"""
================================================================
 TELECOM-ATTACK-CORE v1.0
 Pure attack-simulation logic — NO database, NO file I/O.

 All functions here are safe to call from unit tests without
 a live DB. Persistence lives in telecom_attack.py.
================================================================
"""

import random
from datetime import datetime, timedelta

from telecom_common import SOC_RECIPIENTS

# ------------------------------------------------------------------
# ATTACK CATALOG
# ------------------------------------------------------------------
ATTACK_CATALOG = {
    # --- Signaling (SS7 / Diameter / GTP / PFCP) ---
    "SS7_MAP_ATI_ABUSE": {
        "layer": "SS7",
        "severity": "CRITICAL",
        "family": "signaling",
        "target_iface": "MAP",
        "protocol": "TCAP/MAP",
        "desc": "Bulk Any-Time-Interrogation to locate subscribers",
        "mitre": "T1005",
    },
    "SS7_SRI_FLOOD": {
        "layer": "SS7",
        "severity": "HIGH",
        "family": "signaling",
        "target_iface": "MAP",
        "protocol": "TCAP/MAP",
        "desc": "Send-Routing-Info flood to HLR",
        "mitre": "T1498",
    },
    "DIAMETER_ULR_FLOOD": {
        "layer": "Diameter",
        "severity": "HIGH",
        "family": "signaling",
        "target_iface": "S6a",
        "protocol": "Diameter",
        "desc": "Update-Location-Request flood on HSS",
        "mitre": "T1498",
    },
    "DIAMETER_AIR_FLOOD": {
        "layer": "Diameter",
        "severity": "MEDIUM",
        "family": "signaling",
        "target_iface": "S6a",
        "protocol": "Diameter",
        "desc": "Authentication-Information-Request flood",
        "mitre": "T1498",
    },
    "GTP_C_FLOOD": {
        "layer": "GTP",
        "severity": "HIGH",
        "family": "signaling",
        "target_iface": "S11/S5",
        "protocol": "GTP-C",
        "desc": "Create-Session-Request flood on SGW/PGW",
        "mitre": "T1498",
    },
    "PFCP_SESSION_FLOOD": {
        "layer": "5G",
        "severity": "HIGH",
        "family": "signaling",
        "target_iface": "N4",
        "protocol": "PFCP",
        "desc": "PFCP Session-Establishment flood on UPF",
        "mitre": "T1498",
    },
    "SIP_REGISTER_FLOOD": {
        "layer": "IMS",
        "severity": "HIGH",
        "family": "signaling",
        "target_iface": "Gm",
        "protocol": "SIP",
        "desc": "SIP REGISTER flood on P-CSCF",
        "mitre": "T1498",
    },
    "SIP_INVITE_FLOOD": {
        "layer": "IMS",
        "severity": "MEDIUM",
        "family": "signaling",
        "target_iface": "Gm",
        "protocol": "SIP",
        "desc": "SIP INVITE flood on S-CSCF",
        "mitre": "T1498",
    },
    # --- DDoS / Flood ---
    "HTTP2_RAPID_RESET": {
        "layer": "5G",
        "severity": "HIGH",
        "family": "ddos",
        "target_iface": "SBI",
        "protocol": "HTTP/2",
        "desc": "HTTP/2 Rapid Reset on NRF/AMF SBI",
        "mitre": "T1499",
    },
    "NFS_NRF_ENUM": {
        "layer": "5G",
        "severity": "MEDIUM",
        "family": "recon",
        "target_iface": "SBI",
        "protocol": "HTTP/2",
        "desc": "NF discovery enumeration on NRF",
        "mitre": "T1046",
    },
    "UDP_UPF_AMPLIFY": {
        "layer": "5G",
        "severity": "HIGH",
        "family": "ddos",
        "target_iface": "N3/N6",
        "protocol": "UDP/GTP-U",
        "desc": "UDP amplification via misconfigured UPF",
        "mitre": "T1498",
    },
    "SCTP_MME_FLOOD": {
        "layer": "4G",
        "severity": "CRITICAL",
        "family": "ddos",
        "target_iface": "S1-MME",
        "protocol": "SCTP/S1AP",
        "desc": "SCTP INIT flood on MME",
        "mitre": "T1498",
    },
    # --- RAN / O-RAN ---
    "ORAN_E2_ABUSE": {
        "layer": "O-RAN",
        "severity": "HIGH",
        "family": "ran",
        "target_iface": "E2",
        "protocol": "E2AP/SCTP",
        "desc": "E2 node registration spam to near-RT RIC",
        "mitre": "T1498",
    },
    "ORAN_A1_POLICY_POISON": {
        "layer": "O-RAN",
        "severity": "CRITICAL",
        "family": "ran",
        "target_iface": "A1",
        "protocol": "HTTP/JSON",
        "desc": "Malicious A1 policy injection",
        "mitre": "T1565",
    },
    "ORAN_F1_RESET": {
        "layer": "O-RAN",
        "severity": "MEDIUM",
        "family": "ran",
        "target_iface": "F1",
        "protocol": "F1AP/SCTP",
        "desc": "Repeated F1 Reset on gNB-DU",
        "mitre": "T1499",
    },
    # --- Recon ---
    "NRF_SBI_SCAN": {
        "layer": "5G",
        "severity": "MEDIUM",
        "family": "recon",
        "target_iface": "SBI",
        "protocol": "HTTP/2",
        "desc": "Systematic SBI endpoint scan",
        "mitre": "T1046",
    },
    "DNS_TUNNEL_EXFIL": {
        "layer": "Core",
        "severity": "HIGH",
        "family": "exfil",
        "target_iface": "N6",
        "protocol": "DNS",
        "desc": "DNS tunneling for data exfiltration",
        "mitre": "T1048",
    },
    # ---------------- 6G ----------------
    "RIS_PHASE_POISON": {
        "layer": "6G",
        "severity": "CRITICAL",
        "family": "ran",
        "target_iface": "RIS-C",
        "protocol": "SideControl",
        "desc": "Malicious RIS phase-shift manipulation",
        "mitre": "T1565",
    },
    "ISAC_SPOOFING": {
        "layer": "6G",
        "severity": "HIGH",
        "family": "ran",
        "target_iface": "ISAC",
        "protocol": "Sensing-API",
        "desc": "False radar/sensing returns injection",
        "mitre": "T1036",
    },
    "AI_RAN_POISON": {
        "layer": "6G",
        "severity": "CRITICAL",
        "family": "ran",
        "target_iface": "AI-RAN",
        "protocol": "gRPC/ML",
        "desc": "Training-data poisoning on AI-native RAN",
        "mitre": "T1565",
    },
    "NWDAF_DATA_INJECT": {
        "layer": "6G",
        "severity": "HIGH",
        "family": "signaling",
        "target_iface": "NWDAF",
        "protocol": "HTTP/2",
        "desc": "Fake analytics input to NWDAF",
        "mitre": "T1565",
    },
    "THZ_JAMMING": {
        "layer": "6G",
        "severity": "HIGH",
        "family": "ddos",
        "target_iface": "THz-air",
        "protocol": "RF",
        "desc": "Sub-THz uplink jamming burst",
        "mitre": "T1498",
    },
    "QUIC_FLOOD_6G": {
        "layer": "6G",
        "severity": "HIGH",
        "family": "ddos",
        "target_iface": "N1/N2",
        "protocol": "QUIC",
        "desc": "QUIC connection flood on 6G AMF",
        "mitre": "T1498",
    },
}


# ------------------------------------------------------------------
# TARGET PICKING (pure)
# ------------------------------------------------------------------
def pick_target(attack_type: str, idx: dict) -> str:
    """Pick a plausible target node for the attack type.

    Pure function: relies on a pre-built index dict produced by
    telecom_attack._build_target_index(). No DB access here.

    Args:
        attack_type: key from ATTACK_CATALOG.
        idx: dict with keys {"cores", "all_cores", "cells_5g", "cells_6g"}.

    Returns:
        A node_id or cell_id, or "UNKNOWN" if the pool is empty.
    """
    roles = []
    pool = None

    if attack_type in ("DIAMETER_ULR_FLOOD", "DIAMETER_AIR_FLOOD"):
        roles = ["HSS"]
    elif attack_type == "GTP_C_FLOOD":
        roles = ["SGW", "PGW"]
    elif attack_type == "PFCP_SESSION_FLOOD":
        roles = ["UPF"]
    elif attack_type in ("SIP_REGISTER_FLOOD", "SIP_INVITE_FLOOD"):
        roles = ["IMS"]
    elif attack_type in ("HTTP2_RAPID_RESET", "NFS_NRF_ENUM", "NRF_SBI_SCAN"):
        roles = ["AMF", "SMF", "UPF"]
    elif attack_type == "SCTP_MME_FLOOD":
        roles = ["MME"]
    elif attack_type in ("SS7_MAP_ATI_ABUSE", "SS7_SRI_FLOOD"):
        roles = ["MSC"]
    elif attack_type in ("RIS_PHASE_POISON", "ISAC_SPOOFING", "AI_RAN_POISON"):
        roles = [
            {
                "RIS_PHASE_POISON": "RIS-C",
                "ISAC_SPOOFING": "ISAC",
                "AI_RAN_POISON": "AI-RAN",
            }[attack_type]
        ]
    elif attack_type == "NWDAF_DATA_INJECT":
        roles = ["NWDAF"]
    elif attack_type == "THZ_JAMMING":
        pool = idx.get("cells_6g", [])
    elif attack_type == "QUIC_FLOOD_6G":
        roles = ["AMF"]
    elif attack_type.startswith("ORAN_"):
        pool = idx.get("cells_5g", [])
    else:
        pool = idx.get("all_cores", [])

    if pool is None:
        pool = []
        for r in roles:
            pool.extend(idx.get("cores", {}).get(r, []))

    return random.choice(pool) if pool else "UNKNOWN"


# ------------------------------------------------------------------
# SCENARIO GENERATION (pure)
# ------------------------------------------------------------------
def generate_scenarios(n: int, target_idx: dict, now: datetime | None = None) -> list[dict]:
    """Generate n random attack scenarios with plausible timings.

    Pure: does not touch the DB. Caller supplies a pre-built target
    index (see telecom_attack._build_target_index()).

    Guarantees a share of 6G scenarios (RIS_PHASE_POISON,
    AI_RAN_POISON, THZ_JAMMING, QUIC_FLOOD_6G).

    Args:
        n: number of scenarios to generate.
        target_idx: dict with keys {"cores", "all_cores",
                    "cells_5g", "cells_6g"}.
        now: reference time; defaults to datetime.now().

    Returns:
        List of dicts matching the attack_scenarios table schema.
    """
    if now is None:
        now = datetime.now()

    scenarios = []
    all_types = list(ATTACK_CATALOG.keys())
    _forced_6g = [
        a
        for a in ("RIS_PHASE_POISON", "AI_RAN_POISON", "THZ_JAMMING", "QUIC_FLOOD_6G")
        if a in ATTACK_CATALOG
    ]
    n_forced = min(len(_forced_6g), n)
    chosen_types: list[str] = list(random.sample(_forced_6g, k=n_forced))
    other_types = [t for t in all_types if t not in _forced_6g]
    if n > n_forced and other_types:
        chosen_types += random.choices(other_types, k=n - n_forced)

    for i, atype in enumerate(chosen_types):
        meta = ATTACK_CATALOG[atype]

        start = now - timedelta(hours=random.uniform(0, 24), minutes=random.uniform(0, 60))
        dur = random.choice([10, 30, 60, 120, 300, 600, 1800])
        end = start + timedelta(seconds=dur)

        base_rate = {
            "signaling": (500, 50_000),
            "ddos": (10_000, 2_000_000),
            "ran": (100, 20_000),
            "recon": (5, 500),
            "exfil": (10, 2_000),
        }.get(meta["family"], (100, 10_000))
        rate = random.randint(*base_rate)
        total_events = int(rate * dur * random.uniform(0.7, 1.0))

        scenarios.append(
            {
                "scenario_id": f"ATK-{now.strftime('%Y%m%d')}-{i+1:04d}",
                "name": f"{atype} on {meta['target_iface']}",
                "attack_type": atype,
                "target_layer": meta["layer"],
                "target_node": pick_target(atype, target_idx),
                "target_iface": meta["target_iface"],
                "protocol": meta["protocol"],
                "severity": meta["severity"],
                "start_ts": start.strftime("%Y-%m-%d %H:%M:%S"),
                "end_ts": end.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_sec": dur,
                "rate_pps": rate,
                "total_events": total_events,
                "source_ip": f"{random.randint(1, 223)}.{random.randint(0, 255)}."
                f"{random.randint(0, 255)}.{random.randint(1, 254)}",
                "mitre": meta["mitre"],
                "status": random.choices(
                    ["BLOCKED", "DETECTED", "SUCCESS", "ONGOING"], weights=[0.5, 0.35, 0.1, 0.05]
                )[0],
                "notes": meta["desc"],
            }
        )
    return scenarios


# ------------------------------------------------------------------
# EVENT EXPANSION (pure)
# ------------------------------------------------------------------
def expand_events(scenarios: list[dict], samples_per_scenario: int = 20) -> list[dict]:
    """Expand each scenario into a time-series of event samples.

    Pure: no DB, no I/O.

    For each scenario, generate `samples_per_scenario` equally-spaced
    samples between start_ts and end_ts. Each sample carries MTTD,
    MTTR, and KPI impact (latency, drop) derived from pps.
    """
    events = []
    for s in scenarios:
        start = datetime.strptime(s["start_ts"], "%Y-%m-%d %H:%M:%S")
        dur = s["duration_sec"]
        for k in range(samples_per_scenario):
            offset = dur * k / samples_per_scenario
            ts = start + timedelta(seconds=offset)

            mttd = random.uniform(3, 90) if s["status"] != "SUCCESS" else None
            detected = 1 if mttd is not None and k * dur / samples_per_scenario >= mttd else 0

            mttr = None
            blocked = 0
            if detected and mttd is not None:
                mttr = random.uniform(15, 600)
                if k * dur / samples_per_scenario >= mttd + mttr:
                    blocked = 1

            latency = random.gauss(50, 20) + (s["rate_pps"] / 10_000) * random.uniform(5, 30)
            latency = max(1.0, latency)
            drop = min(95.0, (s["rate_pps"] / 100_000) * random.uniform(2, 15))

            events.append(
                {
                    "scenario_id": s["scenario_id"],
                    "ts": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "attack_type": s["attack_type"],
                    "target_node": s["target_node"],
                    "source_ip": s["source_ip"],
                    "pps": int(s["rate_pps"] * random.uniform(0.6, 1.4)),
                    "latency_ms": round(latency, 2),
                    "drop_pct": round(drop, 2),
                    "detected": detected,
                    "detected_by": random.choice(["SIEM", "SOC-N1", "Anomaly-Engine", "NOC"])
                    if detected
                    else None,
                    "blocked": blocked,
                    "mttd_sec": round(mttd, 1) if detected and mttd is not None else None,
                    "mttr_sec": round(mttr, 1) if blocked and mttr is not None else None,
                    "severity": s["severity"],
                    "notes": "",
                }
            )
    return events


# ------------------------------------------------------------------
# ALERT GENERATION (pure)
# ------------------------------------------------------------------
def attacks_to_alerts(scenarios: list[dict], events: list[dict]) -> list[dict]:
    """Convert attack scenarios into alert rows for the alerts table.

    Pure: no DB, no I/O. Only DETECTED/SUCCESS/ONGOING or CRITICAL
    scenarios become alerts. Each alert routes to one SOC recipient.
    """
    alerts = []
    ts_now = datetime.now()
    ts_suffix = ts_now.strftime("%H%M%S")
    interesting = [
        s
        for s in scenarios
        if s["status"] in ("DETECTED", "SUCCESS", "ONGOING") or s["severity"] == "CRITICAL"
    ]
    for idx, s in enumerate(interesting[:30]):
        sev_map = {"CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
        sev = sev_map.get(s["severity"], "MEDIUM")
        soc_to = random.choice(SOC_RECIPIENTS)
        alert_id = f"ALT-{ts_now.strftime('%Y%m%d')}-{ts_suffix}-ATK{idx+1:04d}"
        alerts.append(
            {
                "alert_id": alert_id,
                "timestamp": s["start_ts"],
                "severity": sev,
                "alert_type": f"ATTACK_{s['attack_type']}",
                "msisdn": "-",
                "description": f"{s['attack_type']} on {s['target_node']} "
                f"({s['target_iface']}) @ {s['rate_pps']:,} pps",
                "extra": json_dumps(
                    {
                        "scenario_id": s["scenario_id"],
                        "layer": s["target_layer"],
                        "protocol": s["protocol"],
                        "mitre": s["mitre"],
                        "status": s["status"],
                    }
                ),
                "sms_sent": 1,
                "sms_to": soc_to,
                "sms_body": f"[{sev}] ATTACK {s['attack_type']} → "
                f"{s['target_node']} | {s['status']}",
                "ack": 0,
            }
        )
    return alerts


# Small local helper so this module stays dependency-free
def json_dumps(obj):
    import json

    return json.dumps(obj)
