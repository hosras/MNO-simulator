# -*- coding: utf-8 -*-
"""
================================================================
 TELECOM-NET-SIM v3.0
 Comprehensive Mobile Network Simulator
 + OSINT / SIGINT Analysis
 + Special Lines (VIP/Government/Emergency/Test)
 + Filter Bypass & CLIR (No Caller ID)
 + End-to-End Encryption (incl. quantum-safe)
 + Alert Engine + SMS Dispatch to SOC
 + Voice Bearers: VoLTE / VoWiFi / VoNR / CSFB
 + Messaging: SMS / MMS / RCS
 Fully local data generation - no external calls
================================================================
"""
import os, json, math, random, sqlite3, hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter
from typing import List, Dict, Tuple

from telecom_common import CIPHER_SUITES

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_PLOT = True
except Exception:
    HAS_PLOT = False

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
OPERATOR = "TELECOM"
MCC, MNC = "432", "99"
SEED = 1403
OUT = "telecom_sim_output"
os.makedirs(OUT, exist_ok=True)
DB = os.path.join(OUT, "telecom_sim.db")

random.seed(SEED)

CITIES = [
    ("Tehran",     35.6892, 51.3890, 12_000_000, 0.35),
    ("Mashhad",    36.2605, 59.6168,  3_400_000, 0.14),
    ("Isfahan",    32.6546, 51.6680,  2_200_000, 0.10),
    ("Karaj",      35.8400, 50.9391,  1_900_000, 0.09),
    ("Shiraz",     29.5918, 52.5837,  1_800_000, 0.08),
    ("Tabriz",     38.0800, 46.2919,  1_700_000, 0.07),
    ("Qom",        34.6401, 50.8764,  1_200_000, 0.05),
    ("Ahvaz",      31.3183, 48.6706,  1_300_000, 0.05),
    ("Kermanshah", 34.3142, 47.0650,    950_000, 0.035),
    ("Urmia",      37.5527, 45.0761,    800_000, 0.035),
]

# ------------------------------------------------------------------
# SPECIAL LINES / PRIVILEGED ACCESS CLASSES
# ------------------------------------------------------------------
LINE_CLASSES = ["Normal", "VIP", "Government", "Corporate", "Emergency", "Test"]
LINE_WEIGHTS = [0.900,   0.030,  0.020,       0.040,      0.005,      0.005]

QOS_BY_CLASS = {
    "Normal":     (0, 2),
    "VIP":        (6, 8),
    "Government": (7, 9),
    "Corporate":  (4, 6),
    "Emergency":  (9, 9),
    "Test":       (3, 5),
}

FILTER_BYPASS_CLASSES = {"Government", "Emergency", "Test", "Corporate"}
CLIR_AUTHORIZED       = {"Government", "Emergency", "Test", "VIP"}
CLIR_OVERRIDE_CLASSES = {"Government", "Emergency"}

# ------------------------------------------------------------------
# ENCRYPTION PROFILES
# ------------------------------------------------------------------
MANDATORY_ENCRYPTION = {"Government", "Emergency"}
OPTIONAL_ENCRYPTION  = {"Test", "VIP", "Corporate"}

# ------------------------------------------------------------------
# ALERT ENGINE RULES
# ------------------------------------------------------------------
ALERT_RULES = {
    "CRITICAL_CLIR_ABUSE":      {"severity": "CRITICAL", "threshold": 1},
    "CRITICAL_ENCRYPTION_FAIL": {"severity": "CRITICAL", "threshold": 1},
    "HIGH_FILTER_BYPASS":       {"severity": "HIGH",     "threshold": 5},
    "HIGH_SIMBOX":              {"severity": "HIGH",     "threshold": 1},
    "MEDIUM_IMPOSSIBLE_TRAVEL": {"severity": "MEDIUM",   "threshold": 1},
    "MEDIUM_LI_MISS":           {"severity": "MEDIUM",   "threshold": 1},
    "MEDIUM_VOLTE_FALLBACK":    {"severity": "MEDIUM",   "threshold": 3},
    "LOW_WEAK_CELL":            {"severity": "LOW",      "threshold": 10},
    "LOW_LARGE_MMS":            {"severity": "LOW",      "threshold": 1},
}

SOC_RECIPIENTS = ["989120000001", "989120000002", "989120000003"]

# ------------------------------------------------------------------
# VOICE / MESSAGING ENHANCEMENTS
# ------------------------------------------------------------------
CALL_TYPES = ["voice", "sms", "mms", "data", "ussd", "rcs"]

VOICE_BEARERS = {
    "VoLTE":    {"qci": 1, "codec": ["AMR-WB", "EVS", "AMR-NB"],
                 "min_tech": "4G", "sig": "SIP"},
    "VoWiFi":   {"qci": 1, "codec": ["AMR-WB", "EVS"],
                 "min_tech": "WiFi", "sig": "SIP-over-IPSec"},
    "VoNR":     {"qci": 1, "codec": ["EVS"],
                 "min_tech": "5G", "sig": "SIP"},
    "CSFB":     {"qci": 0, "codec": ["AMR-NB"],
                 "min_tech": "2G/3G", "sig": "SS7"},
    "Vo6G":   {"qci": 1, "codec": ["EVS-Stereo", "IVAS", "EVS"],
               "min_tech": "6G", "sig": "SIP-over-QUIC"},
}

MMS_CONTENT_TYPES = ["image/jpeg", "image/png", "video/mp4", "audio/mpeg",
                     "application/pdf", "text/vcard", "application/vnd.wap.multipart"]

MMS_SIZE_BY_TYPE = {
    "image/jpeg":                    (50_000,   800_000),
    "image/png":                     (30_000,   500_000),
    "video/mp4":                     (800_000,  8_000_000),
    "audio/mpeg":                    (100_000,  3_000_000),
    "application/pdf":               (80_000,   2_000_000),
    "text/vcard":                    (500,      5_000),
    "application/vnd.wap.multipart": (200_000,  4_000_000),
}

RCS_TYPES = ["chat", "file-transfer", "location-share", "rich-card", "group-chat"]

# ------------------------------------------------------------------
# UTILS
# ------------------------------------------------------------------
def luhn(number: str) -> str:
    d = [int(x) for x in number]
    for i in range(len(d)-1, -1, -2):
        d[i] *= 2
        if d[i] > 9: d[i] -= 9
    return str((10 - sum(d) % 10) % 10)

def gen_imsi() -> str:
    return f"{MCC}{MNC}" + "".join(random.choices("0123456789", k=10))

MSISDN_PREFIXES = ["910","911","912","913","914","915","916","917","918","919",
                   "901","902","903","905",
                   "930","933","935","936","937","938","939",
                   "920","921","922"]
def gen_msisdn() -> str:
    return "98" + random.choice(MSISDN_PREFIXES) + "".join(random.choices("0123456789", k=7))

IMEI_TACS = ["35674108","35674208","35875108","35294808","86754503",
             "86754603","35061234","35296408","86012345","35879005"]
def gen_imei() -> str:
    p = random.choice(IMEI_TACS) + "".join(random.choices("0123456789", k=6))
    return p + luhn(p)

def haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

