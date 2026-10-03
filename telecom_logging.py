"""Centralized logging configuration for TELECOM-NET-SIM.

Provides:
    setup_logging(level, log_file, simple) -> None
    get_logger(name) -> logging.Logger

Design:
    - Console handler writes to stdout with a compact format.
    - Optional file handler writes to disk (UTF-8).
    - The "report" output (the final summary at the end of a run) is NOT
      logging — it stays as `print()` so it can be piped/redirected.
    - Library modules should call `get_logger(__name__)`. The entry points
      (telecom_net_sim, telecom_attack) call `setup_logging()` once.

Levels:
    DEBUG    - per-record details (use --verbose)
    INFO     - progress messages (default)
    WARNING  - recoverable issues
    ERROR    - hard failures
    CRITICAL - unusable state
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# ------------------------------------------------------------------
# Formats
# ------------------------------------------------------------------
_VERBOSE_FMT = "%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s"
_SIMPLE_FMT = "%(levelname)s: %(message)s"
_DATE_FMT = "%H:%M:%S"


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------
def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    simple: bool = False,
) -> None:
    """Configure the root logger.

    Idempotent: safe to call multiple times — old handlers are removed.

    Args:
        level: one of DEBUG / INFO / WARNING / ERROR / CRITICAL.
        log_file: optional path to a log file (UTF-8).
        simple: if True, use a compact format without timestamps.
    """
    root = logging.getLogger()

    # Remove any handlers added by previous calls (important for tests).
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = _SIMPLE_FMT if simple else _VERBOSE_FMT
    formatter = logging.Formatter(fmt, datefmt=_DATE_FMT)

    # Console handler
    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    # File handler (optional)
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(path, encoding="utf-8", mode="a")
        fh.setFormatter(formatter)
        root.addHandler(fh)

    root.setLevel(_parse_level(level))


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger.

    Thin wrapper around ``logging.getLogger`` so callers depend only on
    this module, not directly on the stdlib.
    """
    return logging.getLogger(name)


def _parse_level(level: str) -> int:
    """Convert a level name to its numeric value (case-insensitive)."""
    if isinstance(level, int):
        return level
    return getattr(logging, str(level).upper(), logging.INFO)


def silence(name: str, level: int = logging.WARNING) -> None:
    """Raise the level of a specific logger.

    Useful for quieting noisy third-party libraries.
    """
    logging.getLogger(name).setLevel(level)


__all__ = ["setup_logging", "get_logger", "silence"]
