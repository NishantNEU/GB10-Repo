"""Regression: the Telegram bot token must never reach a log file (found in rehearsal 3)."""

import logging

from common import config
from common.logsetup import configure_logging


def test_url_logging_libraries_are_silenced(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    configure_logging(tmp_path / "x.log")
    logging.getLogger("httpx").info("POST https://api.telegram.org/botSECRET-TOKEN/sendMessage")
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert "SECRET-TOKEN" not in (tmp_path / "x.log").read_text()
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
