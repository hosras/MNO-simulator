"""Unit tests for telecom_logging."""

import logging
import sys
from pathlib import Path

import pytest

from telecom_logging import get_logger, setup_logging, silence


# ==================================================================
# setup_logging — console handler
# ==================================================================
class TestSetupConsole:
    def test_creates_console_handler(self):
        setup_logging(level="INFO")
        root = logging.getLogger()
        assert any(
            isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
            for h in root.handlers
        )

    def test_idempotent_no_duplicate_handlers(self):
        setup_logging()
        setup_logging()
        setup_logging()
        root = logging.getLogger()
        # At most one console + one file
        assert len(root.handlers) <= 2

    def test_sets_info_level(self):
        setup_logging(level="INFO")
        assert logging.getLogger().level == logging.INFO

    def test_sets_debug_level(self):
        setup_logging(level="DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_sets_warning_level(self):
        setup_logging(level="WARNING")
        assert logging.getLogger().level == logging.WARNING

    def test_level_is_case_insensitive(self):
        setup_logging(level="debug")
        assert logging.getLogger().level == logging.DEBUG

    def test_invalid_level_defaults_to_info(self):
        setup_logging(level="NOPE")
        assert logging.getLogger().level == logging.INFO

    def test_simple_format(self):
        setup_logging(simple=True)
        root = logging.getLogger()
        handler = root.handlers[0]
        assert handler.formatter is not None
        assert "asctime" not in handler.formatter._fmt

    def test_verbose_format(self):
        setup_logging(simple=False)
        root = logging.getLogger()
        handler = root.handlers[0]
        assert "asctime" in handler.formatter._fmt


# ==================================================================
# setup_logging — file handler
# ==================================================================
class TestSetupFile:
    def test_creates_file_handler(self, tmp_path):
        log_file = tmp_path / "test.log"
        setup_logging(level="INFO", log_file=str(log_file))
        root = logging.getLogger()
        assert any(isinstance(h, logging.FileHandler) for h in root.handlers)

    def test_writes_to_file(self, tmp_path):
        log_file = tmp_path / "test.log"
        setup_logging(level="INFO", log_file=str(log_file))

        logger = get_logger("test.file")
        logger.info("hello world")

        # Force flush
        for h in logging.getLogger().handlers:
            if isinstance(h, logging.FileHandler):
                h.flush()

        content = log_file.read_text(encoding="utf-8")
        assert "hello world" in content

    def test_creates_parent_dirs(self, tmp_path):
        log_file = tmp_path / "subdir" / "another" / "test.log"
        setup_logging(level="INFO", log_file=str(log_file))
        assert log_file.parent.is_dir()

    def test_appends_to_existing_file(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("PRE-EXISTING\n", encoding="utf-8")

        setup_logging(level="INFO", log_file=str(log_file))
        logger = get_logger("test.append")
        logger.info("new line")

        for h in logging.getLogger().handlers:
            if isinstance(h, logging.FileHandler):
                h.flush()

        content = log_file.read_text(encoding="utf-8")
        assert "PRE-EXISTING" in content
        assert "new line" in content


# ==================================================================
# get_logger
# ==================================================================
class TestGetLogger:
    def test_returns_logger(self):
        logger = get_logger("my.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "my.module"

    def test_returns_same_instance(self):
        a = get_logger("m")
        b = get_logger("m")
        assert a is b


# ==================================================================
# silence
# ==================================================================
class TestSilence:
    def test_silence_sets_level(self):
        silence("noisy.lib", level=logging.ERROR)
        assert logging.getLogger("noisy.lib").level == logging.ERROR

    def test_silence_default_is_warning(self):
        # Reset first
        logging.getLogger("another").setLevel(logging.NOTSET)
        silence("another")
        assert logging.getLogger("another").level == logging.WARNING


# ==================================================================
# End-to-end
# ==================================================================
class TestEndToEnd:
    def test_logger_output_goes_to_file(self, tmp_path):
        log_file = tmp_path / "e2e.log"
        setup_logging(level="DEBUG", log_file=str(log_file))

        logger = get_logger("e2e.test")
        logger.debug("debug msg")
        logger.info("info msg")
        logger.warning("warn msg")
        logger.error("err msg")

        for h in logging.getLogger().handlers:
            h.flush()

        content = log_file.read_text(encoding="utf-8")
        for msg in ("debug msg", "info msg", "warn msg", "err msg"):
            assert msg in content

    def test_level_filtering(self, tmp_path):
        log_file = tmp_path / "filtered.log"
        setup_logging(level="WARNING", log_file=str(log_file))

        logger = get_logger("filter.test")
        logger.info("should not appear")
        logger.warning("should appear")

        for h in logging.getLogger().handlers:
            h.flush()

        content = log_file.read_text(encoding="utf-8")
        assert "should not appear" not in content
        assert "should appear" in content
