#!/usr/bin/env bash
# Onboard the NemoClaw sandbox against the running vLLM, with Telegram, then apply the
# tool-server policy and install the pitcrew skill.
# Prereqs: 03_check_vllm.sh passes; TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_IDS set in .env.
set -euo pipefail
source "$(dirname "$0")/../env.sh"
need_docker
command -v nemoclaw >/dev/null || die "nemoclaw not installed (run 05_install_openshell_nemoclaw.sh)"
[[ -n "${TELEGRAM_BOT_TOKEN:-}" ]] || die "TELEGRAM_BOT_TOKEN missing in .env"
[[ -n "${TELEGRAM_ALLOWED_IDS:-}" ]] || die "TELEGRAM_ALLOWED_IDS missing in .env"
curl -sf "localhost:$VLLM_PORT/v1/models" >/dev/null || die "vLLM not answering on :$VLLM_PORT"

if ! nemoclaw "$SANDBOX_NAME" status >/dev/null 2>&1; then
  export TELEGRAM_BOT_TOKEN TELEGRAM_ALLOWED_IDS
  say "nemoclaw onboard. Choose:"
  echo "    sandbox name ........ $SANDBOX_NAME"
  echo "    inference ........... Local vLLM (it detects localhost:$VLLM_PORT; never pick a cloud/NVIDIA endpoint)"
  echo "    messaging channel ... Telegram (token and allowed IDs come from the environment)"
  nemoclaw onboard
fi

say "tool-server policy (dry run, then apply)"
nemoclaw "$SANDBOX_NAME" policy add --from-file "$REPO_DIR/scripts/openshell/pitcrew-toolserver.yaml" --dry-run
nemoclaw "$SANDBOX_NAME" policy add --from-file "$REPO_DIR/scripts/openshell/pitcrew-toolserver.yaml" --yes

say "pitcrew skill"
"$REPO_DIR/skills/install_skill.sh"

say "status (check inferenceHealth and the model)"
nemoclaw "$SANDBOX_NAME" status || true
say "next: DM the Pitcrew bot on Telegram, then run skills/test_trigger.sh"
