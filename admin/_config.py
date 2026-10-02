"""Package-level constants shared across admin modules."""

import os

from telecom_common import OUT_DIR

DB_PATH = "telecom_sim_output/telecom_sim.db"
BACKUP_DIR = os.path.join(OUT_DIR, "backups")

# Login rate-limit policy
LOGIN_WINDOW_MIN = 15
LOGIN_MAX_FAILS = 5

# Line classes for bulk update
BULK_UPDATE_CLASSES = [
    "VIP",
    "Government",
    "Corporate",
    "Emergency",
    "Test",
    "Normal",
]
