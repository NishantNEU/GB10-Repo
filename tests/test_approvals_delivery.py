"""Approval-code delivery: email is preferred, uses STARTTLS + login, and falls back cleanly."""

import pytest

from common import config
from toolserver import approvals


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host, port, timeout):
        self.host, self.port, self.timeout = host, port, timeout
        self.calls, self.sent = [], []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user))

    def send_message(self, msg):
        self.calls.append("send")
        self.sent.append(msg)


@pytest.fixture
def smtp(monkeypatch, tmp_path):
    FakeSMTP.instances.clear()
    monkeypatch.setattr(approvals.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    for key, value in {"APPROVER_EMAIL": "oncall@example.com", "SMTP_HOST": "smtp.example.com",
                       "SMTP_PORT": 587, "SMTP_USERNAME": "pitcrew@example.com",
                       "SMTP_PASSWORD": "app-password", "SMTP_FROM": "",
                       "APPROVER_BOT_TOKEN": "", "ONCALL_CHAT_ID": ""}.items():
        monkeypatch.setattr(config, key, value)
    return FakeSMTP


def test_email_is_used_when_configured(smtp):
    via = approvals.send_code("APR-0001", "INC-0001", "pitcrew-test-hog", "largest memory user", "4821")
    assert via == "email"
    s = smtp.instances[0]
    assert (s.host, s.port) == ("smtp.example.com", 587)
    assert s.calls == ["starttls", ("login", "pitcrew@example.com"), "send"]   # TLS before credentials
    msg = s.sent[0]
    assert msg["To"] == "oncall@example.com" and msg["From"] == "pitcrew@example.com"
    assert "4821" in msg.get_content() and "pitcrew-test-hog" in msg["Subject"]


def test_falls_back_to_local_log_without_email_or_bot(smtp, monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SMTP_PASSWORD", "")
    assert approvals.send_code("APR-0002", "INC-0001", "pitcrew-test-hog", "x", "1234") == "local_log"
    assert smtp.instances == []
    assert "1234" in (tmp_path / "approval_codes.log").read_text()
