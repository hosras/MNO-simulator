"""
================================================================
 TELECOM-ATTACK-SIM v1.0
 Local-only attack scenario simulator for resilience testing
 + Signaling attacks (SS7, Diameter, GTP, PFCP, SIP)
 + DDoS / Flood attacks (HTTP/2, UDP, SCTP)
 + RAN / O-RAN attacks (E2, A1, F1)
 + Persists to telecom_sim.db: attack_events, attack_scenarios
 WARNING: simulation only - no packets leave the host
================================================================
"""

import json
import random
from datetime import datetime, timedelta

from telecom_common import SOC_RECIPIENTS, db_connect

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
# SCHEMA
# ------------------------------------------------------------------
def init_attack_tables():
    con = db_connect()
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS attack_scenarios(
        scenario_id TEXT PRIMARY KEY,
        name TEXT,
        attack_type TEXT,
        target_layer TEXT,
        target_node TEXT,
        target_iface TEXT,
        protocol TEXT,
        severity TEXT,
        start_ts TEXT,
        end_ts TEXT,
        duration_sec INT,
        rate_pps INT,
        total_events INT,
        source_ip TEXT,
        mitre TEXT,
        status TEXT,
        notes TEXT
    );
    CREATE TABLE IF NOT EXISTS attack_events(
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        scenario_id TEXT,
        ts TEXT,
        attack_type TEXT,
        target_node TEXT,
        source_ip TEXT,
        pps INT,
        latency_ms REAL,
        drop_pct REAL,
        detected INT,
        detected_by TEXT,
        blocked INT,
        mttd_sec REAL,
        mttr_sec REAL,
        severity TEXT,
        notes TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_atk_scen ON attack_events(scenario_id);
    CREATE INDEX IF NOT EXISTS idx_atk_ts   ON attack_events(ts);
    CREATE INDEX IF NOT EXISTS idx_atk_type ON attack_events(attack_type);
    """)
    con.commit()
    con.close()


# ------------------------------------------------------------------
# PICK TARGET
# ------------------------------------------------------------------
def _build_target_index() -> dict:
    """One-shot DB read: cache role -> [node_id] and 5G/6G cell lists.

    Called once per generate_attack_scenarios() run so that _pick_target()
    does not open a new SQLite connection for every scenario.
    """
    idx = {
        "cores": {},  # role -> [node_id, ...]
        "all_cores": [],  # every node_id
        "cells_5g": [],  # 5G cell_ids (for ORAN_* attacks)
        "cells_6g": [],  # 6G cell_ids (for THZ_JAMMING)
    }
    try:
        con = db_connect()
        try:
            for role, node_id in con.execute("SELECT role, node_id FROM cores"):
                idx["cores"].setdefault(role, []).append(node_id)
                idx["all_cores"].append(node_id)
            idx["cells_5g"] = [
                r[0] for r in con.execute("SELECT cell_id FROM cells WHERE tech='5G'")
            ]
            idx["cells_6g"] = [
                r[0] for r in con.execute("SELECT cell_id FROM cells WHERE tech='6G'")
            ]
        finally:
            con.close()
    except Exception:
        # leave whatever partial data we managed to read; the picker
        # will fall back to UNKNOWN if the pool is empty.
        pass
    return idx


def _pick_target(attack_type: str, idx: dict) -> str:
    """Pick a plausible target node for the attack type using the
    pre-built index returned by _build_target_index()."""
    roles = []
    pool = None  # explicit pool overrides roles lookup

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
# SCENARIO GENERATOR
# ------------------------------------------------------------------
def generate_attack_scenarios(n: int = 25) -> list[dict]:
    """Generate n random attack scenarios with plausible timings.

    Picks attack types from ATTACK_CATALOG, resolves a target node
    from the DB (via _build_target_index), and assigns:
      - realistic start/end timestamps within the last 24h,
      - a rate (pps) drawn from the attack family's typical range,
      - a status in {BLOCKED, DETECTED, SUCCESS, ONGOING}.

    Guarantees a share of 6G scenarios (RIS_PHASE_POISON, AI_RAN_POISON,
    THZ_JAMMING, QUIC_FLOOD_6G) so 6G is always represented.

    Args:
        n: Number of scenarios to generate. Default 25.

    Returns:
        List of dicts, each with the schema of the `attack_scenarios`
        table (see init_attack_tables()).
    """
    init_attack_tables()
    _target_idx = _build_target_index()  # one DB read
    scenarios = []
    now = datetime.now()
    all_types = list(ATTACK_CATALOG.keys())
    # Actually guarantee a share of 6G scenarios,
    # instead of only reordering the list (which random.choice ignored).
    _forced_6g = [
        a
        for a in ("RIS_PHASE_POISON", "AI_RAN_POISON", "THZ_JAMMING", "QUIC_FLOOD_6G")
        if a in ATTACK_CATALOG
    ]
    n_forced = min(len(_forced_6g), n)
    chosen_types = random.sample(_forced_6g, k=n_forced)
    other_types = [t for t in all_types if t not in _forced_6g]
    if n > n_forced and other_types:
        chosen_types += random.choices(other_types, k=n - n_forced)
    random.shuffle(chosen_types)

    for i, atype in enumerate(chosen_types):
        meta = ATTACK_CATALOG[atype]

        # Timing: attacks typically bursty, short-lived
        start = now - timedelta(hours=random.uniform(0, 24), minutes=random.uniform(0, 60))
        dur = random.choice([10, 30, 60, 120, 300, 600, 1800])
        end = start + timedelta(seconds=dur)

        # Rate depends on family
        base_rate = {
            "signaling": (500, 50_000),
            "ddos": (10_000, 2_000_000),
            "ran": (100, 20_000),
            "recon": (5, 500),
            "exfil": (10, 2_000),
        }.get(meta["family"], (100, 10_000))
        rate = random.randint(*base_rate)

        total_events = int(rate * dur * random.uniform(0.7, 1.0))

        scenario = {
            "scenario_id": f"ATK-{now.strftime('%Y%m%d')}-{i+1:04d}",
            "name": f"{atype} on {meta['target_iface']}",
            "attack_type": atype,
            "target_layer": meta["layer"],
            "target_node": _pick_target(atype, _target_idx),
            "target_iface": meta["target_iface"],
            "protocol": meta["protocol"],
            "severity": meta["severity"],
            "start_ts": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_ts": end.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_sec": dur,
            "rate_pps": rate,
            "total_events": total_events,
            "source_ip": f"{random.randint(1,223)}.{random.randint(0,255)}."
            f"{random.randint(0,255)}.{random.randint(1,254)}",
            "mitre": meta["mitre"],
            "status": random.choices(
                ["BLOCKED", "DETECTED", "SUCCESS", "ONGOING"], weights=[0.5, 0.35, 0.1, 0.05]
            )[0],
            "notes": meta["desc"],
        }
        scenarios.append(scenario)
    return scenarios


# ------------------------------------------------------------------
# EVENT EXPANSION (time-series samples per scenario)
# ------------------------------------------------------------------
def expand_events(scenarios: list[dict], samples_per_scenario: int = 20) -> list[dict]:
    events = []
    for s in scenarios:
        start = datetime.strptime(s["start_ts"], "%Y-%m-%d %H:%M:%S")
        dur = s["duration_sec"]
        for k in range(samples_per_scenario):
            offset = dur * k / samples_per_scenario
            ts = start + timedelta(seconds=offset)

            # Detection happens after some delay (MTTD)
            mttd = random.uniform(3, 90) if s["status"] != "SUCCESS" else None
            detected = 1 if mttd is not None and k * dur / samples_per_scenario >= mttd else 0

            # Blocking after MTTD + response time
            mttr = None
            blocked = 0
            if detected:
                mttr = random.uniform(15, 600)
                if k * dur / samples_per_scenario >= mttd + mttr:
                    blocked = 1

            # KPI impact
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
# ALERT GENERATION FROM ATTACKS
# ------------------------------------------------------------------
def attacks_to_alerts(scenarios: list[dict], events: list[dict]) -> list[dict]:
    """Convert attack scenarios into alert rows for the alerts table.

    Only scenarios that are DETECTED, SUCCESS, or ONGOING — or that
    carry CRITICAL severity — become alerts. Each alert routes to one
    of SOC_RECIPIENTS and includes an SMS body preview.

    Args:
        scenarios: List of scenario dicts.
        events:    List of event dicts (currently unused; kept for
                   future KPI enrichment).

    Returns:
        List of dicts matching the `alerts` table schema
        (alert_id, timestamp, severity, alert_type, msisdn, ...).
    """
    alerts = []
    ts_now = datetime.now()
    ts_suffix = ts_now.strftime("%H%M%S")  # avoid collisions across runs
    # Only alert on non-blocked or high-severity attacks
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
                "extra": json.dumps(
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


# ------------------------------------------------------------------
# PERSIST
# ------------------------------------------------------------------
def persist_attacks(scenarios: list[dict], events: list[dict]) -> None:
    init_attack_tables()
    con = db_connect()
    cur = con.cursor()

    # Wipe previous run
    cur.execute("DELETE FROM attack_scenarios")
    cur.execute("DELETE FROM attack_events")

    cur.executemany(
        """INSERT INTO attack_scenarios VALUES(
        :scenario_id,:name,:attack_type,:target_layer,:target_node,
        :target_iface,:protocol,:severity,:start_ts,:end_ts,
        :duration_sec,:rate_pps,:total_events,:source_ip,:mitre,
        :status,:notes)""",
        scenarios,
    )

    cur.executemany(
        """INSERT INTO attack_events(
        scenario_id,ts,attack_type,target_node,source_ip,pps,
        latency_ms,drop_pct,detected,detected_by,blocked,
        mttd_sec,mttr_sec,severity,notes) VALUES(
        :scenario_id,:ts,:attack_type,:target_node,:source_ip,:pps,
        :latency_ms,:drop_pct,:detected,:detected_by,:blocked,
        :mttd_sec,:mttr_sec,:severity,:notes)""",
        events,
    )

    con.commit()
    con.close()


def inject_attack_alerts(alerts: list[dict]) -> None:
    """Merge attack-derived alerts into the alerts table."""
    if not alerts:
        return
    con = db_connect()
    cur = con.cursor()
    # wipe previous ATTACK_* alerts and their SMS
    try:
        cur.execute(
            "DELETE FROM sms_alerts WHERE alert_id IN "
            "(SELECT alert_id FROM alerts "
            "WHERE alert_type LIKE 'ATTACK_%')"
        )
        cur.execute("DELETE FROM alerts " "WHERE alert_type LIKE 'ATTACK_%'")
        con.commit()
    except Exception:
        pass
    for a in alerts:
        try:
            cur.execute(
                """INSERT OR IGNORE INTO alerts(
                alert_id,timestamp,severity,alert_type,msisdn,description,
                extra,sms_sent,sms_to,sms_body,ack) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    a["alert_id"],
                    a["timestamp"],
                    a["severity"],
                    a["alert_type"],
                    a["msisdn"],
                    a["description"],
                    a["extra"],
                    a["sms_sent"],
                    a["sms_to"],
                    a["sms_body"],
                    a["ack"],
                ),
            )
            if a["sms_sent"]:
                cur.execute(
                    """INSERT INTO sms_alerts(
                    alert_id,timestamp,recipient,body,status)
                    VALUES(?,?,?,?,?)""",
                    (a["alert_id"], a["timestamp"], a["sms_to"], a["sms_body"], "DELIVERED"),
                )
        except Exception:
            pass
    con.commit()
    con.close()


