"""Application-wide logger writing to platformdirs user_log_dir."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from platformdirs import user_log_dir

_APP_NAME = "todopro_cli"
_LOG_FILE = "todopro.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3

_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    """Return the singleton application logger, initialising it on first call."""
    global _logger
    if _logger is not None:
        return _logger

    log_dir = Path(user_log_dir(_APP_NAME))
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        log_dir / _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    logger = logging.getLogger(_APP_NAME)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        logger.addHandler(handler)
    logger.propagate = False

    _logger = logger
    return _logger