# ------------------------------------------------------------------
# 1) TOPOLOGY
# ------------------------------------------------------------------
@dataclass
class CellSite:
    cell_id: str
    name: str
    tech: str
    city: str
    lat: float
    lon: float
    band: str
    azimuth: int
    tilt: int
    tx_dbm: float
    backhaul_gbps: float

@dataclass
class CoreNode:
    node_id: str
    name: str
    role: str
    tech: str
    city: str
    capacity_tps: int

BANDS = {
    "2G": ["GSM-900", "GSM-1800"],
    "3G": ["UMTS-2100", "UMTS-900"],
    "4G": ["LTE-B3", "LTE-B7", "LTE-B20", "LTE-B1"],
    "5G": ["NR-n78", "NR-n41", "NR-n28"],
    "6G": ["THz-140", "THz-220", "sub-THz-300", "mmWave-28"],
}

def build_topology():
    cells: List[CellSite] = []
    counters = defaultdict(int)
    for city, lat, lon, pop, _w in CITIES:
        n4 = max(8, int(pop / 250_000))
        n5 = max(3, int(n4 * 0.35))
        n6 = max(1, int(n5 * 0.40))
        n3 = max(3, int(n4 * 0.4))
        n2 = max(3, int(n4 * 0.5))
        for tech, n in [("2G", n2), ("3G", n3), ("4G", n4),
                        ("5G", n5), ("6G", n6)]:
            for i in range(n):
                counters[tech] += 1
                cid = f"{tech}-{city[:3].upper()}-{counters[tech]:04d}"
                cells.append(CellSite(
                    cell_id=cid,
                    name=f"{city}-{tech}-{i+1}",
                    tech=tech, city=city,
                    lat=lat + random.uniform(-0.20, 0.20),
                    lon=lon + random.uniform(-0.25, 0.25),
                    band=random.choice(BANDS[tech]),
                    azimuth=random.choice([0,30,60,90,120,150,180,210,240,270,300,330]),
                    tilt=random.choice([2,4,6,8,10]),
                    tx_dbm=round(random.uniform(20, 46), 1),
                    backhaul_gbps=round(
                        random.uniform(1, 10)   if tech in ("2G","3G") else
                        random.uniform(80, 200) if tech == "6G" else
                        random.uniform(10, 40), 1),
                ))
    cores: List[CoreNode] = []
    core_plan = [
        ("MSC", "2G/3G", 12), ("BSC", "2G", 20), ("RNC", "3G", 10),
        ("MME", "4G", 8), ("SGW", "4G", 8), ("PGW", "4G", 8),
        ("HSS", "4G/5G", 4), ("PCRF", "4G", 4),
        ("AMF", "5G", 6), ("SMF", "5G", 6), ("UPF", "5G", 10),
        ("IMS", "VoLTE/VoWiFi", 6), ("MMSC", "MMS", 3), ("RCS-AS", "RCS", 3),
        ("NWDAF",  "6G", 4), ("RIS-C",  "6G", 3),
        ("ISAC",   "6G", 2), ("AI-RAN", "6G", 2),
    ]
    idx = 0
    for role, tech, count in core_plan:
        for i in range(count):
            idx += 1
            city = random.choice(CITIES)[0]
            cores.append(CoreNode(
                node_id=f"{role}-{i+1:02d}",
                name=f"{OPERATOR}-{role}-{city[:3].upper()}-{i+1:02d}",
                role=role, tech=tech, city=city,
                capacity_tps=random.choice([50_000, 100_000, 200_000, 400_000]),
            ))
    return cells, cores

# ------------------------------------------------------------------
# 2) SUBSCRIBERS
# ------------------------------------------------------------------
@dataclass
class Subscriber:
    msisdn: str
    imsi: str
    imei: str
    city: str
    plan: str
    kyc_age_days: int
    roaming_enabled: bool
    risk_score: float
    # Special line attributes
    line_class: str
    international_access: bool
    filter_bypass: bool
    clir_enabled: bool
    clir_override: bool
    priority_qos: int
    lawful_intercept: bool
    direct_routing: bool
    whitelisted_asns: List[str] = field(default_factory=list)
    # Encryption attributes
    encryption_required: bool = False
    cipher_suite: str = "None"
    key_id: str = ""
    key_rotation_days: int = 0
    e2e_enabled: bool = False

PLANS = ["Prepaid-Basic", "Prepaid-Plus", "Postpaid-Silver",
         "Postpaid-Gold", "Postpaid-Business", "IoT-M2M"]

def build_subscribers(n: int = 5000) -> List[Subscriber]:
    subs = []
    used_msisdn = set()
    used_imsi   = set()
    city_choices = random.choices(
        [c[0] for c in CITIES], weights=[c[4] for c in CITIES], k=n
    )
    for i in range(n):
        # --- Guarantee unique MSISDN ---
        while True:
            msisdn = gen_msisdn()
            if msisdn not in used_msisdn:
                used_msisdn.add(msisdn)
                break

        # --- Guarantee unique IMSI ---
        while True:
            imsi = gen_imsi()
            if imsi not in used_imsi:
                used_imsi.add(imsi)
                break

        imei = gen_imei()

        line_class = random.choices(LINE_CLASSES, weights=LINE_WEIGHTS)[0]
        qos_lo, qos_hi = QOS_BY_CLASS[line_class]

        intl_access   = line_class in {"Government","Corporate","VIP","Emergency","Test"} \
                        or random.random() < 0.08
        filter_bypass = line_class in FILTER_BYPASS_CLASSES \
                        or (line_class == "VIP" and random.random() < 0.3)
        clir_enabled  = line_class in CLIR_AUTHORIZED
        clir_override = line_class in CLIR_OVERRIDE_CLASSES
        lawful        = line_class in {"Government", "Emergency"} \
                        or (line_class == "VIP" and random.random() < 0.05)
        direct_route  = line_class in {"Government", "Emergency", "Corporate"}

        whitelisted = []
        if filter_bypass:
            whitelisted = random.sample(
                ["AS15169","AS13335","AS16509","AS32934","AS8075","AS20940"],
                k=random.randint(1, 4)
            )

        enc_required = line_class in MANDATORY_ENCRYPTION
        if enc_required:
            e2e = True
        elif line_class in OPTIONAL_ENCRYPTION:
            e2e = random.random() < 0.6
        else:
            e2e = False

        if e2e:
            if line_class in MANDATORY_ENCRYPTION:
                cipher = random.choices(
                    ["Kyber-1024+AES-256", "AES-256-GCM", "ChaCha20-Poly1305"],
                    weights=[0.5, 0.3, 0.2])[0]
            else:
                cipher = random.choice(list(CIPHER_SUITES.keys()))
            key_id = "KEY-" + hashlib.sha1(
                f"{imsi}{random.random()}".encode()
            ).hexdigest()[:16].upper()
            rot_days = random.choice([30, 60, 90, 180])
        else:
            cipher = "None"; key_id = ""; rot_days = 0

        subs.append(Subscriber(
            msisdn=msisdn, imsi=imsi, imei=imei,
            city=city_choices[i],
            plan=random.choices(PLANS, weights=[40,25,15,10,5,5])[0],
            kyc_age_days=random.randint(1, 3000),
            roaming_enabled=random.random() < 0.15 or intl_access,
            risk_score=round(random.betavariate(2, 8), 3),
            line_class=line_class,
            international_access=intl_access,
            filter_bypass=filter_bypass,
            clir_enabled=clir_enabled,
            clir_override=clir_override,
            priority_qos=random.randint(qos_lo, qos_hi),
            lawful_intercept=lawful,
            direct_routing=direct_route,
            whitelisted_asns=whitelisted,
            encryption_required=enc_required,
            cipher_suite=cipher,
            key_id=key_id,
            key_rotation_days=rot_days,
            e2e_enabled=e2e,
        ))
    return subs