# ------------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------------
def run_attack_simulation(
    n_scenarios: int = 25, samples_per_scenario: int = 20, inject_alerts: bool = True
) -> dict:
    """End-to-end attack simulation: generate → persist → alert.

    Pipeline:
        1. generate_attack_scenarios(n_scenarios)
        2. expand_events(...) → time-series
        3. persist_attacks(...) → attack_scenarios + attack_events tables
        4. attacks_to_alerts(...) → alert rows
        5. inject_attack_alerts(...) → merge into alerts + sms_alerts

    Args:
        n_scenarios:         Number of attack scenarios to generate.
        samples_per_scenario: Event samples per scenario.
        inject_alerts:       If True, merge into alerts/sms_alerts tables.

    Returns:
        Summary dict:
            {
              "scenarios": int,
              "events":    int,
              "alerts":    int,
              "by_status":   {status: count, ...},
              "by_severity": {severity: count, ...},
            }
    """
    print(f"[ATTACK] Generating {n_scenarios} scenarios...")
    scenarios = generate_attack_scenarios(n_scenarios)
    print("[ATTACK] Expanding to event time-series...")
    events = expand_events(scenarios, samples_per_scenario)
    print(f"[ATTACK] Persisting {len(scenarios)} scenarios, {len(events)} events...")
    persist_attacks(scenarios, events)
    alerts = attacks_to_alerts(scenarios, events)
    if inject_alerts and alerts:
        print(f"[ATTACK] Injecting {len(alerts)} alerts into alerts table...")
        inject_attack_alerts(alerts)
    summary = {
        "scenarios": len(scenarios),
        "events": len(events),
        "alerts": len(alerts),
        "by_status": {},
        "by_severity": {},
    }
    for s in scenarios:
        summary["by_status"][s["status"]] = summary["by_status"].get(s["status"], 0) + 1
        summary["by_severity"][s["severity"]] = summary["by_severity"].get(s["severity"], 0) + 1
    return summary


if __name__ == "__main__":
    summary = run_attack_simulation()
    print(json.dumps(summary, indent=2))
