"""Watches the machine and the queue; opens one incident and wakes the agent.

Every DETECTOR_INTERVAL_S (5 s): write a metrics row. If there is no open incident and at least
INCIDENT_MIN_DELAYED jobs are delayed, open one incident and call skills.trigger.trigger_agent.
Plain rules only: the model is never asked whether something is wrong (spec section 8).

    .venv/bin/python -m service.detector
"""

from __future__ import annotations

import json
import logging
import signal
import threading
import time

from common import config, db, hostinfo
from service import impact

log = logging.getLogger("detector")
stop = threading.Event()


def _trigger(incident_id: str, summary: str, details: dict) -> None:
    # Imported lazily so the detector still records incidents if the agent side isn't set up.
    from skills.trigger import trigger_agent
    trigger_agent(incident_id, summary, details=details)


def tick(conn, trigger=_trigger) -> str | None:
    """One detector pass. Returns the new incident id if one was opened."""
    now = time.time()
    mem = hostinfo.memory()
    gpu = hostinfo.gpu()
    svc = hostinfo.service_status()
    conn.execute(
        "INSERT OR REPLACE INTO metrics (ts, mem_used_gb, mem_avail_gb, gpu_util, service_status, jobs_per_min)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (now, mem["mem_used_gb"], mem["mem_avail_gb"], gpu["gpu_util"], svc["status"], svc.get("jobs_per_min")),
    )

    if db.open_incident(conn) is not None:
        return None
    last = conn.execute("SELECT MAX(opened_at) FROM incidents").fetchone()[0]
    if last is not None and now - last < config.INCIDENT_COOLDOWN_S:
        return None  # cool-down: the human already decided on the last incident
    imp = impact.compute(conn, now=now)
    if imp["delayed_jobs"] < config.INCIDENT_MIN_DELAYED:
        return None

    incident_id = db.next_id(conn, "incidents", "INC")
    trigger_info = {
        "rule": f"delayed_jobs >= {config.INCIDENT_MIN_DELAYED}",
        "delayed_jobs": imp["delayed_jobs"], "affected_customers": imp["affected_customers"],
        "longest_wait": imp["longest_wait"], "service_status": svc["status"],
        "mem_avail_gb": mem["mem_avail_gb"], "mem_used_gb": mem["mem_used_gb"],
    }
    conn.execute("INSERT INTO incidents (id, opened_at, status, trigger) VALUES (?, ?, 'open', ?)",
                 (incident_id, now, json.dumps(trigger_info)))
    summary = (f"service {svc['status']}, {imp['delayed_jobs']} jobs delayed, "
               f"memory available {mem['mem_avail_gb']} GB")
    log.warning("incident %s opened: %s", incident_id, summary)
    try:
        trigger(incident_id, summary, trigger_info)
        log.info("agent triggered for %s", incident_id)
    except Exception:  # the incident stays recorded even if the agent can't be reached
        log.exception("could not trigger the agent for %s", incident_id)
    return incident_id


def main() -> None:
    config.LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(config.LOG_DIR / "detector.log"), logging.StreamHandler()],
    )
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    conn = db.connect()
    log.info("detector running every %.0fs (incident at >= %d delayed jobs, delay > %.0fs)",
             config.DETECTOR_INTERVAL_S, config.INCIDENT_MIN_DELAYED, config.DELAY_THRESHOLD_S)
    while not stop.is_set():
        tick(conn)
        stop.wait(config.DETECTOR_INTERVAL_S)


if __name__ == "__main__":
    main()
