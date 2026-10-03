"""Logging setup shared by every long-running Pitcrew process."""

from __future__ import annotations

import logging
from pathlib import Path

from common import config

LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"

# Libraries that log full request URLs at INFO. Telegram Bot API URLs embed the bot token,
# so these must never log below WARNING.
_URL_LOGGING_LIBRARIES = ("httpx", "httpcore")


def configure_logging(log_file: Path) -> None:
    """Log to `log_file` and the console, with secret-bearing library logs suppressed."""
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT,
                        handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
    for name in _URL_LOGGING_LIBRARIES:
        logging.getLogger(name).setLevel(logging.WARNING)
