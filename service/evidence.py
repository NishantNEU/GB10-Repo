"""Deterministic evidence snapshots for Pitcrew incidents.

This module is read-only and has no runtime integration yet. It turns the
detector's already-calculated trigger and impact data into a stable,
JSON-serializable evidence record.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

SNAPSHOT_SCHEMA_VERSION = "1.1"
CALCULATION_VERSION = "impact-v1"


def build_incident_snapshot(
    *,
    incident_id: str,
    captured_at: float,
    trigger: Mapping[str, Any],
    impact_result: Mapping[str, Any],
    source_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a deterministic, detached incident-evidence snapshot."""
    if not incident_id.strip():
        raise ValueError("incident_id must not be empty")
    if captured_at < 0:
        raise ValueError("captured_at must not be negative")

    trigger_copy = deepcopy(dict(trigger))
    impact_copy = deepcopy(dict(impact_result))
    source_evidence_copy = deepcopy(dict(source_evidence or {}))
    customers = impact_copy.get("customers")

    if not isinstance(customers, list):
        raise ValueError("impact_result must contain a customers list")

    try:
        customer_ids = [customer["id"] for customer in customers]
        job_ids = sorted(
            {
                job_id
                for customer in customers
                for job_id in customer["job_ids"]
            }
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(
            "each customer must contain id and job_ids"
        ) from exc

    snapshot = {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "incident_id": incident_id,
        "captured_at": captured_at,
        "trigger": trigger_copy,
        "impact": impact_copy,
        "source_evidence": source_evidence_copy,
        "evidence": {
            "customer_ids": customer_ids,
            "job_ids": job_ids,
        },
    }

    canonical_json = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    snapshot["snapshot_sha256"] = hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()
    return snapshot
