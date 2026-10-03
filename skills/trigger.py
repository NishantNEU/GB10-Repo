"""Start the Pitcrew agent with no human message (timeline.md: Kunal, "Trigger test").

Chosen method (option B from the research): the documented non-interactive NemoClaw command
    nemoclaw <sandbox> agent --agent main --channel telegram --to=<chat> --deliver -m "PITCREW_ALERT ..."
which runs `openclaw agent` inside the sandbox. `--to` puts this turn in the same session as the
Telegram chat, so the engineer's later "approve <code>" reply continues the same conversation.

Called by the detector when it opens an incident:
    from skills.trigger import trigger_agent
    trigger_agent("INC-0001", "5 delayed jobs, memory available 14 GB", details={...})
or from a shell (waits for the turn):
    .venv/bin/python skills/trigger.py INC-0001 --summary "..."

What happens:
1. The monitor posts "🚨 Incident opened" to Telegram itself, with numbers from code. An agent
   turn only delivers its final reply, so the agent can't reliably post this first message.
2. The agent turn runs in a background thread, logged to logs/trigger-<incident>.log.
3. If the turn fails it is retried once; if it fails again, a backup alert tells the human
   directly, so a broken agent can never fail silently.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / ".env")

SANDBOX = os.environ.get("SANDBOX_NAME", "pitcrew")
TURN_TIMEOUT_S = int(os.environ.get("PITCREW_TURN_TIMEOUT_S", "300"))
RETRY_DELAY_S = 10


def _chat_id() -> str:
    chat = os.environ.get("PITCREW_CHAT_ID") or os.environ.get("ONCALL_CHAT_ID")
    if not chat:
        raise RuntimeError("set PITCREW_CHAT_ID (or ONCALL_CHAT_ID) in .env")
    return chat


def build_command(incident_id: str, summary: str = "") -> list[str]:
    message = f"PITCREW_ALERT incident={incident_id}"
    if summary:
        message += f" | {summary}"
    message += " | Follow the pitcrew skill, procedure A."
    nemoclaw = shutil.which("nemoclaw") or "nemoclaw"
    return [
        nemoclaw, SANDBOX, "agent",
        "--agent", "main",
        "--channel", "telegram",
        # --to= form: Telegram group IDs start with "-100" and would otherwise parse as a flag.
        f"--to={_chat_id()}",
        "--deliver",
        "--timeout", str(TURN_TIMEOUT_S),
        "-m", message,
    ]


def send_telegram(text: str) -> bool:
    """Post straight to the on-call chat through the Pitcrew bot's API, without the agent.
    Used for the "incident opened" alert (numbers from code) and the backup alert. Never raises."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return False
    try:
        r = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                       json={"chat_id": _chat_id(), "text": text}, timeout=10)
        return r.status_code == 200
    except Exception:  # the token is in the URL, so never let the exception text reach a log
        return False


def opened_message(incident_id: str, d: dict) -> str:
    return (f"🚨 Incident {incident_id} opened — {time.strftime('%H:%M')}\n"
            f"The sample AI service is {d.get('service_status', 'degraded')}. "
            f"Memory available: {d.get('mem_avail_gb', '?')} GB.\n"
            f"Impact so far: {d.get('delayed_jobs', '?')} jobs delayed across "
            f"{d.get('affected_customers', '?')} fictional customers (longest wait {d.get('longest_wait', '?')}).\n"
            f"Pitcrew is investigating on the GB10 before recommending an action.")


def _run_with_fallback(incident_id: str, cmd: list[str], log_path: Path) -> int:
    """Run the agent turn; retry once on failure; if it still fails, tell a human directly."""
    rc = 1
    for attempt in (1, 2):
        with open(log_path, "ab") as log:
            log.write(f"$ [attempt {attempt}] {' '.join(cmd)}\n".encode())
            log.flush()
            rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
            log.write(f"[attempt {attempt}] exit code {rc}\n".encode())
        if rc == 0:
            return 0
        if attempt == 1:
            time.sleep(RETRY_DELAY_S)
    sent = send_telegram(f"⚠️ Incident {incident_id} is open, but the Pitcrew agent did not respond "
                         f"(exit code {rc}, retried once). A human needs to check the GB10. "
                         f"Nothing has been stopped.")
    with open(log_path, "ab") as log:
        log.write(f"[fallback] backup alert {'sent' if sent else 'NOT sent'}\n".encode())
    return rc


def trigger_agent(incident_id: str, summary: str = "", details: dict | None = None,
                  wait: bool = False) -> int | None:
    """Post the "incident opened" alert, then start one agent turn for this incident.

    By default the turn runs in a background thread (it can take minutes), so the caller
    returns at once. Returns the agent's exit code only when wait=True."""
    if details is not None:
        send_telegram(opened_message(incident_id, details))
    cmd = build_command(incident_id, summary)
    log_dir = REPO / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"trigger-{incident_id}.log"
    if wait:
        return _run_with_fallback(incident_id, cmd, log_path)
    threading.Thread(target=_run_with_fallback, args=(incident_id, cmd, log_path),
                     name=f"trigger-{incident_id}", daemon=True).start()
    return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("incident_id")
    p.add_argument("--summary", default="")
    p.add_argument("--dry-run", action="store_true", help="print the command only")
    a = p.parse_args()
    if a.dry_run:
        print(" ".join(build_command(a.incident_id, a.summary)))
        return 0
    # From a shell, wait: a background thread would die when this process exits.
    rc = trigger_agent(a.incident_id, a.summary, wait=True)
    print(f"triggered {a.incident_id} (exit {rc}); log: logs/trigger-{a.incident_id}.log")
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
