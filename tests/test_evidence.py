"""Regression tests for deterministic incident evidence."""

import json

import pytest

from conftest import add_job
from service import evidence, impact

NOW = 1_000_000.0


def test_snapshot_is_deterministic_json_and_detached(conn):
    add_job(conn, "CUST-NORTHWIND", NOW - 90)
    add_job(
        conn,
        "CUST-BLUEFIN",
        NOW - 120,
        status="running",
        started_at=NOW - 80,
    )
    add_job(conn, "CUST-ACORN", NOW - 10)

    impact_result = impact.compute(conn, now=NOW, threshold_s=30)
    trigger = {
        "rule": "delayed_jobs >= 2",
        "delayed_jobs": impact_result["delayed_jobs"],
        "affected_customers": impact_result["affected_customers"],
    }

    first = evidence.build_incident_snapshot(
        incident_id="INC-0001",
        captured_at=NOW,
        trigger=trigger,
        impact_result=impact_result,
    )
    second = evidence.build_incident_snapshot(
        incident_id="INC-0001",
        captured_at=NOW,
        trigger=trigger,
        impact_result=impact_result,
    )

    assert first == second
    assert first["snapshot_schema_version"] == "1.0"
    assert first["calculation_version"] == "impact-v1"
    assert first["impact"]["delayed_jobs"] == 2
    assert first["evidence"]["job_ids"] == [1, 2]
    assert first["evidence"]["customer_ids"] == [
        "CUST-NORTHWIND",
        "CUST-BLUEFIN",
    ]
    assert len(first["snapshot_sha256"]) == 64
    json.dumps(first, allow_nan=False)

    impact_result["customers"][0]["job_ids"].append(999)
    trigger["delayed_jobs"] = 999

    assert first["evidence"]["job_ids"] == [1, 2]
    assert first["trigger"]["delayed_jobs"] == 2


def test_snapshot_rejects_invalid_required_fields():
    with pytest.raises(ValueError, match="incident_id"):
        evidence.build_incident_snapshot(
            incident_id="",
            captured_at=NOW,
            trigger={},
            impact_result={"customers": []},
        )

    with pytest.raises(ValueError, match="customers"):
        evidence.build_incident_snapshot(
            incident_id="INC-0001",
            captured_at=NOW,
            trigger={},
            impact_result={},
        )
