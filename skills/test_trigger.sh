#!/usr/bin/env bash
# Trigger smoke test (checkpoint 15:15): the agent should post in Telegram with nobody typing.
# Safe: asks for a one-line reply and no tool calls.
set -euo pipefail
source "$(dirname "$0")/../scripts/env.sh"
chat="${PITCREW_CHAT_ID:-${ONCALL_CHAT_ID:-}}"
[[ -n "$chat" ]] || die "set PITCREW_CHAT_ID (or ONCALL_CHAT_ID) in .env"
say "sending a test turn to sandbox $SANDBOX_NAME, delivering to Telegram chat $chat"
time nemoclaw "$SANDBOX_NAME" agent --agent main --channel telegram "--to=$chat" --deliver --timeout 120 \
  -m "PITCREW_TEST: reply with exactly one line: 'Pitcrew trigger test OK — running on the GB10.' Do not call any tools."
say "now check the Telegram chat for that line"
