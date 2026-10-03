"""Dashboard routes and the live "agent activity" feed.

The tool server records every API call (method, path, status, caller) in a small ring buffer.
Calls from outside loopback come from the NemoClaw sandbox, i.e. the agent. The page shows
these observable tool calls and decisions, never the model's hidden reasoning (spec section 5).
"""

from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from common import config, db, hostinfo
from service import impact as impact_calc

router = APIRouter()
PAGE = Path(__file__).with_name("index.html")
RESOLVED_SHOW_S = 900   # show "Resolved"/"Unresolved" until 15 min after the incident opened
HISTORY_S = 600         # memory chart window

_activity: deque[dict] = deque(maxlen=60)


def record(method: str, path: str, status: int, client: str | None) -> None:
    if path.startswith("/dashboard") or path in ("/favicon.ico", "/docs", "/openapi.json"):
        return
    local = client in (None, "127.0.0.1", "::1", "testclient")
    _activity.appendleft({"ts": time.time(), "method": method, "path": path, "status": status,
                          "who": "local" if local else "agent"})


@router.get("/dashboard", include_in_schema=False)
def page() -> FileResponse:
    return FileResponse(PAGE, media_type="text/html")


def _status(incident, approval, svc_status: str) -> tuple[str, str]:
    """(key, label) for the big banner. Order follows the incident lifecycle."""
    if incident is not None and incident["status"] in db.OPEN_STATUSES:
        if approval is not None and approval["status"] == "approved":
            return "recovering", "Recovering"
        if incident["status"] == "awaiting_approval":
            return "awaiting", "Awaiting approval"
        return "investigating", "Investigating"
    if (incident is not None and incident["status"] in ("resolved", "unresolved")
            and time.time() - incident["opened_at"] < RESOLVED_SHOW_S):
        return incident["status"], incident["status"].capitalize()
    if svc_status == "degraded":
        return "degraded", "Degraded"
    if svc_status == "down":
        return "down", "Service down"
    return "healthy", "Healthy"


def _timeline(conn, incident) -> list[dict]:
    if incident is None:
        return []
    trig = json.loads(incident["trigger"])
    events = [{"ts": incident["opened_at"], "kind": "open",
               "text": f"Incident {incident['id']} opened: {trig.get('delayed_jobs', '?')} jobs delayed, "
                       f"service {trig.get('service_status', '?')}"}]
    for a in conn.execute("SELECT * FROM approvals WHERE incident_id = ? ORDER BY created_at", (incident["id"],)):
        events.append({"ts": a["created_at"], "kind": "approval",
                       "text": f"Approval {a['id']} requested: stop {a['target']} (one-time code sent to the on-call engineer)"})
        if a["attempts"]:
            events.append({"ts": a["created_at"] + 0.001, "kind": "refused",
                           "text": f"{a['attempts']} wrong code attempt(s) refused; nothing stopped"})
        if a["decided_at"]:
            text = {"approved": f"Approved: {a['target']} stopped",
                    "denied": "Denied by on-call engineer: no action taken",
                    "expired": "Approval expired: no action taken"}.get(a["status"], a["status"])
            events.append({"ts": a["decided_at"], "kind": a["status"], "text": text})
    if incident["report_json"]:
        report = json.loads(incident["report_json"])
        # No close timestamp is stored, so place the report right after the last decision.
        events.append({"ts": max(e["ts"] for e in events) + 0.002, "kind": incident["status"],
                       "text": f"Report saved: {incident['status']}"
                               + (f" ({report.get('likely_cause')})" if report.get("likely_cause") else "")})
    return sorted(events, key=lambda e: e["ts"])


@router.get("/dashboard/state", include_in_schema=False)
def state() -> dict:
    from toolserver import app as ts  # lazy: the tool server imports this module

    conn = db.connect()
    now = time.time()
    incident = db.open_incident(conn) or conn.execute(
        "SELECT * FROM incidents ORDER BY opened_at DESC LIMIT 1").fetchone()
    approval = conn.execute(
        "SELECT * FROM approvals WHERE incident_id = ? ORDER BY created_at DESC LIMIT 1",
        (incident["id"],)).fetchone() if incident else None
    svc = hostinfo.service_status()
    key, label = _status(incident, approval, svc["status"])
    history = [dict(r) for r in conn.execute(
        "SELECT ts, mem_used_gb, mem_avail_gb FROM metrics WHERE ts > ? ORDER BY ts", (now - HISTORY_S,))]
    report = json.loads(incident["report_json"]) if incident and incident["report_json"] else None

    return {
        "now": now,
        "status": {"key": key, "label": label},
        "service": {**svc, **ts._queue(conn)},
        "metrics": {**hostinfo.memory(), **hostinfo.gpu()},
        "impact": impact_calc.compute(conn, now=now),
        "incident": None if incident is None else {
            "id": incident["id"], "status": incident["status"], "opened_at": incident["opened_at"],
            "trigger": json.loads(incident["trigger"]), "report": report},
        "approval": None if approval is None else {
            "id": approval["id"], "status": approval["status"], "target": approval["target"],
            "created_at": approval["created_at"], "decided_at": approval["decided_at"],
            "attempts": approval["attempts"], "expires_at": approval["created_at"] + config.APPROVAL_TTL_S},
        "timeline": _timeline(conn, incident),
        "processes": ts.processes_top(n=6)["processes"],
        "logs": ts.logs_service(lines=8)["lines"],
        "activity": list(_activity)[:14],
        "history": history,
        "config": {"mem_threshold_gb": config.MEM_THRESHOLD_GB, "delay_threshold_s": config.DELAY_THRESHOLD_S,
                   "hog": config.HOG_CONTAINER, "model": "Qwen3.6-35B-A3B NVFP4", "host": "Dell Pro Max GB10"},
    }
