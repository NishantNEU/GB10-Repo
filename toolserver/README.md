# toolserver/ — Backend

`.venv/bin/uvicorn toolserver.app:app --host 0.0.0.0 --port 9000` (started by `scripts/run_all.sh`).
`TOOLSERVER_STUB=1` serves the fixed JSON in `stub_data.py` (same shapes), so Kunal can test the agent early.

| File | What it does |
|---|---|
| `app.py` | All timeline endpoints: reads, `POST /approvals`, `/approvals/{id}/deny`, `/actions/stop_test_program`, `/incidents/{id}/report` |
| `approvals.py` | 4-digit code → only its hash is stored → sent by the **Approvals bot** (`APPROVER_BOT_TOKEN`, `ONCALL_CHAT_ID`). Without a token it writes to `logs/approval_codes.log` (host only) for testing |
| `docker_ops.py` | Container name per process (cgroup → `docker ps`), label check, `docker stop` |
| `stub_data.py` | Fixed responses for stub mode |

## Safety checks on `POST /actions/stop_test_program` (all must pass)

1. The approval exists and is `pending` (single use; denied or used approvals return 409).
2. Not expired (5 min) and fewer than 3 wrong attempts. After that it locks.
3. The code matches the stored hash.
4. Target is `pitcrew-test-hog` **and** the container carries label `pitcrew.role=test-hog` (set by `chaos/start_hog.sh`).

`POST /approvals` only accepts `action=stop_test_program`, `target=pitcrew-test-hog`, for the currently open incident.

## Connections to other folders

- **Uses:** `common/` (config, db, hostinfo) and `service.impact`.
- **Called by:** the agent (`skills/pitcrew/SKILL.md`), through `scripts/openshell/pitcrew-toolserver.yaml`. If you add or rename an endpoint, update both; `tests/test_contracts.py` fails until they match.

## Your remaining timeline tasks

- [ ] Create the Pitcrew Approvals bot (BotFather), engineer sends `/start`, put `APPROVER_BOT_TOKEN` and `ONCALL_CHAT_ID` in `.env`.
- [ ] Check `/processes/top` shows `pitcrew-test-hog` once Docker access works.
- [ ] Optional dashboard only if the full flow passes by 16:45.

Test: `.venv/bin/pytest -q tests/test_toolserver.py tests/test_contracts.py`
