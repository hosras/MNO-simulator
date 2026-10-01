# -*- coding: utf-8 -*-
"""TELECOM Admin Panel v2.0 — full CRUD + audit + backup (see common.py)

Refactored: all Streamlit-rendering code lives inside main(), guarded so
that importing this module (e.g. for tests or from another module) does
NOT execute any st.* call and does NOT emit ScriptRunContext warnings.
"""
import os, json, sqlite3, random
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import plotly.express as px

from telecom_common import (
    DB_PATH, OUT_DIR, CITIES, LINE_CLASSES, PLANS, CIPHER_SUITES,
    gen_msisdn, gen_imsi, gen_imei, gen_key_id,
    has_password, set_password, verify_password,
    db_df, db_exec, db_one, db_count, db_chunked_in_update,
)

BACKUP_DIR = os.path.join(OUT_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


# ------------------------------------------------------------------
# Helpers — safe to define at import time (they only touch st.*
# when actually CALLED, i.e. from inside main()).
# ------------------------------------------------------------------
def is_logged_in():
    return st.session_state.get("admin_logged_in", False)

def current_user():
    try:
        return st.session_state.get("admin_user") or "anonymous"
    except Exception:
        return "system"

def logout():
    st.session_state["admin_logged_in"] = False
    st.session_state["admin_user"] = None

def init_audit():
    db_exec("""CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, user TEXT,
        action TEXT, entity TEXT, entity_id TEXT, details TEXT)""")

def log_audit(action, entity, entity_id, details=""):
    db_exec(
        "INSERT INTO audit_log(ts,user,action,entity,entity_id,details) "
        "VALUES(?,?,?,?,?,?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         current_user(), action, entity, str(entity_id), details),
    )


# ------------------------------------------------------------------
# Login rate-limit helpers
# Counter lives in audit_log, not session_state, so browser refresh
# and app restart cannot clear it.
# ------------------------------------------------------------------
LOGIN_WINDOW_MIN = 15
LOGIN_MAX_FAILS = 5


def count_recent_failed_logins(minutes=LOGIN_WINDOW_MIN):
    """Count LOGIN_FAILED entries in audit_log within the last N minutes."""
    cutoff = (datetime.now() - timedelta(minutes=minutes)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    try:
        row = db_one(
            "SELECT COUNT(*) FROM audit_log "
            "WHERE action='LOGIN_FAILED' AND ts >= ?",
            (cutoff,),
        )
        return int(row[0]) if row else 0
    except Exception:
        return 0


def lockout_remaining_sec():
    """Seconds until the oldest of the last N failures ages out.

    Returns 0 if there are fewer than N recent failures.
    """
    try:
        row = db_one(
            "SELECT MIN(ts) FROM ("
            "  SELECT ts FROM audit_log "
            "  WHERE action='LOGIN_FAILED' "
            "  ORDER BY id DESC LIMIT ?"
            ")",
            (LOGIN_MAX_FAILS,),
        )
        if not row or not row[0]:
            return 0
        oldest = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        expires = oldest + timedelta(minutes=LOGIN_WINDOW_MIN)
        return max(0, int((expires - datetime.now()).total_seconds()))
    except Exception:
        return 0


def create_backup(label="auto"):
    """Create a WAL-consistent snapshot of the SQLite DB.

    Uses sqlite3's online backup API instead of shutil.copy2 so that
    any data still sitting in the -wal file is included. Do NOT swap
    this back to a plain file copy while journal_mode=WAL is active.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    os.makedirs(BACKUP_DIR, exist_ok=True)

    safe_label = "".join(
        ch for ch in str(label) if ch.isalnum() or ch in "-_"
    ) or "auto"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = os.path.join(BACKUP_DIR, f"backup_{safe_label}_{ts}.db")

    src = sqlite3.connect(DB_PATH)
    try:
        dst = sqlite3.connect(fn)
        try:
            src.backup(dst)  # atomic, WAL-aware snapshot
            chk = dst.execute("PRAGMA quick_check").fetchone()
            if not chk or chk[0] != "ok":
                raise RuntimeError(f"Backup integrity check failed: {chk}")
        finally:
            dst.close()
    finally:
        src.close()

    return os.path.abspath(fn)

def list_backups():
    if not os.path.isdir(BACKUP_DIR):
        return []
    return sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")],
        reverse=True,
    )

def restore_backup(backup_filename):
    """Atomically restore a backup into the live DB.

    - Verifies the backup file's integrity before touching anything.
    - Uses sqlite3's backup API (WAL-aware) to overwrite the live DB.
    - Removes stale -wal / -shm sidecar files.
    - Refuses to run if the backup path escapes BACKUP_DIR.

    Returns the absolute path of the restored backup on success.
    Raises RuntimeError on any failure (caller should catch and st.error).
    """
    # ---- 1) Path safety: never trust caller-supplied filenames ----
    if not isinstance(backup_filename, str) or not backup_filename:
        raise RuntimeError("Invalid backup filename.")
    if os.path.basename(backup_filename) != backup_filename:
        raise RuntimeError("Backup filename must not contain path separators.")

    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    if not os.path.isfile(backup_path):
        raise RuntimeError(f"Backup not found: {backup_filename}")
    if not os.path.isfile(DB_PATH):
        raise RuntimeError(f"Live DB not found: {DB_PATH}")

    # ---- 2) Verify the backup before we destroy the live DB ----
    try:
        chk_con = sqlite3.connect(backup_path)
        try:
            res = chk_con.execute("PRAGMA quick_check").fetchone()
        finally:
            chk_con.close()
    except sqlite3.DatabaseError as e:
        raise RuntimeError(f"Backup is not a valid SQLite DB: {e}")

    if not res or res[0] != "ok":
        raise RuntimeError(f"Backup integrity check failed: {res}")

    # ---- 3) Copy the backup INTO the live DB (atomic, WAL-aware) ----
    src = sqlite3.connect(backup_path)
    try:
        dst = sqlite3.connect(DB_PATH)
        try:
            dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            src.backup(dst)
            dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            dst.close()
    finally:
        src.close()

    # ---- 4) Remove stale sidecar files left over from before ----
    for suffix in ("-wal", "-shm"):
        side = DB_PATH + suffix
        if os.path.exists(side):
            try:
                os.remove(side)
            except OSError:
                pass

    return os.path.abspath(backup_path)



# ------------------------------------------------------------------
# All Streamlit rendering lives here. Nothing runs at import time.
# ------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="TELECOM Admin Panel",
        page_icon="\u2699\ufe0f",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        "<style>html,body,[class*=\"css\"]{direction:ltr;text-align:left;"
        "font-family:'Segoe UI',sans-serif;}"
        ".admin-header{background:linear-gradient(90deg,#dc2626,#7c2d12);"
        "padding:18px 24px;border-radius:14px;color:#fff;"
        "display:flex;justify-content:space-between;align-items:center;}"
        ".danger-box{background:#fef2f2;border-left:4px solid #ef4444;"
        "padding:12px 16px;border-radius:8px;margin:10px 0;}</style>",
        unsafe_allow_html=True,
    )

    if not os.path.exists(DB_PATH):
        st.error("Database not found. Run telecom_net_sim.py first.")
        st.stop()

    init_audit()

    # ---------------- first-time password setup ----------------
    if not has_password():
        st.markdown(
            '<div class="admin-header"><div>'
            '<div style="font-size:24px;font-weight:800;">'
            'TELECOM Admin Panel</div>'
            '<div style="opacity:.9;font-size:13px;">'
            'First-time setup</div></div></div>',
            unsafe_allow_html=True,
        )
        st.write("")
        with st.form("setup_pw"):
            pw1 = st.text_input("Password (min 8 chars)", type="password")
            pw2 = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Create Password",
                                     use_container_width=True):
                if len(pw1) < 8:
                    st.error("At least 8 characters.")
                elif pw1 != pw2:
                    st.error("Mismatch.")
                else:
                    set_password(pw1)
                    st.session_state["admin_logged_in"] = True
                    st.session_state["admin_user"] = "admin"
                    st.rerun()
        st.stop()

    # ---------------- login ----------------
    if not is_logged_in():
        # Rate-limit from audit_log so that
        # a browser refresh or app restart cannot bypass the lockout.
        recent_fails = count_recent_failed_logins()
        locked_out = recent_fails >= LOGIN_MAX_FAILS

        st.markdown(
            '<div class="admin-header"><div>'
            '<div style="font-size:24px;font-weight:800;">'
            'TELECOM Admin Panel</div>'
            '<div style="opacity:.9;font-size:13px;">'
            'Authenticated access</div></div></div>',
            unsafe_allow_html=True,
        )
        st.write("")

        if locked_out:
            sec = lockout_remaining_sec()
            mins = max(1, (sec + 59) // 60)
            st.error(
                f"Too many failed logins ({recent_fails}/{LOGIN_MAX_FAILS}). "
                f"Try again in about {mins} minute(s)."
            )
            st.stop()

        with st.form("login"):
            user = st.text_input("Username", value="admin")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                if user == "admin" and verify_password(pw):
                    st.session_state["admin_logged_in"] = True
                    st.session_state["admin_user"] = "admin"
                    log_audit("LOGIN", "system", "-", "successful")
                    st.rerun()
                else:
                    log_audit("LOGIN_FAILED", "system", user or "-",
                              "bad credentials")
                    remaining = LOGIN_MAX_FAILS - (recent_fails + 1)
                    if remaining > 0:
                        st.error(
                            f"Invalid credentials. "
                            f"{remaining} attempt(s) left in the "
                            f"{LOGIN_WINDOW_MIN}-minute window."
                        )
                    else:
                        st.error(
                            f"Too many failed logins. Try again in "
                            f"about {LOGIN_WINDOW_MIN} minute(s)."
                        )
        st.stop()

    # ---------------- header ----------------
    st.markdown(
        f'<div class="admin-header"><div>'
        f'<div style="font-size:22px;font-weight:800;">'
        f'TELECOM Admin Panel</div>'
        f'<div style="opacity:.9;font-size:13px;">CRUD | Audit | Backup | '
        f'User: <b>{current_user()}</b></div></div>'
        f'<div style="text-align:right;font-size:12px;opacity:.9;">'
        f'{datetime.now():%Y-%m-%d %H:%M}</div></div>',
        unsafe_allow_html=True,
    )
    st.write("")

    # ---------------- sidebar ----------------
    with st.sidebar:
        st.markdown(f"### {current_user()}")
        if st.button("Logout", use_container_width=True):
            log_audit("LOGOUT", "system", "-", "")
            logout()
            st.rerun()
        st.divider()
        st.markdown("### Quick Stats")
        st.metric("Subscribers", f"{db_count('subscribers'):,}")
        st.metric("Cells", f"{db_count('cells'):,}")
        try:
            _n6g = int(db_df(
                "SELECT COUNT(*) AS n FROM cells WHERE tech='6G'"
            ).iloc[0]["n"])
            st.metric("  6G Cells", f"{_n6g:,}")
        except Exception:
            pass
        st.metric("Core Nodes", f"{db_count('cores'):,}")
        st.metric("CDR Records", f"{db_count('cdrs'):,}")
        st.metric("Alerts", f"{db_count('alerts'):,}")
        st.divider()
        if st.button("Create Backup Now", use_container_width=True):
            p = create_backup("manual")
            log_audit("BACKUP", "db", p, "manual")
            st.success(f"Backup: {os.path.basename(p)}")

    tabs = st.tabs([
        "Dashboard", "Subscribers", "Cells", "Core Nodes", "Alerts",
        "Special Lines", "Encryption", "Backup / Restore", "Audit Log",
    ])

    # ==================== TAB 0 — DASHBOARD ====================
    with tabs[0]:
        st.subheader("Admin Dashboard")
        n_6g = int(db_df(
            "SELECT COUNT(*) AS n FROM cells WHERE tech='6G'"
        ).iloc[0]["n"])
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric("Subscribers", f"{db_count('subscribers'):,}")
        with c2: st.metric("Cells", f"{db_count('cells'):,}")
        with c3: st.metric("6G Cells", f"{n_6g:,}")
        with c4: st.metric("Alerts", f"{db_count('alerts'):,}")
        with c5: st.metric("Audit Records", f"{db_count('audit_log'):,}")
        st.divider()
        st.markdown("### Recent Audit Activity")
        recent = db_df(
            "SELECT ts,user,action,entity,entity_id,details "
            "FROM audit_log ORDER BY id DESC LIMIT 20"
        )
        if not recent.empty:
            st.dataframe(recent, use_container_width=True, hide_index=True)
        st.markdown("### Subscribers by Line Class")
        lc = db_df(
            "SELECT line_class, COUNT(*) AS count FROM subscribers "
            "GROUP BY line_class ORDER BY count DESC"
        )
        if not lc.empty:
            fig = px.bar(lc, x="line_class", y="count", color="count",
                         color_continuous_scale="Blues")
            fig.update_layout(height=340, coloraxis_showscale=False,
                              xaxis_title="", yaxis_title="Subscribers")
            st.plotly_chart(fig, use_container_width=True)

    # ==================== TAB 1 — SUBSCRIBERS ====================
    with tabs[1]:
        st.subheader("Manage Subscribers")
        action = st.radio("Action", ["View", "Add", "Edit", "Delete"],
                          horizontal=True, key="sub_act",
                          label_visibility="collapsed")

        if action == "View":
            c1, c2, c3 = st.columns(3)
            with c1:
                search = st.text_input("Search (MSISDN/IMSI/IMEI)",
                                       key="sub_q")
            with c2:
                lc_f = st.multiselect("Line Class", LINE_CLASSES,
                                      default=LINE_CLASSES, key="sub_lc")
            with c3:
                lim = st.number_input("Limit", 50, 10000, 500, 50,
                                      key="sub_lim")
            sql = "SELECT * FROM subscribers WHERE 1=1"
            params = []
            if search:
                sql += " AND (msisdn LIKE ? OR imsi LIKE ? OR imei LIKE ?)"
                p = f"%{search}%"
                params += [p, p, p]
            if lc_f:
                sql += f" AND line_class IN ({','.join('?'*len(lc_f))})"
                params += lc_f
            sql += f" LIMIT {int(lim)}"
            df = db_df(sql, tuple(params))
            st.caption(f"{len(df)} records")
            st.dataframe(df, use_container_width=True,
                         hide_index=True, height=500)
            st.download_button(
                "Download CSV",
                df.to_csv(index=False).encode("utf-8-sig"),
                "subscribers.csv", "text/csv",
            )

        elif action == "Add":
            with st.form("add_sub"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    msisdn = st.text_input("MSISDN", value=gen_msisdn())
                    imsi = st.text_input("IMSI", value=gen_imsi())
                    imei = st.text_input("IMEI", value=gen_imei())
                    city = st.selectbox("City", [c[0] for c in CITIES])
                with c2:
                    plan = st.selectbox("Plan", PLANS)
                    line_class = st.selectbox("Line Class", LINE_CLASSES)
                    kyc = st.number_input("KYC Age (days)", 0, 5000, 365)
                    qos = st.slider("Priority QoS", 0, 9, 3)
                with c3:
                    intl = st.checkbox("International Access")
                    fb = st.checkbox("Filter Bypass")
                    clir = st.checkbox("CLIR")
                    cliro = st.checkbox("CLIR Override")
                    li = st.checkbox("Lawful Intercept")
                    dr = st.checkbox("Direct Routing")
                    roa = st.checkbox("Roaming Enabled")
                st.markdown("##### Encryption")
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    enc_req = st.checkbox("Encryption Required")
                    e2e = st.checkbox("E2E Enabled")
                with ec2:
                    cipher = st.selectbox(
                        "Cipher Suite", ["None"] + list(CIPHER_SUITES.keys())
                    )
                with ec3:
                    key_id_in = st.text_input("Key ID", value="")
                    rot = st.number_input("Key Rotation (days)", 0, 365, 90)
                if st.form_submit_button("Add Subscriber",
                                         use_container_width=True):
                    try:
                        db_exec(
                            """INSERT INTO subscribers(
                                msisdn,imsi,imei,city,plan,kyc_age_days,
                                roaming_enabled,risk_score,line_class,
                                international_access,filter_bypass,clir_enabled,
                                clir_override,priority_qos,lawful_intercept,
                                direct_routing,whitelisted_asns,
                                encryption_required,cipher_suite,key_id,
                                key_rotation_days,e2e_enabled)
                                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (msisdn, imsi, imei, city, plan, kyc, int(roa), 0.1,
                             line_class, int(intl), int(fb), int(clir),
                             int(cliro), qos, int(li), int(dr), "",
                             int(enc_req), cipher,
                             key_id_in or (gen_key_id(imsi) if e2e else ""),
                             rot, int(e2e)),
                        )
                        log_audit("CREATE", "subscriber", msisdn,
                                  f"class={line_class}")
                        st.success("Added.")
                        st.rerun()
                    except sqlite3.IntegrityError as e:
                        st.error(f"Duplicate: {e}")
                    except Exception as e:
                        st.error(f"Error: {e}")

        elif action == "Edit":
            msisdn = st.text_input("MSISDN to edit", key="sub_edit_m")
            if msisdn:
                row = db_one(
                    "SELECT * FROM subscribers WHERE msisdn=?", (msisdn,)
                )
                if not row:
                    st.warning("Not found.")
                else:
                    cols = [
                        "msisdn", "imsi", "imei", "city", "plan",
                        "kyc_age_days", "roaming_enabled", "risk_score",
                        "line_class", "international_access", "filter_bypass",
                        "clir_enabled", "clir_override", "priority_qos",
                        "lawful_intercept", "direct_routing",
                        "whitelisted_asns", "encryption_required",
                        "cipher_suite", "key_id", "key_rotation_days",
                        "e2e_enabled",
                    ]
                    d = dict(zip(cols, row))
                    cl = [c[0] for c in CITIES]
                    with st.form("edit_sub"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.text_input("MSISDN", d["msisdn"],
                                          disabled=True)
                            st.text_input("IMSI", d["imsi"], disabled=True)
                            imei_new = st.text_input("IMEI", d["imei"])
                            city = st.selectbox(
                                "City", cl,
                                index=cl.index(d["city"])
                                if d["city"] in cl else 0,
                            )
                        with c2:
                            plan = st.selectbox(
                                "Plan", PLANS,
                                index=PLANS.index(d["plan"])
                                if d["plan"] in PLANS else 0,
                            )
                            line_class = st.selectbox(
                                "Line Class", LINE_CLASSES,
                                index=LINE_CLASSES.index(d["line_class"])
                                if d["line_class"] in LINE_CLASSES else 0,
                            )
                            qos = st.slider("Priority QoS", 0, 9,
                                            int(d["priority_qos"]))
                        with c3:
                            intl = st.checkbox(
                                "International",
                                bool(d["international_access"]))
                            fb = st.checkbox("Filter Bypass",
                                             bool(d["filter_bypass"]))
                            clir = st.checkbox("CLIR",
                                               bool(d["clir_enabled"]))
                            cliro = st.checkbox("CLIR Override",
                                                bool(d["clir_override"]))
                            li = st.checkbox("Lawful Intercept",
                                             bool(d["lawful_intercept"]))
                            dr = st.checkbox("Direct Routing",
                                             bool(d["direct_routing"]))
                            roa = st.checkbox("Roaming",
                                              bool(d["roaming_enabled"]))
                        cipher_l = ["None"] + list(CIPHER_SUITES.keys())
                        cipher = st.selectbox(
                            "Cipher Suite", cipher_l,
                            index=cipher_l.index(d["cipher_suite"])
                            if d["cipher_suite"] in cipher_l else 0,
                        )
                        if st.form_submit_button("Save",
                                                 use_container_width=True):
                            db_exec(
                                """UPDATE subscribers SET
                                    imei=?, city=?, plan=?, kyc_age_days=?,
                                    roaming_enabled=?, line_class=?,
                                    international_access=?, filter_bypass=?,
                                    clir_enabled=?, clir_override=?,
                                    priority_qos=?, lawful_intercept=?,
                                    direct_routing=?, cipher_suite=?
                                    WHERE msisdn=?""",
                                (imei_new, city, plan, d["kyc_age_days"],
                                 int(roa), line_class, int(intl), int(fb),
                                 int(clir), int(cliro), qos, int(li),
                                 int(dr), cipher, msisdn),
                            )
                            log_audit("UPDATE", "subscriber", msisdn,
                                      f"class={line_class}")
                            st.success("Updated.")
                            st.rerun()

        elif action == "Delete":
            msisdn = st.text_input("MSISDN to delete", key="sub_del_m")
            if msisdn:
                row = db_one(
                    "SELECT * FROM subscribers WHERE msisdn=?", (msisdn,)
                )
                if not row:
                    st.warning("Not found.")
                else:
                    st.json(dict(zip(
                        ["msisdn", "imsi", "imei", "city", "plan"], row[:5]
                    )))
                    if st.checkbox("Confirm", key="sub_del_c"):
                        if st.button("Delete", type="primary"):
                            db_exec(
                                "DELETE FROM subscribers WHERE msisdn=?",
                                (msisdn,),
                            )
                            log_audit("DELETE", "subscriber", msisdn, "")
                            st.success("Deleted.")
                            st.rerun()

    # ==================== TAB 2 — CELLS ====================
    with tabs[2]:
        st.subheader("Manage Cells")
        act = st.radio("Action", ["View", "Add", "Edit", "Delete"],
                       horizontal=True, key="cell_act",
                       label_visibility="collapsed")
        if act == "View":
            c1, c2 = st.columns(2)
            with c1:
                tf = st.multiselect(
                    "Tech", ["2G", "3G", "4G", "5G", "6G"],
                    default=["2G", "3G", "4G", "5G", "6G"], key="cell_tf",
                )
            with c2:
                lm = st.number_input("Limit", 50, 2000, 300, 50,
                                     key="cell_lim")
            sql = "SELECT * FROM cells"
            params = []
            if tf:
                sql += f" WHERE tech IN ({','.join('?'*len(tf))})"
                params += tf
            sql += f" LIMIT {int(lm)}"
            st.dataframe(db_df(sql, tuple(params)),
                         use_container_width=True, hide_index=True,
                         height=500)
        elif act == "Add":
            with st.form("add_cell"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    cid = st.text_input("Cell ID", key="cell_add_id")
                    nm = st.text_input("Name")
                    tc = st.selectbox("Tech",
                                      ["2G", "3G", "4G", "5G", "6G"])
                    ct = st.selectbox("City", [c[0] for c in CITIES])
                with c2:
                    la = st.number_input("Latitude", 20.0, 40.0, 35.6892,
                                         0.0001)
                    lo = st.number_input("Longitude", 40.0, 65.0, 51.3890,
                                         0.0001)
                    bd = st.selectbox(
                        "Band",
                        ["GSM-900", "GSM-1800", "UMTS-2100", "UMTS-900",
                         "LTE-B3", "LTE-B7", "LTE-B20", "LTE-B1",
                         "NR-n78", "NR-n41", "NR-n28",
                         "THz-140", "THz-220", "sub-THz-300", "mmWave-28"],
                    )
                with c3:
                    az = st.slider("Azimuth", 0, 359, 0, 30)
                    tl = st.slider("Tilt", 0, 15, 4)
                    tx = st.number_input("Tx Power", 10.0, 60.0, 40.0, 0.1)
                    bh = st.number_input("Backhaul", 0.1, 100.0, 10.0, 0.1)
                if st.form_submit_button("Add", use_container_width=True):
                    try:
                        db_exec(
                            "INSERT INTO cells VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                            (cid, nm, tc, ct, la, lo, bd, az, tl, tx, bh),
                        )
                        log_audit("CREATE", "cell", cid, tc)
                        st.success("Added.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        elif act == "Edit":
            cid = st.text_input("Cell ID", key="cell_edit_id")
            if cid:
                row = db_one("SELECT * FROM cells WHERE cell_id=?", (cid,))
                if row:
                    d = dict(zip(
                        ["cell_id", "name", "tech", "city", "lat", "lon",
                         "band", "azimuth", "tilt", "tx_dbm",
                         "backhaul_gbps"],
                        row,
                    ))
                    with st.form("edit_cell"):
                        nm = st.text_input("Name", d["name"])
                        az = st.slider("Azimuth", 0, 359,
                                       int(d["azimuth"]), 30)
                        tl = st.slider("Tilt", 0, 15, int(d["tilt"]))
                        tx = st.number_input("Tx Power", 10.0, 60.0,
                                             float(d["tx_dbm"]), 0.1)
                        bh = st.number_input("Backhaul", 0.1, 100.0,
                                             float(d["backhaul_gbps"]), 0.1)
                        if st.form_submit_button("Save",
                                                 use_container_width=True):
                            db_exec(
                                """UPDATE cells SET name=?,azimuth=?,tilt=?,
                                   tx_dbm=?,backhaul_gbps=? WHERE cell_id=?""",
                                (nm, az, tl, tx, bh, cid),
                            )
                            log_audit("UPDATE", "cell", cid, "")
                            st.success("Updated.")
                            st.rerun()
                else:
                    st.warning("Not found.")
        elif act == "Delete":
            cid = st.text_input("Cell ID", key="cell_del_id")
            if cid and db_one("SELECT 1 FROM cells WHERE cell_id=?", (cid,)):
                if st.checkbox("Confirm", key="cell_del_c"):
                    if st.button("Delete", type="primary"):
                        db_exec("DELETE FROM cells WHERE cell_id=?", (cid,))
                        log_audit("DELETE", "cell", cid, "")
                        st.success("Deleted.")
                        st.rerun()

    # ==================== TAB 3 — CORE NODES ====================
    with tabs[3]:
        st.subheader("Manage Core Nodes")
        act = st.radio("Action", ["View", "Add", "Edit", "Delete"],
                       horizontal=True, key="core_act",
                       label_visibility="collapsed")
        if act == "View":
            st.dataframe(
                db_df("SELECT * FROM cores ORDER BY role"),
                use_container_width=True, hide_index=True, height=500,
            )
        elif act == "Add":
            with st.form("add_core"):
                c1, c2 = st.columns(2)
                with c1:
                    nid = st.text_input("Node ID", key="core_add_id")
                    nm = st.text_input("Name")
                    rl = st.selectbox(
                        "Role",
                        ["MSC", "BSC", "RNC", "MME", "SGW", "PGW",
                         "HSS", "PCRF", "AMF", "SMF", "UPF", "IMS",
                         "MMSC", "RCS-AS", "NWDAF", "RIS-C", "ISAC",
                         "AI-RAN"],
                    )
                with c2:
                    tc = st.text_input("Tech", "4G/5G")
                    ct = st.selectbox("City", [c[0] for c in CITIES])
                    cp = st.number_input("Capacity (tps)", 1000,
                                         1_000_000, 100_000, 1000)
                if st.form_submit_button("Add", use_container_width=True):
                    try:
                        db_exec("INSERT INTO cores VALUES(?,?,?,?,?,?)",
                                (nid, nm, rl, tc, ct, cp))
                        log_audit("CREATE", "core", nid, rl)
                        st.success("Added.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        elif act == "Edit":
            nid = st.text_input("Node ID", key="core_edit_id")
            if nid:
                row = db_one("SELECT * FROM cores WHERE node_id=?", (nid,))
                if row:
                    d = dict(zip(
                        ["node_id", "name", "role", "tech", "city",
                         "capacity_tps"], row,
                    ))
                    with st.form("edit_core"):
                        nm = st.text_input("Name", d["name"])
                        cp = st.number_input("Capacity", 1000, 1_000_000,
                                             int(d["capacity_tps"]), 1000)
                        if st.form_submit_button("Save",
                                                 use_container_width=True):
                            db_exec(
                                "UPDATE cores SET name=?,capacity_tps=? "
                                "WHERE node_id=?",
                                (nm, cp, nid),
                            )
                            log_audit("UPDATE", "core", nid, "")
                            st.success("Updated.")
                            st.rerun()
                else:
                    st.warning("Not found.")
        elif act == "Delete":
            nid = st.text_input("Node ID", key="core_del_id")
            if nid and db_one("SELECT 1 FROM cores WHERE node_id=?", (nid,)):
                if st.checkbox("Confirm", key="core_del_c"):
                    if st.button("Delete", type="primary"):
                        db_exec("DELETE FROM cores WHERE node_id=?", (nid,))
                        log_audit("DELETE", "core", nid, "")
                        st.success("Deleted.")
                        st.rerun()

    # ==================== TAB 4 — ALERTS ====================
    with tabs[4]:
        st.subheader("Manage Alerts")
        c1, c2, c3 = st.columns(3)
        with c1:
            sv = st.multiselect(
                "Severity",
                ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                default=["CRITICAL", "HIGH", "MEDIUM", "LOW"], key="al_sv",
            )
        with c2:
            ak = st.selectbox(
                "ACK Status",
                ["All", "Unacknowledged", "Acknowledged"], key="al_ak",
            )
        with c3:
            lm = st.number_input("Limit", 10, 1000, 100, 10, key="al_lm")
        sql = "SELECT * FROM alerts WHERE 1=1"
        params = []
        if sv:
            sql += f" AND severity IN ({','.join('?'*len(sv))})"
            params += sv
        if ak == "Unacknowledged":
            sql += " AND ack=0"
        elif ak == "Acknowledged":
            sql += " AND ack=1"
        sql += f" ORDER BY timestamp DESC LIMIT {int(lm)}"
        df = db_df(sql, tuple(params))
        st.caption(f"{len(df)} alerts")
        st.dataframe(
            df[["alert_id", "timestamp", "severity", "alert_type",
                "msisdn", "description", "ack"]],
            use_container_width=True, hide_index=True, height=400,
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("ACK All", use_container_width=True):
                db_exec("UPDATE alerts SET ack=1 WHERE ack=0")
                log_audit("ACK_ALL", "alert", "-", "")
                st.success("ACKed.")
                st.rerun()
        with c2:
            if st.button("Un-ACK All", use_container_width=True):
                db_exec("UPDATE alerts SET ack=0")
                log_audit("UNACK_ALL", "alert", "-", "")
                st.success("Un-ACKed.")
                st.rerun()
        with c3:
            if st.button("Delete ACKed", use_container_width=True):
                db_exec("DELETE FROM alerts WHERE ack=1")
                log_audit("DELETE_ACKED", "alert", "-", "")
                st.success("Deleted.")
                st.rerun()
        st.markdown("#### Add Manual Alert")
        with st.form("add_alert"):
            c1, c2, c3 = st.columns(3)
            with c1:
                sv2 = st.selectbox("Severity",
                                   ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
                at = st.text_input("Alert Type", "MANUAL")
            with c2:
                ms2 = st.text_input("Related MSISDN", "-")
                snd = st.checkbox("Send SMS to SOC", value=True)
            with c3:
                ds = st.text_area("Description", height=68)
            if st.form_submit_button("Create Alert",
                                     use_container_width=True):
                nid = (f"ALT-{datetime.now():%Y%m%d}-MAN"
                       f"{random.randint(1000, 9999)}")
                to = random.choice(
                    ["989120000001", "989120000002", "989120000003"]
                )
                db_exec(
                    """INSERT INTO alerts(alert_id,timestamp,severity,
                        alert_type,msisdn,description,extra,sms_sent,sms_to,
                        sms_body,ack) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (nid, f"{datetime.now():%Y-%m-%d %H:%M:%S}", sv2, at,
                     ms2, ds, "{}", int(snd), to if snd else "",
                     f"[{sv2}] {at} | {ds[:80]}" if snd else "", 0),
                )
                log_audit("CREATE", "alert", nid, at)
                st.success(f"Created {nid}.")
                st.rerun()

    # ==================== TAB 5 — SPECIAL LINES ====================
    with tabs[5]:
        st.subheader("Special Lines Management")
        c1, c2 = st.columns(2)
        with c1:
            lc_s = st.multiselect(
                "Line Class",
                ["VIP", "Government", "Corporate", "Emergency", "Test"],
                default=["VIP", "Government", "Corporate", "Emergency",
                         "Test"],
                key="sl_lc",
            )
        with c2:
            ob = st.checkbox("Only filter-bypass", key="sl_ob")
            oc = st.checkbox("Only CLIR", key="sl_oc")
        sql = ("SELECT * FROM subscribers "
               "WHERE line_class != 'Normal'")
        params = []
        if lc_s:
            sql += f" AND line_class IN ({','.join('?'*len(lc_s))})"
            params += lc_s
        if ob:
            sql += " AND filter_bypass=1"
        if oc:
            sql += " AND clir_enabled=1"
        df = db_df(sql, tuple(params))
        st.caption(f"{len(df)} special subscribers")
        st.dataframe(df, use_container_width=True, hide_index=True,
                     height=400)
        st.markdown("#### Bulk Update")
        newc = st.selectbox(
            "Change ALL to:",
            ["VIP", "Government", "Corporate", "Emergency", "Test",
             "Normal"],
        )
        if st.checkbox("I understand", key="sl_blk_c"):
            if st.button("Apply"):
                if len(df) > 0:
                    n = db_chunked_in_update(
                        "subscribers", "msisdn", "line_class=?",
                        [newc], df["msisdn"].tolist(),
                    )
                    log_audit("BULK_UPDATE", "subscriber", f"{n}",
                              f"class={newc}")
                    st.success(f"Updated {n}.")
                    st.rerun()
        st.markdown("#### Single Toggle")
        msisdn = st.text_input("MSISDN", key="sl_msisdn_toggle")
        if msisdn:
            row = db_one(
                """SELECT msisdn,line_class,international_access,
                    filter_bypass,clir_enabled,clir_override,priority_qos,
                    lawful_intercept,direct_routing
                    FROM subscribers WHERE msisdn=?""",
                (msisdn,),
            )
            if not row:
                st.warning("Not found.")
            else:
                st.write(dict(zip(
                    ["msisdn", "class", "intl", "fb", "clir", "cliro",
                     "qos", "li", "dr"],
                    row,
                )))
                with st.form("toggle_sl"):
                    p1, p2, p3 = st.columns(3)
                    with p1:
                        nlc = st.selectbox(
                            "Line Class", LINE_CLASSES,
                            index=LINE_CLASSES.index(row[1])
                            if row[1] in LINE_CLASSES else 0,
                        )
                        intl = st.checkbox("International", bool(row[2]))
                        fb = st.checkbox("Filter Bypass", bool(row[3]))
                    with p2:
                        clir = st.checkbox("CLIR", bool(row[4]))
                        cliro = st.checkbox("CLIR Override", bool(row[5]))
                        qos = st.slider("QoS", 0, 9, int(row[6]))
                    with p3:
                        li = st.checkbox("Lawful Intercept", bool(row[7]))
                        dr = st.checkbox("Direct Routing", bool(row[8]))
                    if st.form_submit_button("Save",
                                             use_container_width=True):
                        db_exec(
                            """UPDATE subscribers SET line_class=?,
                                international_access=?,filter_bypass=?,
                                clir_enabled=?,clir_override=?,priority_qos=?,
                                lawful_intercept=?,direct_routing=?
                                WHERE msisdn=?""",
                            (nlc, int(intl), int(fb), int(clir),
                             int(cliro), qos, int(li), int(dr), msisdn),
                        )
                        log_audit("PERM_UPDATE", "subscriber", msisdn,
                                  f"class={nlc}")
                        st.success("Saved.")
                        st.rerun()

    # ==================== TAB 6 — ENCRYPTION ====================
    with tabs[6]:
        st.subheader("Encryption Management")
        df = db_df(
            """SELECT msisdn,line_class,cipher_suite,key_id,
                key_rotation_days,e2e_enabled,encryption_required
                FROM subscribers WHERE e2e_enabled=1"""
        )
        st.caption(f"{len(df)} encrypted subscribers")
        st.dataframe(df.head(500), use_container_width=True,
                     hide_index=True, height=400)
        st.markdown("#### Rotate Keys")
        c1, c2 = st.columns(2)
        with c1:
            rc = st.multiselect(
                "Classes:",
                ["VIP", "Government", "Corporate", "Emergency", "Test"],
                default=["Government", "Emergency"], key="enc_rc",
            )
        with c2:
            nc = st.selectbox("New cipher", list(CIPHER_SUITES.keys()),
                              key="enc_nc")
        if st.button("Rotate Now", type="primary"):
            if rc:
                ph = ",".join("?" * len(rc))
                rows = db_df(
                    f"SELECT msisdn FROM subscribers "
                    f"WHERE line_class IN ({ph})",
                    tuple(rc),
                )
                n = 0
                for _, r in rows.iterrows():
                    db_exec(
                        "UPDATE subscribers SET key_id=?,cipher_suite=? "
                        "WHERE msisdn=?",
                        (gen_key_id(r["msisdn"]), nc, r["msisdn"]),
                    )
                    n += 1
                log_audit("KEY_ROTATE", "encryption", f"{n}",
                          f"cipher={nc}")
                st.success(f"Rotated {n}.")
                st.rerun()

        st.markdown("#### Single Subscriber Edit")
        msisdn = st.text_input("MSISDN", key="enc_msisdn_edit")
        if msisdn:
            row = db_one(
                """SELECT msisdn,cipher_suite,key_id,e2e_enabled,
                    encryption_required,key_rotation_days
                    FROM subscribers WHERE msisdn=?""",
                (msisdn,),
            )
            if not row:
                st.warning("Not found.")
            else:
                st.write(dict(zip(
                    ["msisdn", "cipher", "key_id", "e2e", "req", "rot"],
                    row,
                )))
                cl = ["None"] + list(CIPHER_SUITES.keys())
                with st.form("enc_edit"):
                    e2e = st.checkbox("E2E Enabled", bool(row[3]))
                    er = st.checkbox("Encryption Required", bool(row[4]))
                    cs = st.selectbox(
                        "Cipher", cl,
                        index=cl.index(row[1]) if row[1] in cl else 0,
                    )
                    rt = st.number_input("Rotation days", 0, 365,
                                         int(row[5]))
                    nk = st.text_input("New Key ID (blank=keep)", "")
                    if st.form_submit_button("Save",
                                             use_container_width=True):
                        kid = nk.strip() or row[2]
                        db_exec(
                            """UPDATE subscribers SET e2e_enabled=?,
                                encryption_required=?,cipher_suite=?,
                                key_rotation_days=?,key_id=?
                                WHERE msisdn=?""",
                            (int(e2e), int(er), cs, rt, kid, msisdn),
                        )
                        log_audit("ENC_UPDATE", "subscriber", msisdn,
                                  f"cipher={cs}")
                        st.success("Saved.")
                        st.rerun()

    # ==================== TAB 7 — BACKUP ====================
    with tabs[7]:
        st.subheader("Backup & Restore")
        lbl = st.text_input("Backup label", "manual", key="bk_lbl")
        if st.button("Create Backup", use_container_width=True):
            p = create_backup(lbl)
            log_audit("BACKUP", "db", p, "")
            st.success(f"Created: {p}")
        st.markdown("#### Backups")
        bks = list_backups()
        if bks:
            for b in bks[:20]:
                c1, c2, c3 = st.columns([3, 1, 1])
                mb = os.path.getsize(os.path.join(BACKUP_DIR, b)) / 1e6
                with c1:
                    st.write(f"{b} -- {mb:.2f} MB")
                with c2:
                    with open(os.path.join(BACKUP_DIR, b), "rb") as f:
                        st.download_button(
                            "DL", f.read(), b, "application/x-sqlite3",
                            key=f"dl_{b}",
                        )
                with c3:
                    if st.button("Restore", key=f"rs_{b}"):
                        try:
                            restored = restore_backup(b)
                            log_audit("RESTORE", "db", b, "ok")
                            st.cache_data.clear()
                            st.success(
                                f"Restored {os.path.basename(restored)}. "
                                f"Reloading…"
                            )
                            st.rerun()
                        except Exception as e:
                            log_audit("RESTORE_FAILED", "db", b, str(e))
                            st.error(f"Restore failed: {e}")
        else:
            st.info("No backups.")
        st.divider()
        if st.button("Export DB to JSON"):
            all_data = {}
            for t in ["subscribers", "cells", "cores", "alerts",
                      "audit_log", "attack_scenarios", "attack_events"]:
                try:
                    all_data[t] = db_df(
                        f"SELECT * FROM {t}"
                    ).to_dict(orient="records")
                except Exception:
                    pass
            st.download_button(
                "Download JSON",
                json.dumps(all_data, ensure_ascii=False, indent=2,
                           default=str),
                "telecom_export.json", "application/json",
            )
            log_audit("EXPORT", "db", "json", "")
        if st.checkbox("Delete ALL subscribers", key="rs_c"):
            if st.button("Delete ALL Subscribers", type="primary"):
                db_exec("DELETE FROM subscribers")
                log_audit("RESET", "subscribers", "ALL", "")
                st.success("Deleted.")
                st.rerun()

    # ==================== TAB 8 — AUDIT ====================
    with tabs[8]:
        st.subheader("Audit Log")
        c1, c2, c3 = st.columns(3)
        with c1:
            aa = db_df(
                "SELECT DISTINCT action FROM audit_log"
            )["action"].tolist()
            af = st.multiselect("Action", sorted(aa), default=sorted(aa),
                                key="au_a")
        with c2:
            ee = db_df(
                "SELECT DISTINCT entity FROM audit_log"
            )["entity"].tolist()
            ef = st.multiselect("Entity", sorted(ee), default=sorted(ee),
                                key="au_e")
        with c3:
            lm = st.number_input("Limit", 50, 5000, 500, 50, key="au_l")
        sql = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        if af:
            sql += f" AND action IN ({','.join('?'*len(af))})"
            params += af
        if ef:
            sql += f" AND entity IN ({','.join('?'*len(ef))})"
            params += ef
        sql += f" ORDER BY id DESC LIMIT {int(lm)}"
        df = db_df(sql, tuple(params))
        st.caption(f"{len(df)} records")
        st.dataframe(df, use_container_width=True, hide_index=True,
                     height=500)
        st.download_button(
            "CSV", df.to_csv(index=False).encode("utf-8-sig"),
            "audit_log.csv", "text/csv",
        )
        st.divider()
        if st.button("Clear Audit Log (>30 days)"):
            cut = (datetime.now() - timedelta(days=30)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            db_exec("DELETE FROM audit_log WHERE ts < ?", (cut,))
            log_audit("CLEAR", "audit_log", ">30d", "")
            st.success("Cleared.")
            st.rerun()


# ------------------------------------------------------------------
# Entry point — runs under `streamlit run` but NOT on plain import.
# ------------------------------------------------------------------

if __name__ == "__main__":
        main()      



