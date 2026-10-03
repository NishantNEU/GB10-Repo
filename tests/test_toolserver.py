"""Approval safety (spec section 13): wrong code refused, deny means no action, only the hog stops."""

import json
import time

import pytest
from fastapi.testclient import TestClient

from common import config
from toolserver import app as app_module
from toolserver import approvals, docker_ops


@pytest.fixture
def client(conn, monkeypatch):
    sent, stopped = {}, []
    monkeypatch.setattr(approvals, "send_code",
                        lambda aid, iid, target, reason, code: sent.setdefault(aid, code) and "test")
    monkeypatch.setattr(docker_ops, "is_test_container", lambda name: name == config.HOG_CONTAINER)
    monkeypatch.setattr(docker_ops, "stop_container", lambda name: (stopped.append(name) or True, "ok"))
    conn.execute("INSERT INTO incidents (id, opened_at, status, trigger) VALUES ('INC-0001', ?, 'open', ?)",
                 (time.time(), json.dumps({"rule": "test"})))
    c = TestClient(app_module.app)
    c.sent, c.stopped = sent, stopped
    return c


def _request(client):
    r = client.post("/approvals", json={"incident_id": "INC-0001", "action": "stop_test_program",
                                        "target": config.HOG_CONTAINER, "reason": "largest memory user"})
    assert r.status_code == 200, r.text
    return r.json()["approval_id"]


def test_right_code_stops_only_the_hog(client):
    aid = _request(client)
    assert client.get("/incidents/current").json()["pending_approval_id"] == aid
    r = client.post("/actions/stop_test_program", json={"approval_id": aid, "code": client.sent[aid]})
    assert r.status_code == 200 and r.json()["stopped"] is True
    assert client.stopped == [config.HOG_CONTAINER]
    # single use
    assert client.post("/actions/stop_test_program",
                       json={"approval_id": aid, "code": client.sent[aid]}).status_code == 409


def test_wrong_code_refused_then_locks(client):
    aid = _request(client)
    wrong = "0000" if client.sent[aid] != "0000" else "1111"
    for _ in range(config.APPROVAL_MAX_ATTEMPTS):
        assert client.post("/actions/stop_test_program", json={"approval_id": aid, "code": wrong}).status_code == 403
    # even the right code no longer works
    assert client.post("/actions/stop_test_program",
                       json={"approval_id": aid, "code": client.sent[aid]}).status_code == 403
    assert client.stopped == []


def test_deny_means_no_action(client):
    aid = _request(client)
    assert client.post(f"/approvals/{aid}/deny").json()["action_taken"] == "none"
    assert client.post("/actions/stop_test_program",
                       json={"approval_id": aid, "code": client.sent[aid]}).status_code == 409
    assert client.stopped == []


def test_expired_code(client, monkeypatch):
    aid = _request(client)
    monkeypatch.setattr(config, "APPROVAL_TTL_S", -1)
    assert client.post("/actions/stop_test_program",
                       json={"approval_id": aid, "code": client.sent[aid]}).status_code == 403
    assert client.stopped == []


def test_delivery_failure_expires_approval_without_exposing_bot_token(client, conn, monkeypatch):
    token = "secret-bot-token"

    def failed_delivery(*_args):
        raise RuntimeError(f"https://api.telegram.org/bot{token}/sendMessage failed")

    monkeypatch.setattr(approvals, "send_code", failed_delivery)
    response = client.post("/approvals", json={"incident_id": "INC-0001", "action": "stop_test_program",
                                              "target": config.HOG_CONTAINER, "reason": "largest memory user"})
    assert response.status_code == 502
    assert token not in response.text
    approval = conn.execute("SELECT status FROM approvals").fetchone()
    assert approval["status"] == "expired"


def test_only_the_test_container_can_be_requested(client):
    r = client.post("/approvals", json={"incident_id": "INC-0001", "action": "stop_test_program",
                                        "target": "pitcrew-vllm", "reason": "x"})
    assert r.status_code == 400


