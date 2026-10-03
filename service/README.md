# service/ — Data Engineer

| File | Run | What it does |
|---|---|---|
| `seed.py` | `.venv/bin/python -m service.seed [--reset]` | Creates the tables (from `common/db.py`) and 3 fictional customers (Gold/Silver/Bronze) |
| `sample_service.py` | `.venv/bin/python -m service.sample_service` | Job every ~2 s; worker ~1.5 s/job; **degraded** (~6 s/job + `WARN memory pressure`) when available memory < `MEM_THRESHOLD_GB` |
| `impact.py` | imported by the tool server's `GET /impact` | Delayed jobs (> 30 s), affected customers, longest wait, backlog, estimated value |
| `detector.py` | `.venv/bin/python -m service.detector` | Every 5 s writes `metrics`; at ≥ 5 delayed jobs opens **one** incident and calls `skills.trigger.trigger_agent` |

## Connections to other folders

- **Uses:** `common/config.py` (all thresholds, from `.env`), `common/db.py` (schema), `common/hostinfo.py` (memory/GPU).
- **Used by:** `toolserver/app.py` imports `service.impact`. The agent copies the `/impact` field names, so **don't rename** `delayed_jobs`, `affected_customers`, `longest_wait`, `backlog`, `estimated_value` (`tests/test_contracts.py` checks this).
- **Writes for the tool server:** `run/service_status.json` (heartbeat → `/health`) and `logs/service.log` (→ `/logs/service`).

## Your remaining timeline tasks

- [ ] Set `MEM_THRESHOLD_GB` in `.env` from the real baseline (`free -h` with vLLM loaded; healthy must stay healthy, the hog must cross it).
- [ ] Hand-check impact numbers on real data (`tests/test_impact.py` is the template).
- [ ] Run the flow 3× with `scripts/reset.sh`; counts should match.

Test: `.venv/bin/pytest -q tests/test_impact.py tests/test_detector.py`

## FinTech evidence adapter (shadow mode)

`service.fintech_evidence` demonstrates how Pitcrew can be applied to a
payment-authentication incident without changing the core detector or API.
It consumes synthetic `AUTH_CERT_EXPIRED` events, deduplicates retries by
`transaction_id`, calculates affected customers and payment amount in integer
cents, and emits allow-listed source lineage for the Golden Incident Record.

The adapter intentionally excludes card numbers, CVV values, tokens, and
unexpected log fields. `affected_amount_cents` is the amount associated with
affected synthetic payments; it is not automatically claimed as lost revenue.
All calculations are deterministic Python calculations. The local model may
explain verified results but must not invent counts or financial amounts.
