"""The sample "AI service": customers submit jobs, one worker processes them.

Healthy: a job every ~2 s, each takes ~1.5 s, so the queue stays flat.
Degraded: when host available memory < MEM_THRESHOLD_GB, each job takes ~6 s and the queue grows.
It is built to back off under memory pressure; say so in the pitch.

    .venv/bin/python -m service.sample_service
"""

from __future__ import annotations

import json
import logging
import random
import signal
import threading
import time

from common import config, db, hostinfo
from common.logsetup import configure_logging
from service.seed import CUSTOMERS, PRICE, seed

log = logging.getLogger("sample_service")
stop = threading.Event()
WEIGHTS = {"Gold": 0.4, "Silver": 0.35, "Bronze": 0.25}


def submitter() -> None:
    """Fictional customers submit jobs. Seeded, so every demo run has the same mix."""
    conn = db.connect()
    rng = random.Random(42)
    ids = [c[0] for c in CUSTOMERS]
    weights = [WEIGHTS[c[2]] for c in CUSTOMERS]
    while not stop.is_set():
        cid = rng.choices(ids, weights)[0]
        cur = conn.execute(
            "INSERT INTO jobs (customer_id, created_at, status, price) VALUES (?, ?, 'pending', ?)",
            (cid, time.time(), PRICE[cid]),
        )
        log.info("job_submitted id=%s customer=%s", cur.lastrowid, cid)
        stop.wait(config.JOB_INTERVAL_S * rng.uniform(0.8, 1.2))


def write_status(status: str, mem_avail_gb: float, jobs_per_min: float) -> None:
    config.RUN_DIR.mkdir(exist_ok=True)
    tmp = config.SERVICE_STATUS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"status": status, "ts": time.time(),
                               "mem_avail_gb": mem_avail_gb, "jobs_per_min": jobs_per_min}))
    tmp.replace(config.SERVICE_STATUS_FILE)


def worker() -> None:
    conn = db.connect()
    was_degraded = False
    while not stop.is_set():
        mem = hostinfo.memory()
        degraded = mem["mem_avail_gb"] < config.MEM_THRESHOLD_GB
        if degraded and not was_degraded:
            log.warning("memory pressure: reducing throughput (available %.1f GB < %.1f GB)",
                        mem["mem_avail_gb"], config.MEM_THRESHOLD_GB)
        elif was_degraded and not degraded:
            log.info("memory pressure cleared: normal throughput (available %.1f GB)", mem["mem_avail_gb"])
        was_degraded = degraded

        done_last_min = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status = 'done' AND finished_at > ?", (time.time() - 60,)
        ).fetchone()[0]
        write_status("degraded" if degraded else "healthy", mem["mem_avail_gb"], float(done_last_min))

        job = conn.execute(
            "SELECT id, customer_id, created_at FROM jobs WHERE status = 'pending' ORDER BY created_at LIMIT 1"
        ).fetchone()
        if job is None:
            stop.wait(0.2)
            continue
        started = time.time()
        conn.execute("UPDATE jobs SET status = 'running', started_at = ? WHERE id = ?", (started, job["id"]))
        run_s = config.JOB_TIME_DEGRADED_S if degraded else config.JOB_TIME_HEALTHY_S
        stop.wait(run_s)
        conn.execute("UPDATE jobs SET status = 'done', finished_at = ? WHERE id = ?", (time.time(), job["id"]))
        if degraded:
            log.warning("job_done id=%s customer=%s wait_s=%.1f run_s=%.1f mode=degraded",
                        job["id"], job["customer_id"], started - job["created_at"], run_s)
        else:
            log.info("job_done id=%s customer=%s wait_s=%.1f run_s=%.1f",
                     job["id"], job["customer_id"], started - job["created_at"], run_s)


def main() -> None:
    configure_logging(config.SERVICE_LOG)
    seed()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    log.info("sample service starting (threshold %.1f GB available)", config.MEM_THRESHOLD_GB)
    t = threading.Thread(target=submitter, daemon=True)
    t.start()
    worker()
    log.info("sample service stopped")


if __name__ == "__main__":
    main()
