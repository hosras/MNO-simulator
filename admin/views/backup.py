# -*- coding: utf-8 -*-
"""Tab 7 — Backup & Restore."""
import json
import os

import streamlit as st

from admin._config import BACKUP_DIR
from admin.services.db import db_df, db_exec
from admin.services.audit import log_audit
from admin.services.backup import (
    create_backup, list_backups, restore_backup,
)


def render():
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
            json.dumps(all_data, ensure_ascii=False, indent=2, default=str),
            "telecom_export.json", "application/json",
        )
        log_audit("EXPORT", "db", "json", "")

    if st.checkbox("Delete ALL subscribers", key="rs_c"):
        if st.button("Delete ALL Subscribers", type="primary"):
            db_exec("DELETE FROM subscribers")
            log_audit("RESET", "subscribers", "ALL", "")
            st.success("Deleted.")
            st.rerun()