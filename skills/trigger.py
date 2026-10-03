"""Start the Pitcrew agent with no human message (timeline.md: Kunal, "Trigger test").

Chosen method (option B from the research): the documented non-interactive NemoClaw command
    nemoclaw <sandbox> agent --agent main --channel telegram --to=<chat> --deliver -m "PITCREW_ALERT ..."
which runs `openclaw agent` inside the sandbox. `--to` puts this turn in the same session as the
Telegram chat, so the engineer's later "approve <code>" reply continues the same conversation.

Called by the detector when it opens an incident:
    from skills.trigger import trigger_agent
    trigger_agent("INC-0001", "5 delayed jobs, memory available 14 GB")
or from a shell:
    .venv/bin/python skills/trigger.py INC-0001 --summary "..." [--wait]

The agent turn can run for minutes, so by default it is started detached and logged to
logs/trigger-<incident>.log; the caller returns immediately.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / ".env")

SANDBOX = os.environ.get("SANDBOX_NAME", "pitcrew")
TURN_TIMEOUT_S = int(os.environ.get("PITCREW_TURN_TIMEOUT_S", "300"))


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


def trigger_agent(incident_id: str, summary: str = "", wait: bool = False) -> int | None:
    """Start one agent turn for this incident. Returns the exit code if wait=True, else None."""
    cmd = build_command(incident_id, summary)
    log_dir = REPO / "logs"
    log_dir.mkdir(exist_ok=True)
    log = open(log_dir / f"trigger-{incident_id}.log", "ab")
    log.write(f"$ {' '.join(cmd)}\n".encode())
    log.flush()
    if wait:
        return subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
    subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                     start_new_session=True)
    return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("incident_id")
    p.add_argument("--summary", default="")
    p.add_argument("--wait", action="store_true", help="block until the agent turn ends")
    p.add_argument("--dry-run", action="store_true", help="print the command only")
    a = p.parse_args()
    if a.dry_run:
        print(" ".join(build_command(a.incident_id, a.summary)))
        return 0
    rc = trigger_agent(a.incident_id, a.summary, wait=a.wait)
    print(f"triggered {a.incident_id}" + (f" (exit {rc})" if rc is not None else "; log: logs/trigger-"
                                          f"{a.incident_id}.log"))
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
