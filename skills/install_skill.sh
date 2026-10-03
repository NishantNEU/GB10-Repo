#!/usr/bin/env bash
# Install (or update) the pitcrew skill into the NemoClaw sandbox.
# Runs `openclaw skills install <staged> --agent main --force` inside the sandbox (replaces same-name skill).
# The skill lands in /sandbox/.openclaw/workspace/skills/; a new session picks it up.
set -euo pipefail
source "$(dirname "$0")/../scripts/env.sh"
nemoclaw "$SANDBOX_NAME" skill install "$REPO_DIR/skills/pitcrew/"
nemoclaw "$SANDBOX_NAME" skill list
