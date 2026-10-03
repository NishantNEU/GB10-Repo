"""Business impact, calculated in code, never by the model (spec section 7).

The tool server's GET /impact returns compute() as-is, and the agent copies these field names
into its messages: delayed_jobs, affected_customers, longest_wait, backlog, estimated_value.
"""

from __future__ import annotations

import sqlite3
import time

from common import config

TIER_RANK = {"Gold": 0, "Silver": 1, "Bronze": 2}


def _fmt_wait(seconds: float) -> str:
    seconds = int(round(seconds))
    return f"{seconds // 60}m {seconds % 60:02d}s" if seconds >= 60 else f"{seconds}s"


def compute(conn: sqlite3.Connection, now: float | None = None,
            threshold_s: float | None = None) -> dict:
    """A job is delayed if it has waited longer than the threshold and isn't done yet:
    pending jobs older than the threshold, or running jobs that waited longer than it to start."""
    now = time.time() if now is None else now
    t = config.DELAY_THRESHOLD_S if threshold_s is None else threshold_s

    rows = conn.execute(
        """SELECT j.id, j.customer_id, j.created_at, j.started_at, j.status, j.price,
                  c.name, c.tier
           FROM jobs j JOIN customers c ON c.id = j.customer_id
           WHERE j.status IN ('pending', 'running')"""
    ).fetchall()

    backlog = len(rows)
    delayed = []
    for r in rows:
        wait = (now - r["created_at"]) if r["status"] == "pending" else (r["started_at"] - r["created_at"])
        if wait > t:
            delayed.append((r, now - r["created_at"]))

    per_customer: dict[str, dict] = {}
    for r, age in delayed:
        c = per_customer.setdefault(r["customer_id"], {
            "id": r["customer_id"], "name": r["name"], "tier": r["tier"],
            "delayed_jobs": 0, "longest_wait_s": 0.0, "job_ids": [],
        })
        c["delayed_jobs"] += 1
        c["longest_wait_s"] = round(max(c["longest_wait_s"], age), 1)
        c["job_ids"].append(r["id"])
    # Priority rule (spec section 4): tier first, then longest wait.
    customers = sorted(per_customer.values(), key=lambda c: (TIER_RANK[c["tier"]], -c["longest_wait_s"]))

    longest = max((age for _, age in delayed), default=0.0)
    return {
        "delayed_jobs": len(delayed),
        "affected_customers": len(customers),
        "longest_wait": _fmt_wait(longest),
        "longest_wait_s": round(longest, 1),
        "backlog": backlog,
        "estimated_value": round(sum(r["price"] for r, _ in delayed), 2),
        "estimated_value_label": "estimated billable work waiting (not lost revenue)",
        "delay_threshold_s": t,
        "customers": customers,
        "computed_at": now,
    }
