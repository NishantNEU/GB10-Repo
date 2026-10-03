#!/usr/bin/env bash
# Create .venv from the kit's offline wheels (+ vendor/wheels for psutil). No internet, no sudo.
set -euo pipefail
source "$(dirname "$0")/../env.sh"
cd "$REPO_DIR"
[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/pip install -q --no-index \
  --find-links "$KIT_DIR/01_installers/python-wheels-linux-arm64-py312" \
  --find-links vendor/wheels -r requirements.txt
.venv/bin/pip check
say ".venv ready: $(.venv/bin/python --version)"
[[ -f .env ]] || { cp .env.example .env; say "created .env from .env.example; fill in the Telegram values"; }
