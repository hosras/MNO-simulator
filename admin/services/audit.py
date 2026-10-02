"""Audit log: schema init + append helper."""

from datetime import datetime

from admin.services.auth import current_user
from telecom_common import db_exec


def init_audit() -> None:
    db_exec("""CREATE TABLE IF NOT EXISTS audit_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, user TEXT,
        action TEXT, entity TEXT, entity_id TEXT, details TEXT)""")


def log_audit(action: str, entity: str, entity_id, details: str = "") -> None:
    db_exec(
        "INSERT INTO audit_log(ts,user,action,entity,entity_id,details) " "VALUES(?,?,?,?,?,?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            current_user(),
            action,
            entity,
            str(entity_id),
            details,
        ),
    )
