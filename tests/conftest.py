import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from common import config, db  # noqa: E402


@pytest.fixture
def conn(tmp_path, monkeypatch):
    """A fresh database per test; nothing touches data/pitcrew.db or logs/."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "pitcrew.db")
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(config, "RUN_DIR", tmp_path / "run")
    monkeypatch.setattr(config, "SERVICE_LOG", tmp_path / "logs" / "service.log")
    monkeypatch.setattr(config, "SERVICE_STATUS_FILE", tmp_path / "run" / "service_status.json")
    monkeypatch.setattr(config, "APPROVER_BOT_TOKEN", "")
    monkeypatch.setattr(config, "TOOLSERVER_STUB", False)
    from service.seed import seed
    seed()
    c = db.connect()
    yield c
    c.close()


def add_job(conn, customer_id, created_at, status="pending", started_at=None, price=None):
    from service.seed import PRICE
    conn.execute(
        "INSERT INTO jobs (customer_id, created_at, started_at, status, price) VALUES (?, ?, ?, ?, ?)",
        (customer_id, created_at, started_at, status, PRICE[customer_id] if price is None else price))
