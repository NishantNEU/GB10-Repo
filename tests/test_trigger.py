"""The trigger posts the opened alert first, retries a failed agent turn once, and never fails silently."""

from types import SimpleNamespace

import pytest

from skills import trigger


@pytest.fixture
def fake(monkeypatch, tmp_path):
    sent, runs = [], []
    monkeypatch.setenv("PITCREW_CHAT_ID", "123")
    monkeypatch.setattr(trigger, "REPO", tmp_path)
    monkeypatch.setattr(trigger, "RETRY_DELAY_S", 0)
    monkeypatch.setattr(trigger, "send_telegram", lambda text: sent.append(text) or True)
    return SimpleNamespace(sent=sent, runs=runs, set_exit_codes=lambda codes: monkeypatch.setattr(
        trigger.subprocess, "run", lambda cmd, **kw: runs.append(cmd) or SimpleNamespace(returncode=codes.pop(0))))


DETAILS = {"service_status": "degraded", "mem_avail_gb": 16.9, "delayed_jobs": 5,
           "affected_customers": 3, "longest_wait": "41s"}


def test_opened_alert_then_one_agent_turn(fake):
    fake.set_exit_codes([0])
    assert trigger.trigger_agent("INC-0001", "x", details=DETAILS, wait=True) == 0
    assert len(fake.runs) == 1
    assert fake.sent[0].startswith("🚨 Incident INC-0001 opened")
    assert "5 jobs delayed across 3 fictional customers" in fake.sent[0]
    assert len(fake.sent) == 1          # no backup alert


def test_retry_succeeds(fake):
    fake.set_exit_codes([1, 0])
    assert trigger.trigger_agent("INC-0002", "x", wait=True) == 0
    assert len(fake.runs) == 2 and fake.sent == []


def test_backup_alert_when_agent_never_answers(fake):
    fake.set_exit_codes([1, 1])
    assert trigger.trigger_agent("INC-0003", "x", wait=True) == 1
    assert len(fake.runs) == 2
    assert fake.sent[-1].startswith("⚠️ Incident INC-0003 is open, but the Pitcrew agent did not respond")
    assert "Nothing has been stopped" in fake.sent[-1]
