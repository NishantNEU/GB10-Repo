"""The presenter feed must remain read-only even while the demo clicks through."""

import httpx
from fastapi.testclient import TestClient

from dashboard import server


def test_live_snapshot_reads_only_existing_evidence(monkeypatch):
    seen = []

    def respond(request):
        seen.append((request.method, request.url.path))
        return httpx.Response(200, json={"status": "healthy"})

    original_client = httpx.AsyncClient
    monkeypatch.setattr(server.httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.MockTransport(respond), **kwargs))

    result = TestClient(server.app).get("/api/live")

    assert result.status_code == 200
    assert result.json()["complete"] is True
    assert len(seen) == len(server.READ_ENDPOINTS)
    assert {method for method, _ in seen} == {"GET"}
    assert {path for _, path in seen} == {path.split("?")[0] for path in server.READ_ENDPOINTS.values()}


def test_fintech_example_uses_merged_synthetic_adapter():
    result = TestClient(server.app).get("/api/fintech-example")

    assert result.status_code == 200
    payload = result.json()
    assert payload["mode"] == "shadow-mode example"
    evidence = payload["evidence"]
    assert evidence["received_error_events"] == 4
    assert evidence["failed_transactions"] == 3
    assert evidence["affected_customers"] == 2
    assert evidence["affected_amount_cents"] == 300000
    assert len(evidence["source_log_sha256"]) == 64
    assert "message" not in str(payload)
