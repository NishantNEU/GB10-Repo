# skills/ — Kunal (AI/ML)

| File | Runs where | Purpose |
|---|---|---|
| `pitcrew/SKILL.md` | inside the NemoClaw sandbox | Agent instructions: tools (curl to `:9000`), investigation order, diagnosis, approval/deny/verify, message templates, rules |
| `trigger.py` | host | Starts the agent with no human message. The detector calls `trigger_agent(incident_id, summary)` |
| `install_skill.sh` | host | `nemoclaw <sandbox> skill install skills/pitcrew/` (re-run after every SKILL.md edit, then start a new session) |
| `test_trigger.sh` | host | Checkpoint test: the agent posts in Telegram with nobody typing |

## Trigger decision

**Chosen: option B, `nemoclaw <sandbox> agent --agent main --channel telegram --to=<chat> --deliver -m "PITCREW_ALERT …"`.** It needs no config change, it's the documented way to drive a sandbox from another program, and the exit code reports failures. `--to` puts the turn in the Telegram chat's session, so `approve <code>` arrives in the same conversation.

Evidence (kit mirrors): NemoClaw `docs/reference/commands.mdx` (`agent` subcommand, about line 1325) and OpenClaw v2026.9.2 `docs/cli/agent.md` (`--to`, `--channel`, `--deliver`, `--timeout`).

| Rank | Option | Notes |
|---|---|---|
| 1 | **B: `nemoclaw … agent`** (built) | Blocks for the whole turn, so `trigger.py` runs it detached and logs to `logs/trigger-<id>.log` |
| 2 | A: gateway webhook `POST 127.0.0.1:18789/hooks/agent` | Needs `openclaw config set hooks …` inside the sandbox + `nemoclaw <sb> gateway restart`; the hooks token may be stripped on rebuild |
| 3 | C: OpenClaw cron trigger script (≥ 30 s interval) | Polls `/incidents/current` from inside the sandbox; only if the host can't call into it |

## Verify on the GB10 (once onboarded)

1. `skills/test_trigger.sh` posts in Telegram. If not, check `logs/` and the `--to` chat ID.
2. A Telegram reply after a triggered turn continues the same session (the agent remembers the incident). If not, `SKILL.md` already tells the agent to recover `pending_approval_id` from `/incidents/current`. **Ask Backend to include that field.**
3. `openshell term` shows the agent's curl to `:9000` allowed. If it's blocked, fix `binaries:` in `scripts/openshell/pitcrew-toolserver.yaml`.

## Notes for Backend (contract assumptions in SKILL.md)

- `GET /incidents/current` should include `id` and `pending_approval_id` (or null).
- `POST /incidents/{id}/report` accepts the "Report JSON" shape in SKILL.md.
- The agent reads `/impact` fields by name: `delayed_jobs`, `affected_customers`, `longest_wait`, `backlog`, `estimated_value`. Tell Kunal if the names differ.
