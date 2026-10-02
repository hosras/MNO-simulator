"""Login rate-limit helpers.

Counter lives in audit_log (not session_state) so browser refresh
and app restart cannot clear it.
"""

from datetime import datetime, timedelta

from admin._config import LOGIN_MAX_FAILS, LOGIN_WINDOW_MIN
from telecom_common import db_one


def count_recent_failed_logins(minutes: int = LOGIN_WINDOW_MIN) -> int:
    """Count LOGIN_FAILED entries in audit_log within the last N minutes."""
    cutoff = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        row = db_one(
            "SELECT COUNT(*) FROM audit_log " "WHERE action='LOGIN_FAILED' AND ts >= ?",
            (cutoff,),
        )
        return int(row[0]) if row else 0
    except Exception:
        return 0


def lockout_remaining_sec() -> int:
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
