"""TELECOM-NET-SIM | Common Utilities v1.0 (shared across modules)"""

import hashlib
import hmac
import os
import random
import secrets
import sqlite3
from datetime import datetime

import pandas as pd

OPERATOR = "TELECOM"
MCC, MNC = "432", "99"
DB_PATH = "telecom_sim_output/telecom_sim.db"
OUT_DIR = "telecom_sim_output"

CITIES = [
    ("Tehran", 35.6892, 51.3890, 12_000_000, 0.35),
    ("Mashhad", 36.2605, 59.6168, 3_400_000, 0.14),
    ("Isfahan", 32.6546, 51.6680, 2_200_000, 0.10),
    ("Karaj", 35.8400, 50.9391, 1_900_000, 0.09),
    ("Shiraz", 29.5918, 52.5837, 1_800_000, 0.08),
    ("Tabriz", 38.0800, 46.2919, 1_700_000, 0.07),
    ("Qom", 34.6401, 50.8764, 1_200_000, 0.05),
    ("Ahvaz", 31.3183, 48.6706, 1_300_000, 0.05),
    ("Kermanshah", 34.3142, 47.0650, 950_000, 0.035),
    ("Urmia", 37.5527, 45.0761, 800_000, 0.035),
]
LINE_CLASSES = ["Normal", "VIP", "Government", "Corporate", "Emergency", "Test"]
QOS_BY_CLASS = {
    "Normal": (0, 2),
    "VIP": (6, 8),
    "Government": (7, 9),
    "Corporate": (4, 6),
    "Emergency": (9, 9),
    "Test": (3, 5),
}
FILTER_BYPASS_CLASSES = {"Government", "Emergency", "Test", "Corporate"}
CLIR_AUTHORIZED = {"Government", "Emergency", "Test", "VIP"}
CLIR_OVERRIDE_CLASSES = {"Government", "Emergency"}
MANDATORY_ENCRYPTION = {"Government", "Emergency"}
OPTIONAL_ENCRYPTION = {"Test", "VIP", "Corporate"}
PLANS = [
    "Prepaid-Basic",
    "Prepaid-Plus",
    "Postpaid-Silver",
    "Postpaid-Gold",
    "Postpaid-Business",
    "IoT-M2M",
]

# 6G (sub-THz + mmWave) bands
SIXG_BANDS = ["THz-140", "THz-220", "sub-THz-300", "mmWave-28"]

# Technology color map (shared by dashboard + radar)
TECH_COLORS = {
    "2G": "#8888ff",
    "3G": "#38bdf8",
    "4G": "#22c55e",
    "5G": "#f6821f",
    "6G": "#a855f7",
}
CIPHER_SUITES = {
    "AES-256-GCM": {"strength": 256, "quantum_safe": False},
    "ChaCha20-Poly1305": {"strength": 256, "quantum_safe": False},
    "SNOW-3G": {"strength": 128, "quantum_safe": False},
    "NEA2": {"strength": 128, "quantum_safe": False},
    "Kyber-1024+AES-256": {"strength": 384, "quantum_safe": True},
}
MSISDN_PREFIXES = [
    "910",
    "911",
    "912",
    "913",
    "914",
    "915",
    "916",
    "917",
    "918",
    "919",
    "901",
    "902",
    "903",
    "905",
    "930",
    "933",
    "935",
    "936",
    "937",
    "938",
    "939",
    "920",
    "921",
    "922",
]
IMEI_TACS = [
    "35674108",
    "35674208",
    "35875108",
    "35294808",
    "86754503",
    "86754603",
    "35061234",
    "35296408",
    "86012345",
    "35879005",
]
SOC_RECIPIENTS = ["989120000001", "989120000002", "989120000003"]


def luhn(number):
    d = [int(x) for x in number]
    for i in range(len(d) - 1, -1, -2):
        d[i] *= 2
        if d[i] > 9:
            d[i] -= 9
    return str((10 - sum(d) % 10) % 10)


def gen_imsi():
    return f"{MCC}{MNC}" + "".join(random.choices("0123456789", k=10))


def gen_msisdn():
    return "98" + random.choice(MSISDN_PREFIXES) + "".join(random.choices("0123456789", k=7))


def gen_imei():
    p = random.choice(IMEI_TACS) + "".join(random.choices("0123456789", k=6))
    return p + luhn(p)


def gen_key_id(seed=""):
    src = seed or f"{random.random()}{datetime.now()}"
    return "KEY-" + hashlib.sha1(src.encode()).hexdigest()[:16].upper()


_AUTH_FILE = os.path.join(OUT_DIR, ".admin_auth")
_SALT_FILE = os.path.join(OUT_DIR, ".admin_salt")


def _scrypt(pw, salt):
    return hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def has_password():
    return os.path.exists(_AUTH_FILE) and os.path.exists(_SALT_FILE)


def set_password(pw):
    os.makedirs(OUT_DIR, exist_ok=True)
    salt = secrets.token_bytes(16)
    digest = _scrypt(pw, salt)
    with open(_SALT_FILE, "wb") as f:
        f.write(salt)
    with open(_AUTH_FILE, "wb") as f:
        f.write(digest)


def verify_password(pw):
    if not has_password():
        return False
    try:
        with open(_SALT_FILE, "rb") as f:
            salt = f.read()
        with open(_AUTH_FILE, "rb") as f:
            expected = f.read()
        return hmac.compare_digest(_scrypt(pw, salt), expected)
    except Exception:
        return False


def db_connect(path=DB_PATH):
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    return con


def db_df(sql, params=(), path=DB_PATH):
    con = db_connect(path)
    try:
        return pd.read_sql(sql, con, params=params)
    finally:
        con.close()


def db_exec(query, params=(), path=DB_PATH):
    con = db_connect(path)
    try:
        cur = con.cursor()
        cur.execute(query, params)
        con.commit()
    finally:
        con.close()


def db_one(sql, params=(), path=DB_PATH):
    con = db_connect(path)
    try:
        cur = con.cursor()
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        con.close()


def db_count(table, path=DB_PATH):
    try:
        r = db_one(f"SELECT COUNT(*) FROM {table}", path=path)
        return r[0] if r else 0
    except Exception:
        return 0


def db_chunked_in_update(
    table, column, set_clause, values, where_values, chunk_size=800, path=DB_PATH
):
    total = 0
    con = db_connect(path)
    try:
        cur = con.cursor()
        for i in range(0, len(where_values), chunk_size):
            chunk = where_values[i : i + chunk_size]
            ph = ",".join("?" * len(chunk))
            cur.execute(
                f"UPDATE {table} SET {set_clause} " f"WHERE {column} IN ({ph})",
                tuple(values + chunk),
            )
            total += cur.rowcount
        con.commit()
    finally:
        con.close()
    return total
