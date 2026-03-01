"""Tests for the application logger utility."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def reset_logger():
    """Reset the logger singleton and logging state between tests."""
    import todopro_cli.utils.logger as logger_mod

    original = logger_mod._logger
    logger_mod._logger = None

    existing = logging.getLogger("todopro_cli")
    existing.handlers.clear()

    yield

    logger_mod._logger = None
    logging.getLogger("todopro_cli").handlers.clear()
    logger_mod._logger = original


def test_get_logger_creates_log_file(tmp_path):
    """Logger creates the log file inside user_log_dir."""
    with patch("todopro_cli.utils.logger.user_log_dir", return_value=str(tmp_path)):
        from todopro_cli.utils.logger import get_logger

        logger = get_logger()

    log_file = tmp_path / "todopro.log"
    assert log_file.exists(), "Log file should be created on first use"
    assert isinstance(logger, logging.Logger)


def test_get_logger_returns_singleton(tmp_path):
    """Repeated calls return the same logger instance."""
    with patch("todopro_cli.utils.logger.user_log_dir", return_value=str(tmp_path)):
        from todopro_cli.utils.logger import get_logger

        l1 = get_logger()
        l2 = get_logger()

    assert l1 is l2


def test_get_logger_writes_message(tmp_path):
    """Messages written to the logger appear in the log file."""
    with patch("todopro_cli.utils.logger.user_log_dir", return_value=str(tmp_path)):
        from todopro_cli.utils.logger import get_logger

        logger = get_logger()
        logger.info("hello from test")

    # Flush handlers
    for handler in logger.handlers:
        handler.flush()

    content = (tmp_path / "todopro.log").read_text()
    assert "hello from test" in content


def test_get_logger_creates_parent_dirs(tmp_path):
    """Logger creates nested directories if they do not exist."""
    nested = tmp_path / "a" / "b" / "c"
    with patch("todopro_cli.utils.logger.user_log_dir", return_value=str(nested)):
        from todopro_cli.utils.logger import get_logger

        get_logger()

    assert nested.is_dir()
