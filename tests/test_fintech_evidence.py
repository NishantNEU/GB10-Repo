"""Tests for deterministic FinTech source evidence."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from service import evidence, fintech_evidence

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "service/fixtures/payment_auth_errors.jsonl"
NOW = 1_000_000.0


def _events():
    return [
        json.loads(line)
        for line in FIXTURE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_payment_errors_are_deduplicated_and_attached_to_snapshot():
    events = _events()
    summary = fintech_evidence.build_payment_auth_evidence(events)

    assert summary["parser_version"] == "fintech-auth-v1"
    assert summary["incident_type"] == "payment_authentication_failure"
    assert summary["error_code"] == "AUTH_CERT_EXPIRED"
    assert summary["received_error_events"] == 4
    assert summary["unique_error_events"] == 4
    assert summary["failed_transactions"] == 3
    assert summary["affected_customers"] == 2
    assert summary["affected_amount_cents"] == 300000
    assert summary["currency"] == "USD"
    assert summary["transaction_ids"] == [
        "TXN-001",
        "TXN-002",
        "TXN-003",
    ]
    assert summary["customer_ids"] == [
        "CUST-BLUEFIN",
        "CUST-NORTHWIND",
    ]
    assert len(summary["source_log_sha256"]) == 64

    snapshot = evidence.build_incident_snapshot(
        incident_id="INC-FINTECH-0001",
        captured_at=NOW,
        trigger={
            "rule": "AUTH_CERT_EXPIRED",
            "failed_transactions": 3,
        },
        impact_result={"customers": []},
        source_evidence=summary,
    )

    assert snapshot["snapshot_schema_version"] == "1.1"
    assert snapshot["source_evidence"] == summary
    assert snapshot["snapshot_sha256"]


def test_adapter_is_deterministic_and_ignores_sensitive_extra_fields():
    events = _events()
    events[0]["card_number"] = "PAN-SHOULD-NOT-LEAK"
    events[0]["cvv"] = "999"
    events[0]["access_token"] = "do-not-copy"
    events.append(deepcopy(events[0]))

    first = fintech_evidence.build_payment_auth_evidence(events)
    second = fintech_evidence.build_payment_auth_evidence(
        reversed(events)
    )

    assert first["received_error_events"] == 5
    assert first["unique_error_events"] == 4
    assert first["failed_transactions"] == 3
    assert first["affected_amount_cents"] == 300000
    assert first["source_log_sha256"] == second["source_log_sha256"]

    serialized = json.dumps(first)
    assert '"card_number"' not in serialized
    assert '"cvv"' not in serialized
    assert '"access_token"' not in serialized
    assert "PAN-SHOULD-NOT-LEAK" not in serialized
    assert "do-not-copy" not in serialized


def test_conflicting_retry_facts_are_rejected():
    events = _events()
    conflicting_retry = deepcopy(events[0])
    conflicting_retry["event_id"] = "EVT-005"
    conflicting_retry["amount_cents"] = 100001
    events.append(conflicting_retry)

    with pytest.raises(ValueError, match="conflicting facts"):
        fintech_evidence.build_payment_auth_evidence(events)
