# -*- coding: utf-8 -*-
"""Thin wrappers re-exported so views import from one place."""
from telecom_common import (
    db_df, db_exec, db_one, db_count, db_chunked_in_update,
)

__all__ = ["db_df", "db_exec", "db_one", "db_count", "db_chunked_in_update"]