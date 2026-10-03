#!/usr/bin/env bash
# Start the controlled fault: container `pitcrew-test-hog` grows ~1 GiB every 3 s up to 30 GiB.
# Reuses the kit's vLLM image for python3 (no download). No GPU, no network, capped by --memory.
set -euo pipefail
source "$(dirname "$0")/../scripts/env.sh"
need_docker

if docker ps -a --format '{{.Names}}' | grep -qx "$HOG_CONTAINER"; then
  die "$HOG_CONTAINER already exists. Run scripts/reset.sh (or chaos/stop_hog.sh) first."
fi

docker run -d --name "$HOG_CONTAINER" \
  --label pitcrew.role=test-hog \
  --memory "$HOG_MEMORY_LIMIT" --memory-swap "$HOG_MEMORY_LIMIT" \
  --network none --init --restart no \
  --entrypoint python3 \
  -v "$REPO_DIR/chaos/hog.py":/hog.py:ro \
  "$VLLM_IMAGE" /hog.py \
    --step-gb "$HOG_STEP_GB" --interval "$HOG_INTERVAL_S" \
    --max-gb "$HOG_MAX_GB" --min-free-gb "$HOG_MIN_FREE_GB" >/dev/null

say "$HOG_CONTAINER started at $(date +%T). Watch: docker logs -f $HOG_CONTAINER   |   watch -n1 free -h"
