"""One-time approval codes (timeline.md: "How approval can't be faked").

The code goes straight to the on-call engineer on a channel the agent has no access to.
Only its hash is stored; the agent never sees it and can only pass on what the human typed.

Delivery channels, in order of preference (the first one configured is used):
  1. email     APPROVER_EMAIL + SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD (STARTTLS, port 587)
  2. telegram  APPROVER_BOT_TOKEN + ONCALL_CHAT_ID (the separate "Pitcrew Approvals" bot)
  3. local_log logs/approval_codes.log on the host (development only)
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage

import httpx

from common import config

SMTP_TIMEOUT_S = 15


def new_code() -> str:
    return f"{secrets.randbelow(10_000):04d}"


def hash_code(approval_id: str, code: str) -> str:
    return hashlib.sha256(f"{approval_id}:{code.strip()}".encode()).hexdigest()


def code_matches(approval_id: str, code: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_code(approval_id, code), stored_hash)


def email_configured() -> bool:
    return all((config.APPROVER_EMAIL, config.SMTP_HOST, config.SMTP_USERNAME, config.SMTP_PASSWORD))


def _send_email(subject: str, body: str) -> None:
    """Send one plain-text email over SMTP with STARTTLS. Raises on any delivery failure."""
    msg = EmailMessage()
    msg["From"] = config.SMTP_FROM or config.SMTP_USERNAME
    msg["To"] = config.APPROVER_EMAIL
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=SMTP_TIMEOUT_S) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        smtp.send_message(msg)


def send_code(approval_id: str, incident_id: str, target: str, reason: str, code: str) -> str:
    """Deliver the code to the on-call engineer. Returns the channel used.

    Raises if the configured channel fails; the caller expires the approval and reports a
    generic error (provider errors can contain credentials, so they are never echoed)."""
    text = (f"🔐 Pitcrew approval {approval_id} (incident {incident_id})\n"
            f"Action: stop {target}\nReason: {reason}\n\n"
            f"Code: {code}  (valid {config.APPROVAL_TTL_S // 60} min)\n"
            f"To approve, reply to the Pitcrew agent: approve {code}")
    if email_configured():
        _send_email(f"Pitcrew approval needed: stop {target} ({incident_id})",
                    text + "\n\nIf you did not expect this request, ignore it: nothing happens without the code.")
        return "email"
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