def test_report_closes_incident(client):
    r = client.post("/incidents/INC-0001/report", json={"status": "resolved", "likely_cause": "hog"})
    assert r.json()["saved"] is True
    assert client.get("/incidents/current").json()["id"] is None


def test_closing_incident_invalidates_pending_approval(client):
    aid = _request(client)
    result = client.post("/incidents/INC-0001/report", json={"status": "unresolved"})
    assert result.status_code == 200
    attempt = client.post("/actions/stop_test_program", json={"approval_id": aid,
                                                               "code": client.sent[aid]})
    assert attempt.status_code == 409
    assert client.stopped == []


def test_read_endpoints_answer(client):
    for path in ("/metrics", "/processes/top?n=3", "/logs/service?lines=5", "/queue/status", "/impact", "/health"):
        assert client.get(path).status_code == 200, path


def test_processes_top_still_shows_hog_when_host_process_scan_is_denied(client, monkeypatch):
    from types import SimpleNamespace

    def denied_process_scan(*_args, **_kwargs):
        raise PermissionError("host process list unavailable")

    def fake_docker(*args, **_kwargs):
        if args[0] == "stats":
            return SimpleNamespace(returncode=0, stdout="pitcrew-test-hog|28.5GiB / 32GiB\n"
                                   "pitcrew-vllm|22.0GiB / 64GiB\n")
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(app_module.psutil, "process_iter", denied_process_scan)
    monkeypatch.setattr(docker_ops, "_docker", fake_docker)
    result = client.get("/processes/top?n=1")
    assert result.status_code == 200
    assert result.json()["processes"] == [{"pid": None, "name": "docker container",
                                            "rss_gb": 28.5, "container": "pitcrew-test-hog",
                                            "source": "docker_stats"}]


def test_processes_top_names_the_program_and_skips_slow_docker_stats(client, monkeypatch):
    """When the host scan already attributes the hog, show the program row once and don't
    pay for `docker stats` (~2 s)."""
    from types import SimpleNamespace

    process = SimpleNamespace(info={"pid": 123, "name": "python3",
                                    "memory_info": SimpleNamespace(rss=28 * 1024 ** 3)})

    def docker_stats_must_not_run():
        raise AssertionError("docker stats called although the host scan found the hog")

    monkeypatch.setattr(app_module.psutil, "process_iter", lambda *_args: [process])
    monkeypatch.setattr(docker_ops, "container_names", lambda: {"id": "pitcrew-test-hog"})
    monkeypatch.setattr(docker_ops, "container_of", lambda *_args: "pitcrew-test-hog")
    monkeypatch.setattr(docker_ops, "container_memory", docker_stats_must_not_run)

    assert client.get("/processes/top").json()["processes"] == [
        {"pid": 123, "name": "python3", "rss_gb": 28.0, "container": "pitcrew-test-hog",
         "source": "host_process"}]


def test_processes_top_falls_back_without_counting_twice(client, monkeypatch):
    """Hog running but its program can't be attributed: add Docker's rows, except containers
    the scan already accounted for."""
    from types import SimpleNamespace

    vllm_proc = SimpleNamespace(info={"pid": 7, "name": "vllm",
                                      "memory_info": SimpleNamespace(rss=4 * 1024 ** 3)})
    monkeypatch.setattr(app_module.psutil, "process_iter", lambda *_args: [vllm_proc])
    monkeypatch.setattr(docker_ops, "container_names", lambda: {"a": "pitcrew-vllm", "b": "pitcrew-test-hog"})
    monkeypatch.setattr(docker_ops, "container_of", lambda *_args: "pitcrew-vllm")
    monkeypatch.setattr(docker_ops, "container_memory", lambda: [
        {"pid": None, "name": "docker container", "rss_gb": 28.5, "container": "pitcrew-test-hog",
         "source": "docker_stats"},
        {"pid": None, "name": "docker container", "rss_gb": 7.1, "container": "pitcrew-vllm",
         "source": "docker_stats"}])

    rows = client.get("/processes/top").json()["processes"]
    assert [(r["container"], r["source"]) for r in rows] == [
        ("pitcrew-test-hog", "docker_stats"), ("pitcrew-vllm", "host_process")]
