"""The detector opens exactly one incident and wakes the agent once."""

import time

from conftest import add_job

from common import config, db
from service import detector


def test_opens_one_incident_and_triggers_once(conn, monkeypatch):
    monkeypatch.setattr(config, "INCIDENT_MIN_DELAYED", 3)
    calls = []
    for i in range(3):
        add_job(conn, "CUST-NORTHWIND", time.time() - 60 - i)

    first = detector.tick(conn, trigger=lambda iid, s: calls.append(iid))
    second = detector.tick(conn, trigger=lambda iid, s: calls.append(iid))

    assert first == "INC-0001" and second is None
    assert calls == ["INC-0001"]
    assert db.open_incident(conn)["status"] == "open"
    assert conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0] == 2


def test_no_incident_when_healthy(conn):
    add_job(conn, "CUST-ACORN", time.time() - 5)
    assert detector.tick(conn, trigger=lambda *a: None) is None


def test_trigger_failure_still_records_incident(conn, monkeypatch):
    monkeypatch.setattr(config, "INCIDENT_MIN_DELAYED", 1)
    add_job(conn, "CUST-ACORN", time.time() - 60)

    def boom(*_):
        raise RuntimeError("sandbox not up")

    assert detector.tick(conn, trigger=boom) == "INC-0001"
