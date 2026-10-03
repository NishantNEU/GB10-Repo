"""One-time approval codes (timeline.md: "How approval can't be faked").

The code goes straight to the on-call engineer through the separate "Pitcrew Approvals" bot.
Only its hash is stored; the agent never sees it and can only pass on what the human typed.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time

import httpx

from common import config


def new_code() -> str:
    return f"{secrets.randbelow(10_000):04d}"


def hash_code(approval_id: str, code: str) -> str:
    return hashlib.sha256(f"{approval_id}:{code.strip()}".encode()).hexdigest()


def code_matches(approval_id: str, code: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_code(approval_id, code), stored_hash)


def send_code(approval_id: str, incident_id: str, target: str, reason: str, code: str) -> str:
    """Deliver the code to the on-call engineer. Returns how it was delivered."""
    text = (f"🔐 Pitcrew approval {approval_id} (incident {incident_id})\n"
            f"Action: stop {target}\nReason: {reason}\n\n"
            f"Code: {code}  (valid {config.APPROVAL_TTL_S // 60} min)\n"
            f"To approve, reply to the Pitcrew agent: approve {code}")
    if config.APPROVER_BOT_TOKEN and config.ONCALL_CHAT_ID:
        r = httpx.post(f"https://api.telegram.org/bot{config.APPROVER_BOT_TOKEN}/sendMessage",
                       json={"chat_id": config.ONCALL_CHAT_ID, "text": text}, timeout=10)
        r.raise_for_status()
        return "telegram"
    # Dev fallback before the Approvals bot exists: host-only file the sandboxed agent can't read.
    config.LOG_DIR.mkdir(exist_ok=True)
    with open(config.LOG_DIR / "approval_codes.log", "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {text}\n\n")
    return "local_log"
