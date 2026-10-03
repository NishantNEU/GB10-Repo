"""Deterministic evidence extraction for synthetic FinTech error logs.

The adapter handles one demo story: payment authentication failures caused by
an expired authentication certificate. It never sends data to an external
service and emits only allow-listed evidence fields.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

PARSER_VERSION = "fintech-auth-v1"
INCIDENT_TYPE = "payment_authentication_failure"
SUPPORTED_ERROR_CODE = "AUTH_CERT_EXPIRED"


def _required_text(event: Mapping[str, Any], field: str) -> str:
    value = event.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _normalize_event(event: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        raise ValueError("each event must be a mapping")

    amount_cents = event.get("amount_cents")
    if (
        not isinstance(amount_cents, int)
        or isinstance(amount_cents, bool)
        or amount_cents < 0
    ):
        raise ValueError("amount_cents must be a non-negative integer")

    service = _required_text(event, "service").lower()
    level = _required_text(event, "level").upper()
    error_code = _required_text(event, "error_code").upper()
    currency = _required_text(event, "currency").upper()

    if service != "payment-auth":
        raise ValueError("service must be payment-auth")
    if level != "ERROR":
        raise ValueError("level must be ERROR")
    if error_code != SUPPORTED_ERROR_CODE:
        raise ValueError(
            f"unsupported error_code: {error_code}"
        )
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("currency must be a three-letter code")

    # Only allow-listed fields enter evidence. PAN, CVV, tokens, free-text
    # payloads, and any other unexpected fields are intentionally excluded.
    return {
        "event_id": _required_text(event, "event_id"),
        "timestamp": _required_text(event, "timestamp"),
        "service": service,
        "level": level,
        "error_code": error_code,
        "transaction_id": _required_text(event, "transaction_id"),
        "customer_id": _required_text(event, "customer_id"),
        "amount_cents": amount_cents,
        "currency": currency,
    }


def build_payment_auth_evidence(
    events: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return deterministic, deduplicated payment-auth incident evidence."""
    received_events = 0
    events_by_id: dict[str, dict[str, Any]] = {}

    for raw_event in events:
        received_events += 1
        event = _normalize_event(raw_event)
        event_id = event["event_id"]
        previous = events_by_id.get(event_id)

        if previous is not None and previous != event:
            raise ValueError(
                f"event_id {event_id} contains conflicting facts"
            )
        events_by_id[event_id] = event

    if not events_by_id:
        raise ValueError("at least one payment error event is required")

    unique_events = sorted(
        events_by_id.values(),
        key=lambda event: event["event_id"],
    )

    currencies = {event["currency"] for event in unique_events}
    if len(currencies) != 1:
        raise ValueError(
            "one evidence summary cannot mix currencies"
        )

    transactions: dict[str, dict[str, Any]] = {}
    for event in unique_events:
        transaction_id = event["transaction_id"]
        transaction_fact = {
            "customer_id": event["customer_id"],
            "amount_cents": event["amount_cents"],
            "currency": event["currency"],
            "error_code": event["error_code"],
        }
        previous = transactions.get(transaction_id)

        if previous is not None and previous != transaction_fact:
            raise ValueError(
                f"transaction_id {transaction_id} contains conflicting facts"
            )
        transactions[transaction_id] = transaction_fact

    canonical_json = json.dumps(
        unique_events,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    source_log_sha256 = hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()

    transaction_ids = sorted(transactions)
    customer_ids = sorted(
        {
            transaction["customer_id"]
            for transaction in transactions.values()
        }
    )

    return {
        "parser_version": PARSER_VERSION,
        "incident_type": INCIDENT_TYPE,
        "error_code": SUPPORTED_ERROR_CODE,
        "received_error_events": received_events,
        "unique_error_events": len(unique_events),
        "failed_transactions": len(transactions),
        "affected_customers": len(customer_ids),
        "affected_amount_cents": sum(
            transaction["amount_cents"]
            for transaction in transactions.values()
        ),
        "currency": next(iter(currencies)),
        "source_event_ids": [
            event["event_id"] for event in unique_events
        ],
        "transaction_ids": transaction_ids,
        "customer_ids": customer_ids,
        "source_log_sha256": source_log_sha256,
    }
