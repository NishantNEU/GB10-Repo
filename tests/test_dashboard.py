"""The dashboard page and its state feed (host screen only)."""

import json
import time

from fastapi.testclient import TestClient

from toolserver import app as app_module


def test_page_and_state_render_through_an_incident(conn):
    c = TestClient(app_module.app)
    assert c.get("/dashboard").status_code == 200
    assert "PITCREW" in c.get("/dashboard").text

    s = c.get("/dashboard/state").json()
    assert s["status"]["key"] in ("healthy", "down")      # no service heartbeat in tests
    assert {"impact", "metrics", "timeline", "processes", "activity", "config"} <= set(s)

    conn.execute("INSERT INTO incidents (id, opened_at, status, trigger) VALUES ('INC-0001', ?, 'open', ?)",
                 (time.time(), json.dumps({"delayed_jobs": 5, "service_status": "degraded"})))
    s = c.get("/dashboard/state").json()
    assert s["status"]["key"] == "investigating"
    assert s["timeline"][0]["text"].startswith("Incident INC-0001 opened")


def test_agent_calls_show_in_activity_but_dashboard_polls_do_not(conn):
    c = TestClient(app_module.app)
    c.get("/metrics")
    c.get("/dashboard/state")
    paths = [a["path"] for a in c.get("/dashboard/state").json()["activity"]]
    assert "/metrics" in paths and not any(p.startswith("/dashboard") for p in paths)