# ------------------------------------------------------------------
# 3) CDR GENERATION
# ------------------------------------------------------------------
def signal_metrics(tech: str):
    if tech == "2G":
        return {"rssi": round(random.uniform(-95,-60),1),
                "rsrp": None, "rsrq": None, "sinr": None}
    if tech == "3G":
        return {"rssi": round(random.uniform(-95,-55),1),
                "rsrp": None, "rsrq": None, "sinr": None}
    if tech == "4G":
        return {"rsrp": round(random.uniform(-125,-65),1),
                "rsrq": round(random.uniform(-20,-3),1),
                "sinr": round(random.uniform(-5,30),1),
                "rssi": None}
    if tech == "6G":
        return {"rsrp": round(random.uniform(-95,-50),1),
                "rsrq": round(random.uniform(-12,-1),1),
                "sinr": round(random.uniform(10,45),1),
                "rssi": None}
    return {"rsrp": round(random.uniform(-120,-60),1),
            "rsrq": round(random.uniform(-18,-2),1),
            "sinr": round(random.uniform(0,35),1),
            "rssi": None}

def gen_cdrs(subs, cells, n: int = 60_000) -> List[dict]:
    by_city_cells = defaultdict(list)
    for c in cells:
        by_city_cells[c.city].append(c)

    start = datetime.now() - timedelta(days=7)
    cdrs = []
    suspect_sims = set(random.sample([s.imsi for s in subs], k=max(5, len(subs)//500)))
    suspect_imei = [gen_imei() for _ in range(30)]

    for i in range(n):
        s = random.choice(subs)
        cell = random.choice(by_city_cells[s.city])
        ts = start + timedelta(seconds=random.randint(0, 7*24*3600))

        # NEW: expanded call type weights
        ctype = random.choices(CALL_TYPES,
                               weights=[48, 16, 5, 22, 3, 6])[0]
        # voice=48%, sms=16%, mms=5%, data=22%, ussd=3%, rcs=6%

        imei_used = s.imei
        if s.imsi in suspect_sims and random.random() < 0.35:
            imei_used = random.choice(suspect_imei)

        dur = 0
        bytes_ = 0

        # NEW: Voice bearer & messaging metadata
        voice_bearer    = None
        voice_codec     = None
        voice_qci       = None
        voice_sig_proto = None
        mms_content     = None
        mms_size_bytes  = 0
        mms_delivery    = None
        rcs_type        = None

        if ctype == "voice":
            dur = random.choice([random.randint(5, 120), random.randint(120, 1800)])

            if cell.tech == "6G":
                voice_bearer = "Vo6G"
            elif cell.tech == "5G" and s.priority_qos >= 6:
                voice_bearer = "VoNR"
            elif cell.tech == "4G":
                if s.line_class in ("Government","Emergency","VIP"):
                    voice_bearer = "VoLTE"
                else:
                    voice_bearer = random.choices(
                        ["VoLTE", "VoWiFi", "CSFB"], weights=[0.70, 0.15, 0.15])[0]
            elif cell.tech == "3G":
                voice_bearer = random.choices(["CSFB", "VoWiFi"], weights=[0.85, 0.15])[0]
            else:  # 2G
                voice_bearer = "CSFB"

            bearer_cfg      = VOICE_BEARERS[voice_bearer]
            voice_codec     = random.choice(bearer_cfg["codec"])
            voice_qci       = bearer_cfg["qci"]
            voice_sig_proto = bearer_cfg["sig"]

        elif ctype == "sms":
            dur = 0; bytes_ = random.randint(60, 480)

        elif ctype == "mms":
            mms_content = random.choice(MMS_CONTENT_TYPES)
            lo, hi = MMS_SIZE_BY_TYPE[mms_content]
            mms_size_bytes = random.randint(lo, hi)
            bytes_ = mms_size_bytes
            dur = random.randint(2, 30)
            mms_delivery = random.choices(
                ["DELIVERED", "EXPIRED", "REJECTED", "PENDING"],
                weights=[0.88, 0.05, 0.05, 0.02])[0]

        elif ctype == "rcs":
            rcs_type = random.choice(RCS_TYPES)
            dur = random.randint(1, 10)
            bytes_ = random.randint(2_000, 500_000)

        elif ctype == "data":
            dur = random.randint(10, 600)
            bytes_ = random.randint(50_000, 50_000_000)

        else:  # ussd
            dur = random.randint(3, 15)

        result = random.choices(["ANSWERED", "NO_ANSWER", "BUSY", "FAILED"],
                                weights=[80, 10, 5, 5])[0] if ctype == "voice" else "OK"
        if ctype == "mms":
            result = mms_delivery

        sig = signal_metrics(cell.tech)

        # Special-line behaviour
        is_international = (s.international_access and ctype == "data"
                            and random.random() < 0.25)
        clir_used = False
        if s.clir_enabled and ctype in ("voice","sms","mms") and random.random() < 0.35:
            clir_used = True
        elif (not s.clir_enabled) and ctype in ("voice","sms","mms") and random.random() < 0.01:
            clir_used = True

        if s.direct_routing:
            routing_class = "Direct"
        elif s.priority_qos >= 6:
            routing_class = "Priority"
        elif is_international:
            routing_class = "International"
        else:
            routing_class = "Normal"

        filter_applied = not s.filter_bypass

        # Encryption status
        encrypted = s.e2e_enabled and ctype in ("voice", "sms", "mms", "data", "rcs")
        cipher_used = s.cipher_suite if encrypted else "None"
        enc_failure = encrypted and random.random() < 0.01
        if enc_failure:
            encrypted = False
            cipher_used = "FAILED"

        cdrs.append({
            "record_id": f"CDR-{i+1:08d}",
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "msisdn": s.msisdn,
            "imsi": s.imsi,
            "imei": imei_used,
            "called": gen_msisdn() if ctype in ("voice","sms","mms","rcs") else None,
            "call_type": ctype,
            "duration_sec": dur,
            "bytes": bytes_,
            "result": result,
            "cell_id": cell.cell_id,
            "tech": cell.tech,
            "city": cell.city,
            "lat": cell.lat, "lon": cell.lon,
            "rssi": sig.get("rssi"),
            "rsrp": sig.get("rsrp"),
            "rsrq": sig.get("rsrq"),
            "sinr": sig.get("sinr"),
            "clir_used": clir_used,
            "routing_class": routing_class,
            "filter_applied": filter_applied,
            "international": is_international,
            "line_class": s.line_class,
            "priority_qos": s.priority_qos,
            "encrypted": encrypted,
            "cipher_suite": cipher_used,
            "encryption_failure": enc_failure,
            "key_id": s.key_id if s.e2e_enabled else "",
            "voice_bearer": voice_bearer,
            "voice_codec": voice_codec,
            "voice_qci": voice_qci,
            "voice_sig_proto": voice_sig_proto,
            "mms_content_type": mms_content,
            "mms_size_bytes": mms_size_bytes,
            "mms_delivery": mms_delivery,
            "rcs_type": rcs_type,
        })
    return cdrs

# ------------------------------------------------------------------
# 4) OSINT MODULE
# ------------------------------------------------------------------
def osint_collect(cells, subs):
    public_registry = []
    for c in random.sample(cells, k=min(150, len(cells))):
        public_registry.append({
            "cell_id": c.cell_id,
            "operator": OPERATOR,
            "mcc": MCC, "mnc": MNC,
            "lat": round(c.lat + random.uniform(-0.001,0.001), 6),
            "lon": round(c.lon + random.uniform(-0.001,0.001), 6),
            "tech": c.tech, "band": c.band,
            "source": random.choice(["crowd-sourced", "regulatory", "operator-public"]),
        })

    social_complaints = []
    complaint_topics = ["Outage", "Slow Internet", "Call Quality",
                        "Coverage", "Roaming", "SMS Delay", "MMS Failure",
                        "VoLTE Drop", "Billing", "Customer Support"]
    for _ in range(400):
        city = random.choice(CITIES)[0]
        social_complaints.append({
            "city": city,
            "topic": random.choice(complaint_topics),
            "sentiment": random.choices(["negative","neutral","positive"],
                                        weights=[0.7,0.2,0.1])[0],
            "source": random.choice(["Twitter/X","Instagram","Telegram","Forum","News"]),
        })

    dns_records = [
        {"name": f"www.{OPERATOR.lower()}.ir", "type": "A",
         "value": f"10.{random.randint(0,255)}.{random.randint(0,255)}.10"},
        {"name": f"api.{OPERATOR.lower()}.ir", "type": "A",
         "value": f"10.{random.randint(0,255)}.{random.randint(0,255)}.20"},
        {"name": f"mail.{OPERATOR.lower()}.ir", "type": "MX",
         "value": f"mx1.{OPERATOR.lower()}.ir"},
        {"name": f"ims.{OPERATOR.lower()}.ir", "type": "A",
         "value": f"10.{random.randint(0,255)}.{random.randint(0,255)}.30"},
        {"name": f"mmsc.{OPERATOR.lower()}.ir", "type": "A",
         "value": f"10.{random.randint(0,255)}.{random.randint(0,255)}.40"},
    ]
    asn_info = {"asn": "AS12345", "holder": OPERATOR, "country": "IR",
                "prefixes": [f"10.{random.randint(0,255)}.0.0/16" for _ in range(4)]}

    spectrum = [
        {"band": "GSM-900",  "licensee": OPERATOR, "valid_until": "2027-01-01"},
        {"band": "UMTS-2100","licensee": OPERATOR, "valid_until": "2028-06-01"},
        {"band": "LTE-B3",   "licensee": OPERATOR, "valid_until": "2030-03-01"},
        {"band": "NR-n78",   "licensee": OPERATOR, "valid_until": "2032-09-01"},
    ]
    return {
        "public_cell_registry": public_registry,
        "social_complaints": social_complaints,
        "dns_records": dns_records,
        "asn_info": asn_info,
        "spectrum_licenses": spectrum,
    }

def osint_report(osint_data):
    r = {}
    reg = osint_data["public_cell_registry"]
    r["registry_total"] = len(reg)
    r["registry_by_tech"] = dict(Counter(x["tech"] for x in reg))

    comp = osint_data["social_complaints"]
    r["complaints_total"] = len(comp)
    r["complaints_by_city"] = dict(Counter(x["city"] for x in comp).most_common())
    r["complaints_by_topic"] = dict(Counter(x["topic"] for x in comp).most_common())
    r["complaints_sentiment"] = dict(Counter(x["sentiment"] for x in comp))
    return r

# ------------------------------------------------------------------
# 5) SIGINT MODULE
# ------------------------------------------------------------------
def sigint_analyze(cdrs, cells):
    findings = {}

    # 5.1 IMEI churn
    imei_by_imsi = defaultdict(set)
    for c in cdrs:
        imei_by_imsi[c["imsi"]].add(c["imei"])
    imei_churn = {k: len(v) for k, v in imei_by_imsi.items() if len(v) >= 4}
    findings["imei_churn_suspects"] = sorted(imei_churn.items(),
                                             key=lambda x: -x[1])[:20]

    # 5.2 SIM-Box
    out_per_sim = defaultdict(list)
    for c in cdrs:
        if c["call_type"] == "voice" and c["called"]:
            out_per_sim[c["msisdn"]].append(c)
    simbox = []
    for msisdn, rows in out_per_sim.items():
        uniq = len({r["called"] for r in rows})
        short_ratio = sum(1 for r in rows if 0 < r["duration_sec"] < 15) / max(1, len(rows))
        if uniq >= 50 and short_ratio > 0.6:
            simbox.append({"msisdn": msisdn, "out_calls": len(rows),
                           "unique_targets": uniq,
                           "short_call_ratio": round(short_ratio, 2)})
    findings["simbox_suspects"] = sorted(simbox, key=lambda x: -x["unique_targets"])[:15]

    # 5.3 Impossible Travel
    by_sub = defaultdict(list)
    for c in cdrs:
        by_sub[c["imsi"]].append(c)
    impossible = []
    cell_by_id = {c.cell_id: c for c in cells}
    for imsi, rows in by_sub.items():
        rows.sort(key=lambda r: r["timestamp"])
        for a, b in zip(rows, rows[1:]):
            if a["cell_id"] == b["cell_id"]:
                continue
            ca, cb = cell_by_id.get(a["cell_id"]), cell_by_id.get(b["cell_id"])
            if not ca or not cb: continue
            km = haversine(ca.lat, ca.lon, cb.lat, cb.lon)
            dt = (datetime.strptime(b["timestamp"], "%Y-%m-%d %H:%M:%S")
                  - datetime.strptime(a["timestamp"], "%Y-%m-%d %H:%M:%S")).total_seconds()
            if dt <= 0: continue
            speed = km / (dt / 3600.0)
            if speed > 900 and km > 100:
                impossible.append({"imsi": imsi, "msisdn": a["msisdn"],
                                   "from": ca.city, "to": cb.city,
                                   "km": round(km, 1),
                                   "dt_sec": int(dt),
                                   "speed_kmh": round(speed)})
    findings["impossible_travel"] = sorted(impossible, key=lambda x: -x["speed_kmh"])[:20]

    # 5.4 Signal Quality
    bad_signal = defaultdict(int)
    for c in cdrs:
        if c["tech"] in ("4G","5G") and c["rsrp"] is not None and c["rsrp"] < -110:
            bad_signal[c["cell_id"]] += 1
        if c["tech"] in ("4G","5G") and c["sinr"] is not None and c["sinr"] < 0:
            bad_signal[c["cell_id"]] += 1
    findings["weak_cells"] = sorted(bad_signal.items(), key=lambda x: -x[1])[:20]

    # 5.5 Traffic metadata
    by_hour = Counter()
    by_tech = Counter()
    by_city = Counter()
    by_type = Counter()
    for c in cdrs:
        by_hour[c["timestamp"][11:13]] += 1
        by_tech[c["tech"]] += 1
        by_city[c["city"]] += 1
        by_type[c["call_type"]] += 1
    findings["traffic_by_hour"] = dict(sorted(by_hour.items()))
    findings["traffic_by_tech"] = dict(by_tech)
    findings["traffic_by_city"] = dict(by_city.most_common())
    findings["traffic_by_type"] = dict(by_type)

    # 5.6 Special-line abuse
    clir_abuse = []
    bypass_users = defaultdict(int)
    intl_users = defaultdict(int)
    priority_events = defaultdict(int)

    for c in cdrs:
        if c.get("clir_used") and c.get("line_class") not in CLIR_AUTHORIZED:
            clir_abuse.append({
                "msisdn": c["msisdn"], "imsi": c["imsi"],
                "line_class": c["line_class"], "call_type": c["call_type"],
                "ts": c["timestamp"],
            })
        if (not c.get("filter_applied")) and c.get("international"):
            bypass_users[c["msisdn"]] += 1
        if c.get("international"):
            intl_users[c["msisdn"]] += 1
        if c.get("priority_qos", 0) >= 7:
            priority_events[c["line_class"]] += 1

    findings["clir_abuse"] = clir_abuse[:50]
    findings["filter_bypass_users"] = sorted(bypass_users.items(), key=lambda x: -x[1])[:20]
    findings["top_intl_users"] = sorted(intl_users.items(), key=lambda x: -x[1])[:20]
    findings["priority_by_class"] = dict(priority_events)

    # 5.7 Special lines inventory
    special_inventory = Counter(c.get("line_class") for c in cdrs)
    findings["special_line_traffic"] = dict(special_inventory)

    # 5.8 Encryption analysis
    enc_by_class = defaultdict(lambda: {"total": 0, "encrypted": 0, "failures": 0})
    cipher_usage = Counter()
    key_usage = Counter()
    enc_failures = []

    for c in cdrs:
        lc = c.get("line_class", "Unknown")
        enc_by_class[lc]["total"] += 1
        if c.get("encrypted"):
            enc_by_class[lc]["encrypted"] += 1
            cipher_usage[c.get("cipher_suite", "?")] += 1
            key_usage[c.get("key_id", "?")] += 1
        if c.get("encryption_failure"):
            enc_by_class[lc]["failures"] += 1
            enc_failures.append({
                "msisdn": c["msisdn"], "imsi": c["imsi"],
                "line_class": lc, "ts": c["timestamp"],
                "cipher": c.get("cipher_suite"),
            })

    findings["encryption_coverage"] = {
        k: {
            "total": v["total"],
            "encrypted": v["encrypted"],
            "failures": v["failures"],
            "coverage_pct": round(100 * v["encrypted"] / max(1, v["total"]), 2),
        } for k, v in enc_by_class.items()
    }
    findings["cipher_usage"] = dict(cipher_usage.most_common())
    findings["key_usage"] = dict(key_usage.most_common(20))
    findings["encryption_failures"] = enc_failures[:50]

    # 5.9 Voice bearer / VoLTE analysis
    voice_bearers  = Counter()
    voice_codecs   = Counter()
    voice_qci      = Counter()
    volte_fallback = []
    volte_per_tech = defaultdict(Counter)

    for c in cdrs:
        if c["call_type"] != "voice":
            continue
        vb = c.get("voice_bearer")
        if not vb: continue
        voice_bearers[vb] += 1
        voice_codecs[c.get("voice_codec", "?")] += 1
        voice_qci[c.get("voice_qci", 0)] += 1
        volte_per_tech[c["tech"]][vb] += 1

        if c["tech"] in ("4G","5G") and vb == "CSFB":
            volte_fallback.append({
                "msisdn": c["msisdn"], "tech": c["tech"],
                "ts": c["timestamp"], "cell_id": c["cell_id"],
            })

    findings["voice_bearers"]  = dict(voice_bearers.most_common())
    findings["voice_codecs"]   = dict(voice_codecs.most_common())
    findings["voice_qci"]      = dict(voice_qci.most_common())
    findings["voice_per_tech"] = {k: dict(v) for k, v in volte_per_tech.items()}
    findings["volte_fallback"] = volte_fallback[:30]

    # 5.10 MMS analysis
    mms_by_content  = Counter()
    mms_by_delivery = Counter()
    mms_total_bytes = 0
    mms_suspects    = []

    for c in cdrs:
        if c["call_type"] != "mms":
            continue
        ct = c.get("mms_content_type", "?")
        mms_by_content[ct] += 1
        mms_by_delivery[c.get("mms_delivery", "?")] += 1
        mms_total_bytes += c.get("mms_size_bytes", 0)

        if c.get("mms_size_bytes", 0) > 3_000_000 and c.get("line_class") == "Normal":
            mms_suspects.append({
                "msisdn": c["msisdn"],
                "size_mb": round(c["mms_size_bytes"]/1e6, 2),
                "content": ct, "ts": c["timestamp"],
            })

    findings["mms_by_content"]     = dict(mms_by_content.most_common())
    findings["mms_by_delivery"]    = dict(mms_by_delivery.most_common())
    findings["mms_total_mb"]       = round(mms_total_bytes / 1e6, 2)
    findings["mms_large_suspects"] = mms_suspects[:20]

    # 5.11 RCS analysis
    rcs_by_type = Counter()
    for c in cdrs:
        if c["call_type"] == "rcs":
            rcs_by_type[c.get("rcs_type", "?")] += 1
    findings["rcs_by_type"] = dict(rcs_by_type.most_common())

    return findings

# ------------------------------------------------------------------
# 6) ALERT ENGINE
# ------------------------------------------------------------------
def run_alert_engine(subs, cdrs, sigint_r, osint_r):
    alerts = []
    alert_id = 0
    ts_now = datetime.now()

    def add_alert(severity, atype, msisdn, desc, extra=None):
        nonlocal alert_id
        alert_id += 1
        sms_to = random.choice(SOC_RECIPIENTS)
        alerts.append({
            "alert_id": f"ALT-{ts_now.strftime('%Y%m%d')}-{alert_id:05d}",
            "timestamp": ts_now.strftime("%Y-%m-%d %H:%M:%S"),
            "severity": severity,
            "alert_type": atype,
            "msisdn": msisdn or "-",
            "description": desc,
            "extra": json.dumps(extra or {}, ensure_ascii=False),
            "sms_sent": 1,
            "sms_to": sms_to,
            "sms_body": f"[{severity}] {atype} | {desc[:90]}",
            "ack": 0,
        })

    # R1 — CLIR abuse
    for a in sigint_r.get("clir_abuse", [])[:20]:
        add_alert("CRITICAL", "CRITICAL_CLIR_ABUSE", a["msisdn"],
                  f"Unauthorized CLIR by {a['line_class']} line", extra=a)

    # R2 — Encryption failures
    for f in sigint_r.get("encryption_failures", [])[:20]:
        add_alert("CRITICAL", "CRITICAL_ENCRYPTION_FAIL", f["msisdn"],
                  f"E2E failure on {f['line_class']} line ({f['cipher']})", extra=f)

    # R3 — Filter bypass heavy users
    for msisdn, cnt in sigint_r.get("filter_bypass_users", [])[:10]:
        if cnt >= ALERT_RULES["HIGH_FILTER_BYPASS"]["threshold"]:
            add_alert("HIGH", "HIGH_FILTER_BYPASS", msisdn,
                      f"Unfiltered intl sessions: {cnt}",
                      extra={"sessions": cnt})

    # R4 — SIM-Box
    for s in sigint_r.get("simbox_suspects", [])[:10]:
        add_alert("HIGH", "HIGH_SIMBOX", s["msisdn"],
                  f"SIM-Box: {s['out_calls']} calls to {s['unique_targets']} targets",
                  extra=s)

    # R5 — Impossible travel
    for r in sigint_r.get("impossible_travel", [])[:10]:
        add_alert("MEDIUM", "MEDIUM_IMPOSSIBLE_TRAVEL", r["msisdn"],
                  f"{r['from']} -> {r['to']} | {r['km']} km in {r['dt_sec']}s",
                  extra=r)

    # R6 — LI miss (PATCHED: compare against ALL CDR msisdns)
    li_subs = {s.msisdn for s in subs if s.lawful_intercept}
    cdr_msisdns = {c["msisdn"] for c in cdrs}
    for msisdn in sorted(li_subs - cdr_msisdns)[:10]:
        add_alert("MEDIUM", "MEDIUM_LI_MISS", msisdn,
                  "LI-flagged line has no recent CDR captured")

    # R7 — Weak cells
    for cid, cnt in sigint_r.get("weak_cells", [])[:10]:
        if cnt >= ALERT_RULES["LOW_WEAK_CELL"]["threshold"]:
            add_alert("LOW", "LOW_WEAK_CELL", cid,
                      f"Cell with {cnt} weak samples",
                      extra={"cell_id": cid, "count": cnt})

    # R8 — VoLTE fallback spikes
    fb = sigint_r.get("volte_fallback", [])
    if len(fb) >= 5:
        by_cell = Counter(x["cell_id"] for x in fb)
        for cid, n in by_cell.most_common(5):
            if n >= 3:
                add_alert("MEDIUM", "MEDIUM_VOLTE_FALLBACK", cid,
                          f"VoLTE fallback to CSFB on 4G/5G cell: {n} calls",
                          extra={"cell_id": cid, "count": n})

    # R9 — Oversized MMS from Normal lines
    for s in sigint_r.get("mms_large_suspects", [])[:10]:
        add_alert("LOW", "LOW_LARGE_MMS", s["msisdn"],
                  f"Large MMS: {s['size_mb']} MB ({s['content']})",
                  extra=s)

    return alerts

# ------------------------------------------------------------------
# 7) STORAGE
# ------------------------------------------------------------------
def persist(cells, cores, subs, cdrs, osint_data, osint_r, sigint_r, alerts):
    if os.path.exists(DB): os.remove(DB)
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.executescript("""
    CREATE TABLE cells(cell_id TEXT PRIMARY KEY, name TEXT, tech TEXT, city TEXT,
                       lat REAL, lon REAL, band TEXT, azimuth INT, tilt INT,
                       tx_dbm REAL, backhaul_gbps REAL);
    CREATE TABLE cores(node_id TEXT PRIMARY KEY, name TEXT, role TEXT, tech TEXT,
                       city TEXT, capacity_tps INT);
    CREATE TABLE subscribers(
        msisdn TEXT PRIMARY KEY, imsi TEXT, imei TEXT, city TEXT, plan TEXT,
        kyc_age_days INT, roaming_enabled INT, risk_score REAL,
        line_class TEXT, international_access INT, filter_bypass INT,
        clir_enabled INT, clir_override INT, priority_qos INT,
        lawful_intercept INT, direct_routing INT, whitelisted_asns TEXT,
        encryption_required INT, cipher_suite TEXT, key_id TEXT,
        key_rotation_days INT, e2e_enabled INT
    );
    CREATE TABLE cdrs(
        record_id TEXT PRIMARY KEY, timestamp TEXT, msisdn TEXT, imsi TEXT,
        imei TEXT, called TEXT, call_type TEXT, duration_sec INT, bytes INT,
        result TEXT, cell_id TEXT, tech TEXT, city TEXT, lat REAL, lon REAL,
        rssi REAL, rsrp REAL, rsrq REAL, sinr REAL,
        clir_used INT, routing_class TEXT, filter_applied INT,
        international INT, line_class TEXT, priority_qos INT,
        encrypted INT, cipher_suite TEXT, encryption_failure INT, key_id TEXT,
        voice_bearer TEXT, voice_codec TEXT, voice_qci INT, voice_sig_proto TEXT,
        mms_content_type TEXT, mms_size_bytes INT, mms_delivery TEXT,
        rcs_type TEXT
    );
    CREATE TABLE osint_public_registry(cell_id TEXT, operator TEXT, mcc TEXT, mnc TEXT,
                                       lat REAL, lon REAL, tech TEXT, band TEXT, source TEXT);
    CREATE TABLE osint_complaints(city TEXT, topic TEXT, sentiment TEXT, source TEXT);
    CREATE TABLE sigint_findings(key TEXT, value TEXT);
    CREATE TABLE alerts(
        alert_id TEXT PRIMARY KEY, timestamp TEXT, severity TEXT,
        alert_type TEXT, msisdn TEXT, description TEXT, extra TEXT,
        sms_sent INT, sms_to TEXT, sms_body TEXT, ack INT
    );
    CREATE TABLE audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, user TEXT,
        action TEXT, entity TEXT, entity_id TEXT, details TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);
    CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
    CREATE TABLE sms_alerts(
        sms_id INTEGER PRIMARY KEY AUTOINCREMENT, alert_id TEXT,
        timestamp TEXT, recipient TEXT, body TEXT, status TEXT
    );
    CREATE INDEX idx_cdr_msisdn ON cdrs(msisdn);
    CREATE INDEX idx_cdr_imsi   ON cdrs(imsi);
    CREATE INDEX idx_cdr_cell   ON cdrs(cell_id);
    CREATE INDEX idx_cdr_ts     ON cdrs(timestamp);
    CREATE INDEX idx_alert_sev  ON alerts(severity);
    """)

    cur.executemany("INSERT INTO cells VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    [tuple(asdict(c).values()) for c in cells])
    cur.executemany("INSERT INTO cores VALUES(?,?,?,?,?,?)",
[tuple(asdict(c).values()) for c in cores])

    cur.executemany(
        """INSERT INTO subscribers VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(s.msisdn, s.imsi, s.imei, s.city, s.plan, s.kyc_age_days,
          int(s.roaming_enabled), s.risk_score,
          s.line_class, int(s.international_access), int(s.filter_bypass),
          int(s.clir_enabled), int(s.clir_override), s.priority_qos,
          int(s.lawful_intercept), int(s.direct_routing),
          ",".join(s.whitelisted_asns),
          int(s.encryption_required), s.cipher_suite, s.key_id,
          s.key_rotation_days, int(s.e2e_enabled))
         for s in subs])

    cur.executemany(
        """INSERT INTO cdrs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [tuple(c.values()) for c in cdrs])

    cur.executemany("INSERT INTO osint_public_registry VALUES(?,?,?,?,?,?,?,?,?)",
                    [(x["cell_id"], x["operator"], x["mcc"], x["mnc"],
                      x["lat"], x["lon"], x["tech"], x["band"], x["source"])
                     for x in osint_data["public_cell_registry"]])
    cur.executemany("INSERT INTO osint_complaints VALUES(?,?,?,?)",
                    [(x["city"], x["topic"], x["sentiment"], x["source"])
                     for x in osint_data["social_complaints"]])

    for sec, payload in [("OSINT", osint_r), ("SIGINT", sigint_r)]:
        cur.execute("INSERT INTO sigint_findings VALUES(?,?)",
                    (sec, json.dumps(payload, ensure_ascii=False, default=str)))

    cur.executemany(
        """INSERT INTO alerts VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        [(a["alert_id"], a["timestamp"], a["severity"], a["alert_type"],
          a["msisdn"], a["description"], a["extra"],
          a["sms_sent"], a["sms_to"], a["sms_body"], a["ack"])
         for a in alerts])

    cur.executemany(
        """INSERT INTO sms_alerts(alert_id, timestamp, recipient, body, status)
           VALUES(?,?,?,?,?)""",
        [(a["alert_id"], a["timestamp"], a["sms_to"], a["sms_body"], "DELIVERED")
         for a in alerts if a["sms_sent"]])

    con.commit(); con.close()

# ------------------------------------------------------------------
# 8) VISUALIZATION
# ------------------------------------------------------------------
def visualize(cells, cdrs, sigint_r, osint_r):
    if not HAS_PLOT:
        print("  [i] matplotlib not installed - charts skipped.")
        return

    # 1) Cell map
    plt.figure(figsize=(11, 8))
    colors = {"2G": "#8888ff", "3G": "#44aaff", "4G": "#00aa44",
              "5G": "#ff4444", "6G": "#a855f7"}
    for tech, col in colors.items():
        xs = [c.lon for c in cells if c.tech == tech]
        ys = [c.lat for c in cells if c.tech == tech]
        plt.scatter(xs, ys, s=14, c=col, alpha=0.75, label=f"{tech} ({len(xs)})")
    for name, lat, lon, _p, _w in CITIES:
        plt.annotate(name, (lon, lat), fontsize=9, fontweight="bold")
    plt.title(f"{OPERATOR} - Cell Sites Distribution")
    plt.xlabel("Longitude"); plt.ylabel("Latitude"); plt.legend(); plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "01_cell_map.png"), dpi=130)
    plt.close()

    # 2) Hourly traffic
    plt.figure(figsize=(11, 4))
    hours = sorted(sigint_r["traffic_by_hour"].keys())
    vals  = [sigint_r["traffic_by_hour"][h] for h in hours]
    plt.plot(hours, vals, marker="o", color="#1f77b4")
    plt.title("Traffic Distribution by Hour (7 days)")
    plt.xlabel("Hour"); plt.ylabel("CDR count"); plt.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "02_traffic_hour.png"), dpi=130); plt.close()

    # 3) Call type mix
    plt.figure(figsize=(7, 5))
    labels = list(sigint_r["traffic_by_type"].keys())
    sizes  = list(sigint_r["traffic_by_type"].values())
    plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=120)
    plt.title("Traffic Mix by Type")
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "03_traffic_type.png"), dpi=130); plt.close()

    # 4) RSRP histogram
    rsrp = [c["rsrp"] for c in cdrs if c["rsrp"] is not None]
    if rsrp:
        plt.figure(figsize=(10, 4))
        plt.hist(rsrp, bins=45, color="#2ca02c", alpha=0.85)
        plt.title("RSRP Distribution (4G/5G samples)")
        plt.xlabel("RSRP (dBm)"); plt.ylabel("Samples"); plt.grid(alpha=0.3)
        plt.tight_layout(); plt.savefig(os.path.join(OUT, "04_rsrp_hist.png"), dpi=130); plt.close()

    # 5) Volume per city
    plt.figure(figsize=(11, 4))
    cities = list(sigint_r["traffic_by_city"].keys())
    vols   = list(sigint_r["traffic_by_city"].values())
    plt.bar(cities, vols, color="#ff7f0e")
    plt.title("CDR Volume per City")
    plt.xticks(rotation=35); plt.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "05_city_volume.png"), dpi=130); plt.close()

    # 6) OSINT topics
    plt.figure(figsize=(8, 4))
    t = list(osint_r["complaints_by_topic"].keys())
    v = list(osint_r["complaints_by_topic"].values())
    plt.barh(t, v, color="#d62728")
    plt.title("OSINT - Public Complaint Topics")
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "06_osint_topics.png"), dpi=130); plt.close()

    # 7) Special-line traffic by class
    sc = sigint_r.get("special_line_traffic", {})
    if sc:
        plt.figure(figsize=(9, 4))
        ks = list(sc.keys()); vs = [sc[k] for k in ks]
        cols = ["#94a3b8","#22c55e","#ef4444","#0ea5e9","#f59e0b","#a855f7"]
        plt.bar(ks, vs, color=cols[:len(ks)])
        plt.title("Traffic by Line Class")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(OUT, "07_special_lines.png"), dpi=130)
        plt.close()

    # 8) Encryption coverage
    cov = sigint_r.get("encryption_coverage", {})
    if cov:
        plt.figure(figsize=(9, 4))
        ks = list(cov.keys())
        vs = [cov[k]["coverage_pct"] for k in ks]
        plt.bar(ks, vs, color="#22c55e", alpha=0.85)
        plt.ylim(0, 105)
        plt.title("Encryption Coverage by Line Class (%)")
        plt.ylabel("Coverage %")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(OUT, "08_encryption.png"), dpi=130)
        plt.close()

    # 9) Voice bearer mix
    vb = sigint_r.get("voice_bearers", {})
    if vb:
        plt.figure(figsize=(8, 5))
        ks = list(vb.keys()); vs = [vb[k] for k in ks]
        plt.pie(vs, labels=ks, autopct="%1.1f%%", startangle=90)
        plt.title("Voice Bearer Mix (VoLTE / VoWiFi / VoNR / CSFB)")
        plt.tight_layout()
        plt.savefig(os.path.join(OUT, "09_voice_bearers.png"), dpi=130)
        plt.close()

    # 10) MMS content type distribution
    mc = sigint_r.get("mms_by_content", {})
    if mc:
        plt.figure(figsize=(10, 4))
        ks = list(mc.keys()); vs = [mc[k] for k in ks]
        plt.barh(ks, vs, color="#8b5cf6")
        plt.title("MMS by Content Type")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(OUT, "10_mms_content.png"), dpi=130)
        plt.close()

# ------------------------------------------------------------------
# 9) REPORT
# ------------------------------------------------------------------
def build_report(cells, cores, subs, cdrs, osint_r, sigint_r, alerts):
    lines = []
    P = lines.append
    P("=" * 78)
    P(f" {OPERATOR} NETWORK SIMULATION REPORT")
    P(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    P(f" MCC/MNC: {MCC}-{MNC} | Seed: {SEED} | Mode: LOCAL-ONLY")
    P("=" * 78)

    P("\n[1] NETWORK TOPOLOGY")
    P(f"    Cells total          : {len(cells)}")
    by_tech = Counter(c.tech for c in cells)
    for t in ("2G","3G","4G","5G","6G"):
        P(f"      {t:<3} cells         : {by_tech.get(t,0)}")
    P(f"    Core nodes total     : {len(cores)}")
    roles = Counter(c.role for c in cores)
    for r, n in roles.most_common():
        P(f"      {r:<7} : {n}")

    P("\n[2] SUBSCRIBERS")
    P(f"    Total subscribers    : {len(subs)}")
    plan_c = Counter(s.plan for s in subs)
    for p, n in plan_c.most_common():
        P(f"      {p:<18}: {n}")
    P(f"    Roaming-enabled      : {sum(1 for s in subs if s.roaming_enabled)}")

    P("\n[3] TRAFFIC (CDR)")
    P(f"    CDR records          : {len(cdrs)}")
    type_dict = sigint_r['traffic_by_type']
    P(f"    Voice/SMS/MMS/Data   : "
      f"{type_dict.get('voice',0)} / {type_dict.get('sms',0)} / "
      f"{type_dict.get('mms',0)} / {type_dict.get('data',0)}")
    P(f"    RCS / USSD           : {type_dict.get('rcs',0)} / {type_dict.get('ussd',0)}")
    P(f"    Tech distribution    : {sigint_r['traffic_by_tech']}")
    P(f"    Top cities           :")
    for city, n in list(sigint_r["traffic_by_city"].items())[:5]:
        P(f"      {city:<12} {n}")

    P("\n[4] OSINT FINDINGS")
    P(f"    Public registry rows : {osint_r['registry_total']}")
    P(f"    Registry by tech     : {osint_r['registry_by_tech']}")
    P(f"    Public complaints    : {osint_r['complaints_total']}")
    P(f"    Sentiment split      : {osint_r['complaints_sentiment']}")
    P(f"    Top complaint topics :")
    for t, n in list(osint_r["complaints_by_topic"].items())[:5]:
        P(f"      {t:<18} {n}")

    P("\n[5] SIGINT FINDINGS")
    P(f"    IMEI-churn suspects  : {len(sigint_r['imei_churn_suspects'])}")
    for imsi, n in sigint_r["imei_churn_suspects"][:5]:
        P(f"      IMSI ...{imsi[-6:]} -> {n} distinct IMEIs")
    P(f"    SIM-Box suspects     : {len(sigint_r['simbox_suspects'])}")
    for s in sigint_r["simbox_suspects"][:5]:
        P(f"      {s['msisdn']} | out={s['out_calls']} "
          f"uniq={s['unique_targets']} short={s['short_call_ratio']}")
    P(f"    Impossible-travel    : {len(sigint_r['impossible_travel'])}")
    for r in sigint_r["impossible_travel"][:5]:
        P(f"      {r['from']} -> {r['to']} | {r['km']} km "
          f"in {r['dt_sec']}s ({r['speed_kmh']} km/h)")
    P(f"    Weak-signal cells    : {len(sigint_r['weak_cells'])}")
    for cid, n in sigint_r["weak_cells"][:5]:
        P(f"      {cid} : {n} bad samples")

    P("\n[5.1] SPECIAL LINES")
    P(f"    Traffic by class     : {sigint_r.get('special_line_traffic', {})}")
    P(f"    CLIR abuse events    : {len(sigint_r.get('clir_abuse', []))}")
    P(f"    Filter-bypass users  : {len(sigint_r.get('filter_bypass_users', []))}")
    P(f"    Priority events      : {sigint_r.get('priority_by_class', {})}")

    P("\n[5.2] ENCRYPTION")
    for cls, st in sigint_r.get("encryption_coverage", {}).items():
        P(f"    {cls:<12}: {st['encrypted']}/{st['total']} "
          f"({st['coverage_pct']}%) | failures={st['failures']}")
    P(f"    Cipher usage         : {sigint_r.get('cipher_usage', {})}")
    P(f"    Encryption failures  : {len(sigint_r.get('encryption_failures', []))}")

    P("\n[5.3] ALERTS & SMS")
    sev_count = Counter(a["severity"] for a in alerts)
    for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        P(f"    {s:<9}: {sev_count.get(s, 0)}")
    P(f"    Total SMS dispatched : {sum(1 for a in alerts if a['sms_sent'])}")
    P(f"    Recent alerts        :")
    for a in alerts[:5]:
        P(f"      [{a['severity']:<8}] {a['alert_type']:<26} {a['description'][:40]}")

    P("\n[5.4] VOICE BEARERS / VoLTE")
    P(f"    Bearer distribution  : {sigint_r.get('voice_bearers', {})}")
    P(f"    Codec distribution   : {sigint_r.get('voice_codecs', {})}")
    P(f"    QCI distribution     : {sigint_r.get('voice_qci', {})}")
    P(f"    VoLTE fallback count : {len(sigint_r.get('volte_fallback', []))}")

    P("\n[5.5] MMS")
    P(f"    Total volume (MB)    : {sigint_r.get('mms_total_mb', 0)}")
    P(f"    By content type      : {sigint_r.get('mms_by_content', {})}")
    P(f"    Delivery status      : {sigint_r.get('mms_by_delivery', {})}")
    P(f"    Large MMS suspects   : {len(sigint_r.get('mms_large_suspects', []))}")

    P("\n[5.6] RCS")
    P(f"    RCS by type          : {sigint_r.get('rcs_by_type', {})}")

    P("\n[6] OUTPUT ARTIFACTS")
    P(f"    Database             : {DB}")
    if HAS_PLOT:
        P(f"    Charts               : {OUT}/01..10_*.png")

    P("\n" + "=" * 78)
    text = "\n".join(lines)
    with open(os.path.join(OUT, "report.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    print("=" * 78)
    print(f" {OPERATOR}-NET-SIM v3.0 | LOCAL-ONLY | Seed={SEED}")
    print("=" * 78)

    print("[1/7] Building network topology...")
    cells, cores = build_topology()
    print(f"      Cells: {len(cells)} | Core nodes: {len(cores)}")

    print("[2/7] Generating subscribers...")
    subs = build_subscribers(5000)

    print("[3/7] Generating CDR records...")
    cdrs = gen_cdrs(subs, cells, n=60_000)
    print(f"      {len(cdrs)} records generated.")

    print("[4/7] Running OSINT analysis...")
    osint_data = osint_collect(cells, subs)
    osint_r = osint_report(osint_data)

    print("[5/7] Running SIGINT analysis...")
    sigint_r = sigint_analyze(cdrs, cells)

    print("[5.5/7] Running alert engine + SMS dispatch...")
    alerts = run_alert_engine(subs, cdrs, sigint_r, osint_r)
    print(f"        {len(alerts)} alerts dispatched via SMS.")

    print("[6/7] Persisting to SQLite...")
    persist(cells, cores, subs, cdrs, osint_data, osint_r, sigint_r, alerts)

    print("[7/7] Rendering charts and report...")
    visualize(cells, cdrs, sigint_r, osint_r)
    build_report(cells, cores, subs, cdrs, osint_r, sigint_r, alerts)

    print("[8/8] Running attack simulation...")
    try:
        import telecom_attack
        atk = telecom_attack.run_attack_simulation(
            n_scenarios=25, samples_per_scenario=20, inject_alerts=True)
        print(f"        {atk['scenarios']} scenarios, {atk['events']} events, "
              f"{atk['alerts']} alerts.")
    except Exception as e:
        print(f"        [i] Attack simulation skipped: {e}")

    print("\n[OK] Simulation completed successfully.")
    print(f"[DIR] Outputs: {os.path.abspath(OUT)}")

if __name__ == "__main__":
    main()



