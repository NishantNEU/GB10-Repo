#!/usr/bin/env bash
# Manual cleanup only. In the demo, the agent stops the hog through the tool server after approval.
set -euo pipefail
source "$(dirname "$0")/../scripts/env.sh"
need_docker
docker rm -f "$HOG_CONTAINER" >/dev/null 2>&1 && say "$HOG_CONTAINER removed" || say "$HOG_CONTAINER not running"
